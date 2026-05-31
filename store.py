"""TeleStore — Customer store browsing handler."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database.repos import StoreRepo, ProductRepo

router = Router(name="store")


async def show_store_welcome(message: Message, store, user, db):
    """Display the store welcome screen."""
    product_repo = ProductRepo(db)
    total_products = await product_repo.count_active(str(store["_id"]))

    caption_lines = [
        f"🏪 <b>{store['name']}</b>",
        "",
    ]
    if store.get("welcome_caption"):
        caption_lines.append(store["welcome_caption"])
        caption_lines.append("")
    caption_lines += [
        f"📦 <b>{total_products}</b> products available",
    ]
    if store.get("support_username"):
        caption_lines.append(f"💬 Support: @{store['support_username']}")

    caption = "\n".join(caption_lines)
    from keyboards.builders import store_welcome_kb
    kb = store_welcome_kb(str(store["_id"]))

    if store.get("banner_file_id"):
        await message.answer_photo(
            photo=store["banner_file_id"],
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )
    elif store.get("logo_file_id"):
        await message.answer_photo(
            photo=store["logo_file_id"],
            caption=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        await message.answer(caption, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("store:browse:"))
async def browse_store(callback: CallbackQuery, db, db_user):
    store_id = callback.data.split(":")[2]
    store_repo = StoreRepo(db)
    store = await store_repo.get_by_id(store_id)
    if not store:
        await callback.answer("Store not found.", show_alert=True)
        return

    product_repo = ProductRepo(db)
    categories = await product_repo.get_categories(store_id)

    if categories:
        text = (
            f"🏪 <b>{store['name']}</b>\n\n"
            f"📂 <b>Browse Categories</b>\n"
            f"Choose a category to explore:"
        )
        from keyboards.builders import category_list_kb
        kb = category_list_kb(store_id, categories)
    else:
        products = await product_repo.list_active(store_id, limit=20)
        if not products:
            await callback.answer("No products available yet.", show_alert=True)
            return
        text = f"🏪 <b>{store['name']}</b>\n\n📦 <b>All Products</b>"
        from keyboards.builders import product_list_kb
        kb = product_list_kb(store_id, products)

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("store:category:"))
async def browse_category(callback: CallbackQuery, db, db_user):
    parts = callback.data.split(":")
    store_id = parts[2]
    category = parts[3] if len(parts) > 3 else None

    store_repo = StoreRepo(db)
    store = await store_repo.get_by_id(store_id)
    if not store:
        await callback.answer("Store not found.", show_alert=True)
        return

    product_repo = ProductRepo(db)
    products = await product_repo.list_active(store_id, category=category, limit=20)
    if not products:
        await callback.answer("No products in this category.", show_alert=True)
        return

    cat_name = category or "All Products"
    text = (
        f"📂 <b>{cat_name}</b>\n"
        f"🏪 {store['name']}\n\n"
        f"Found <b>{len(products)}</b> product(s):"
    )
    from keyboards.builders import product_list_kb
    kb = product_list_kb(store_id, products, category=category)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("store:info:"))
async def store_info(callback: CallbackQuery, db, db_user):
    store_id = callback.data.split(":")[2]
    store_repo = StoreRepo(db)
    store = await store_repo.get_by_id(store_id)
    if not store:
        await callback.answer("Store not found.", show_alert=True)
        return

    product_repo = ProductRepo(db)
    total = await product_repo.count_active(store_id)
    lines = [f"ℹ️ <b>About {store['name']}</b>", ""]
    if store.get("welcome_caption"):
        lines += [store["welcome_caption"], ""]
    lines += [f"📦 Products: <b>{total}</b>"]
    if store.get("support_username"):
        lines.append(f"💬 Support: @{store['support_username']}")

    from keyboards.builders import back_to_store_kb
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_store_kb(store_id),
        parse_mode="HTML"
    )
    await callback.answer()
