"""TeleStore — Shopping cart handler."""
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.repos import CartRepo, ProductRepo, CouponRepo

router = Router(name="cart")


def _cart_summary(cart, coupon=None) -> tuple[str, float]:
    """Return (text, final_total)."""
    if not cart or not cart.get("items"):
        return "🛒 Your cart is empty.", 0.0

    lines = ["🛒 <b>Your Cart</b>\n"]
    subtotal = 0.0
    for item in cart["items"]:
        line_total = item["price"] * item["qty"]
        subtotal += line_total
        lines.append(
            f"• {item['name']}\n"
            f"  {item['qty']} × ₹{item['price']:,.2f} = <b>₹{line_total:,.2f}</b>"
        )

    lines.append(f"\n💵 Subtotal: <b>₹{subtotal:,.2f}</b>")

    discount = 0.0
    if coupon:
        if coupon["type"] == "percentage":
            discount = subtotal * coupon["value"] / 100
        else:
            discount = min(coupon["value"], subtotal)
        lines.append(f"🎟️ Coupon <code>{coupon['code']}</code>: -₹{discount:,.2f}")

    final = subtotal - discount
    lines.append(f"\n💰 Total: <b>₹{final:,.2f}</b>")
    return "\n".join(lines), final


@router.callback_query(F.data == "cart:view")
async def view_cart(callback: CallbackQuery, db, db_user):
    cart_repo = CartRepo(db)
    cart = await cart_repo.get(str(db_user["_id"]))

    coupon = None
    if cart and cart.get("coupon_code"):
        coupon_repo = CouponRepo(db)
        coupon = await coupon_repo.get_by_code(cart["coupon_code"])

    text, total = _cart_summary(cart, coupon)
    store_id = cart["store_id"] if cart else None

    from keyboards.builders import cart_kb
    kb = cart_kb(
        items=cart.get("items", []) if cart else [],
        store_id=store_id,
        has_coupon=bool(coupon),
        total=total,
    )
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("cart:remove:"))
async def remove_from_cart(callback: CallbackQuery, db, db_user):
    product_id = callback.data.split(":")[2]
    cart_repo = CartRepo(db)
    await cart_repo.remove_item(str(db_user["_id"]), product_id)
    await callback.answer("🗑️ Item removed.")

    # Refresh cart view
    cart = await cart_repo.get(str(db_user["_id"]))
    text, total = _cart_summary(cart)
    store_id = cart["store_id"] if cart else None

    from keyboards.builders import cart_kb
    kb = cart_kb(
        items=cart.get("items", []) if cart else [],
        store_id=store_id,
        has_coupon=False,
        total=total,
    )
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("cart:qty:"))
async def change_qty(callback: CallbackQuery, db, db_user):
    """cart:qty:<product_id>:<+1|-1>"""
    parts = callback.data.split(":")
    product_id = parts[2]
    delta = int(parts[3])

    cart_repo = CartRepo(db)
    cart = await cart_repo.get(str(db_user["_id"]))
    if not cart:
        await callback.answer("Cart is empty.", show_alert=True)
        return

    item = next((i for i in cart["items"] if i["product_id"] == product_id), None)
    if not item:
        await callback.answer("Item not in cart.", show_alert=True)
        return

    new_qty = item["qty"] + delta
    if new_qty <= 0:
        await cart_repo.remove_item(str(db_user["_id"]), product_id)
        await callback.answer("🗑️ Item removed.")
    else:
        # Check stock
        product_repo = ProductRepo(db)
        product = await product_repo.get_by_id(product_id)
        if product and product.get("stock") is not None and new_qty > product["stock"]:
            await callback.answer(f"⚠️ Only {product['stock']} in stock.", show_alert=True)
            return
        await cart_repo.update_qty(str(db_user["_id"]), product_id, new_qty)
        await callback.answer()

    cart = await cart_repo.get(str(db_user["_id"]))
    text, total = _cart_summary(cart)
    store_id = cart["store_id"] if cart else None

    from keyboards.builders import cart_kb
    kb = cart_kb(
        items=cart.get("items", []) if cart else [],
        store_id=store_id,
        has_coupon=False,
        total=total,
    )
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "cart:clear")
async def clear_cart(callback: CallbackQuery, db, db_user):
    cart_repo = CartRepo(db)
    await cart_repo.clear(str(db_user["_id"]))
    await callback.answer("🗑️ Cart cleared.")
    await callback.message.edit_text(
        "🛒 Your cart is empty.",
        parse_mode="HTML"
    )
