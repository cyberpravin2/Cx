"""TeleStore — Customer orders handler."""
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.repos import OrderRepo

router = Router(name="orders")

STATUS_EMOJI = {
    "pending": "⏳",
    "confirmed": "✅",
    "processing": "🔄",
    "shipped": "🚚",
    "delivered": "📦",
    "cancelled": "❌",
    "refunded": "💸",
}


@router.callback_query(F.data == "orders:list")
async def list_orders(callback: CallbackQuery, db, db_user):
    order_repo = OrderRepo(db)
    orders = await order_repo.list_by_user(str(db_user["_id"]), limit=10)

    if not orders:
        await callback.answer("You have no orders yet.", show_alert=True)
        return

    text = "📋 <b>Your Orders</b>\n\n"
    for o in orders:
        eid = str(o["_id"])[-8:].upper()
        emoji = STATUS_EMOJI.get(o.get("status", "pending"), "📦")
        text += (
            f"{emoji} <b>#{eid}</b> — ₹{o['total']:,.2f}\n"
            f"    {o.get('status','pending').title()}\n"
        )

    from keyboards.builders import orders_list_kb
    await callback.message.edit_text(
        text,
        reply_markup=orders_list_kb(orders),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order:view:"))
async def view_order(callback: CallbackQuery, db, db_user):
    order_id = callback.data.split(":")[2]
    order_repo = OrderRepo(db)
    order = await order_repo.get_by_id(order_id)

    if not order or str(order["user_id"]) != str(db_user["_id"]):
        await callback.answer("Order not found.", show_alert=True)
        return

    eid = str(order["_id"])[-8:].upper()
    emoji = STATUS_EMOJI.get(order.get("status", "pending"), "📦")

    lines = [
        f"📋 <b>Order #{eid}</b>",
        f"Status: {emoji} <b>{order.get('status','pending').title()}</b>",
        "",
        "<b>Items:</b>",
    ]
    for item in order.get("items", []):
        lines.append(f"• {item['name']} × {item['qty']} — ₹{item['price'] * item['qty']:,.2f}")

    lines += [
        "",
        f"💰 Total: <b>₹{order['total']:,.2f}</b>",
        f"💳 Payment: {order.get('payment_method','—').upper()}",
    ]

    if order.get("delivery_link"):
        lines += ["", f"📥 <a href=\"{order['delivery_link']}\">Download / Access</a>"]

    from keyboards.builders import order_detail_kb
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=order_detail_kb(order_id),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()
