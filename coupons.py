"""TeleStore — Customer coupon apply handler."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.repos import CartRepo, CouponRepo
from states.forms import ApplyCouponStates

router = Router(name="coupons")


@router.callback_query(F.data.startswith("coupon:apply:"))
async def apply_coupon_start(callback: CallbackQuery, state: FSMContext, db_user):
    store_id = callback.data.split(":")[2]
    await state.update_data(store_id=store_id)
    await state.set_state(ApplyCouponStates.entering_code)
    await callback.message.edit_text(
        "🎟️ <b>Apply Coupon</b>\n\nEnter your coupon code:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(ApplyCouponStates.entering_code)
async def apply_coupon_code(message: Message, db, db_user, state: FSMContext):
    code = message.text.strip().upper()
    data = await state.get_data()
    store_id = data["store_id"]

    coupon_repo = CouponRepo(db)
    coupon = await coupon_repo.get_by_code(code)

    if not coupon or str(coupon.get("store_id", "")) != store_id:
        await message.answer("❌ Invalid coupon code. Please try again or /cancel:")
        return

    if not coupon.get("is_active", True):
        await message.answer("❌ This coupon is no longer active.")
        await state.clear()
        return

    import datetime
    if coupon.get("expires_at") and coupon["expires_at"] < datetime.datetime.utcnow():
        await message.answer("❌ This coupon has expired.")
        await state.clear()
        return

    if coupon.get("usage_limit") and coupon.get("usage_count", 0) >= coupon["usage_limit"]:
        await message.answer("❌ This coupon has reached its usage limit.")
        await state.clear()
        return

    # Apply to cart
    cart_repo = CartRepo(db)
    cart = await cart_repo.get(str(db_user["_id"]))
    if not cart or not cart.get("items"):
        await message.answer("❌ Your cart is empty.")
        await state.clear()
        return

    await cart_repo.apply_coupon(str(db_user["_id"]), code)

    # Calculate discount preview
    subtotal = sum(i["price"] * i["qty"] for i in cart["items"])
    if coupon["type"] == "percentage":
        discount = subtotal * coupon["value"] / 100
        discount_str = f"{coupon['value']}% off (-₹{discount:,.2f})"
    else:
        discount = min(coupon["value"], subtotal)
        discount_str = f"₹{discount:,.2f} off"

    await state.clear()
    await message.answer(
        f"✅ <b>Coupon applied!</b>\n\n"
        f"🎟️ Code: <code>{code}</code>\n"
        f"💸 Discount: {discount_str}\n"
        f"💰 New total: <b>₹{subtotal - discount:,.2f}</b>\n\n"
        f"Proceed to checkout to complete your order.",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("coupon:remove:"))
async def remove_coupon(callback: CallbackQuery, db, db_user):
    cart_repo = CartRepo(db)
    await cart_repo.remove_coupon(str(db_user["_id"]))
    await callback.answer("🎟️ Coupon removed.")
    # Redirect back to cart view
    from handlers.cart import view_cart
    await view_cart(callback, db=db, db_user=db_user)
