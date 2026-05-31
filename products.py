"""TeleStore — Customer product browsing & detail handler."""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from bson import ObjectId

from database.repos import StoreRepo, ProductRepo, CartRepo

router = Router(name="products")


@router.callback_query(F.data.startswith("product:view:"))
async def view_product(callback: CallbackQuery, db, db_user):
    """Show product detail page."""
    product_id = callback.data.split(":")[2]
    product_repo = ProductRepo(db)
    product = await product_repo.get_by_id(product_id)
    if not product or not product.get("is_active", True):
        await callback.answer("Product not found or unavailable.", show_alert=True)
        return

    store_repo = StoreRepo(db)
    store = await store_repo.get_by_id(str(product["store_id"]))

    price_str = f"₹{product['price']:,.2f}"
    stock_str = ""
    if product.get("stock") is not None:
        if product["stock"] == 0:
            stock_str = "\n❌ <b>Out of stock</b>"
        else:
            stock_str = f"\n📦 Stock: <b>{product['stock']}</b>"

    lines = [
        f"🛍️ <b>{product['name']}</b>",
        "",
        f"💰 Price: <b>{price_str}</b>{stock_str}",
    ]
    if product.get("description"):
        lines += ["", product["description"]]
    if product.get("category"):
        lines.append(f"\n📂 Category: {product['category']}")

    text = "\n".join(lines)

    from keyboards.builders import product_detail_kb
    kb = product_detail_kb(
        product_id=product_id,
        store_id=str(product["store_id"]),
        out_of_stock=(product.get("stock") == 0),
    )

    if product.get("image_file_id"):
        await callback.message.answer_photo(
            photo=product["image_file_id"],
            caption=text,
            reply_markup=kb,
            parse_mode="HTML"
        )
        await callback.message.delete()
    else:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("product:add_cart:"))
async def add_to_cart_from_product(callback: CallbackQuery, db, db_user):
    """Add product to cart directly from product page."""
    product_id = callback.data.split(":")[2]
    product_repo = ProductRepo(db)
    product = await product_repo.get_by_id(product_id)
    if not product or not product.get("is_active", True):
        await callback.answer("Product not available.", show_alert=True)
        return

    if product.get("stock") == 0:
        await callback.answer("❌ Out of stock!", show_alert=True)
        return

    cart_repo = CartRepo(db)
    await cart_repo.add_item(
        user_id=str(db_user["_id"]),
        store_id=str(product["store_id"]),
        product_id=product_id,
        name=product["name"],
        price=product["price"],
        qty=1,
    )

    await callback.answer("✅ Added to cart!", show_alert=False)

    # Refresh product view with updated kb
    from keyboards.builders import product_detail_kb
    kb = product_detail_kb(
        product_id=product_id,
        store_id=str(product["store_id"]),
        out_of_stock=False,
        in_cart=True,
    )
    try:
        if callback.message.caption:
            await callback.message.edit_caption(
                caption=callback.message.caption,
                reply_markup=kb,
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass
