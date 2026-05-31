"""TeleStore — Customer reviews handler."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.repos import ReviewRepo, OrderRepo, ProductRepo
from states.forms import ReviewStates

router = Router(name="reviews")

STAR_MAP = {"1": "⭐", "2": "⭐⭐", "3": "⭐⭐⭐", "4": "⭐⭐⭐⭐", "5": "⭐⭐⭐⭐⭐"}


@router.callback_query(F.data.startswith("review:start:"))
async def review_start(callback: CallbackQuery, state: FSMContext):
    """Begin review flow for an order."""
    order_id = callback.data.split(":")[2]
    await state.update_data(order_id=order_id)
    await state.set_state(ReviewStates.selecting_rating)

    from keyboards.builders import rating_kb
    await callback.message.edit_text(
        "⭐ <b>Leave a Review</b>\n\nHow would you rate your experience?",
        reply_markup=rating_kb(order_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("review:rate:"), ReviewStates.selecting_rating)
async def review_rate(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    order_id = parts[2]
    rating = int(parts[3])
    stars = STAR_MAP.get(str(rating), "⭐")

    await state.update_data(rating=rating)
    await state.set_state(ReviewStates.entering_comment)
    await callback.message.edit_text(
        f"You gave: {stars}\n\nNow write a short review (or send /skip to skip):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(ReviewStates.entering_comment)
async def review_comment(message: Message, db, db_user, state: FSMContext):
    data = await state.get_data()
    order_id = data["order_id"]
    rating = data["rating"]
    comment = None if message.text == "/skip" else message.text.strip()

    # Get order to find store/product
    order_repo = OrderRepo(db)
    order = await order_repo.get_by_id(order_id)
    if not order:
        await message.answer("❌ Order not found.")
        await state.clear()
        return

    review_repo = ReviewRepo(db)
    await review_repo.create(
        user_id=str(db_user["_id"]),
        store_id=str(order["store_id"]),
        order_id=order_id,
        rating=rating,
        comment=comment,
    )

    stars = STAR_MAP.get(str(rating), "⭐")
    await state.clear()
    await message.answer(
        f"✅ <b>Review submitted!</b>\n\n"
        f"Rating: {stars}\n"
        + (f"Comment: {comment}\n" if comment else "")
        + "\nThank you for your feedback!",
        parse_mode="HTML"
    )
