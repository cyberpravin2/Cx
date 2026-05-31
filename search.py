"""TeleStore — Product search handler."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.repos import ProductRepo, StoreRepo
from states.forms import SearchStates

router = Router(name="search")


@router.callback_query(F.data.startswith("search:start:"))
async def search_start(callback: CallbackQuery, state: FSMContext):
    store_id = callback.data.split(":")[2]
    await state.update_data(store_id=store_id)
    await state.set_state(SearchStates.entering_query)
    await callback.message.edit_text(
        "🔍 <b>Search Products</b>\n\nEnter a keyword to search:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SearchStates.entering_query)
async def do_search(message: Message, db, db_user, state: FSMContext):
    query = message.text.strip()
    data = await state.get_data()
    store_id = data.get("store_id")

    if not store_id:
        await state.clear()
        return

    product_repo = ProductRepo(db)
    results = await product_repo.search(store_id, query, limit=15)

    await state.clear()

    if not results:
        from keyboards.builders import back_to_store_kb
        await message.answer(
            f"🔍 No results for <b>{query}</b>",
            reply_markup=back_to_store_kb(store_id),
            parse_mode="HTML"
        )
        return

    text = f"🔍 Results for <b>{query}</b> — {len(results)} found:"
    from keyboards.builders import product_list_kb
    await message.answer(
        text,
        reply_markup=product_list_kb(store_id, results, show_back=True),
        parse_mode="HTML"
    )
