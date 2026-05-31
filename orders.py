"""TeleStore — Owner order management."""
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.repos import OrderRepo, PaymentRepo, UserRepo
from utils.helpers import is_owner
from services.delivery import DeliveryService

router = Router(name="owner_orders")

STATUS_EMOJI = {
    "pending": "⏳", "confirmed": "✅", "processing": "🔄",
    "shipped": "🚚", "delivered": "📦", "cancelled": "❌", "refunded": "💸"
}


@router.callback_query(F.data == "owner:orders")
async def owner_orders_list(callback: CallbackQuery, db, db_user, owner_store):
    if not owner_store:
        await callback.answer("No store found.", show_alert=True)
        return

    order_repo = OrderRepo(db)
    orders = await order_repo.list_by_store(str(owner_store["_id"]), limit=20)

    if not orders:
        await callback.answer("No orders yet.", show_alert=True)
        return

    lines = [f"🛒 <b>Orders</b> — {owner_store['name']}\n"]
    for o in orders:
        eid = str(o["_id"])[-8:].upper()
        emoji = STATUS_EMOJI.get(o.get("status", "pending"), "📦")
        lines.append(f"{emoji} <b>#{eid}</b> — ₹{o['total']:,.2f} — {o.get('status','pending').title()}")

    from keyboards.builders import owner_orders_list_kb
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=owner_orders_list_kb(orders),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("owner:order:view:"))
async def owner_view_order(callback: CallbackQuery, db, db_user, owner_store):
    if not owner_store:
        await callback.answer("No store.", show_alert=True)
        return

    order_id = callback.data.split(":")[3]
    order_repo = OrderRepo(db)
    order = await order_repo.get_by_id(order_id)
    if not order or str(order["store_id"]) != str(owner_store["_id"]):
        await callback.answer("Order not found.", show_alert=True)
        return

    user_repo = UserRepo(db)
    customer = await user_repo.get_by_id(str(order["user_id"]))
    customer_str = f"@{customer['username']}" if customer and customer.get("username") else f"User {order['user_id']}"

    eid = str(order["_id"])[-8:].upper()
    emoji = STATUS_EMOJI.get(order.get("status", "pending"), "📦")

    lines = [
        f"🛒 <b>Order #{eid}</b>",
        f"Status: {emoji} {order.get('status','pending').title()}",
        f"👤 Customer: {customer_str}",
        f"💳 Payment: {order.get('payment_method','—').upper()}",
        "",
        "<b>Items:</b>",
    ]
    for item in order.get("items", []):
        lines.append(f"• {item['name']} × {item['qty']} — ₹{item['price'] * item['qty']:,.2f}")
    lines += ["", f"💰 Total: <b>₹{order['total']:,.2f}</b>"]

    if order.get("coupon_code"):
        lines.append(f"🎟️ Coupon: {order['coupon_code']}")

    from keyboards.builders import owner_order_detail_kb
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=owner_order_detail_kb(order_id, order.get("status", "pending")),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("owner:order:status:"))
async def owner_update_order_status(callback: CallbackQuery, db, db_user, owner_store):
    if not owner_store:
        await callback.answer("No store.", show_alert=True)
        return

    parts = callback.data.split(":")
    order_id = parts[3]
    new_status = parts[4]

    order_repo = OrderRepo(db)
    order = await order_repo.get_by_id(order_id)
    if not order or str(order["store_id"]) != str(owner_store["_id"]):
        await callback.answer("Order not found.", show_alert=True)
        return

    await order_repo.update_status(order_id, new_status)
    await callback.answer(f"✅ Status → {new_status.title()}")

    # Notify customer
    user_repo = UserRepo(db)
    customer = await user_repo.get_by_id(str(order["user_id"]))
    if customer:
        eid = str(order["_id"])[-8:].upper()
        emoji = STATUS_EMOJI.get(new_status, "📦")
        try:
            await callback.message.bot.send_message(
                chat_id=customer["telegram_id"],
                text=(
                    f"{emoji} <b>Order Update</b>\n\n"
                    f"Order #{eid} is now <b>{new_status.title()}</b>."
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass

    # If delivered, trigger delivery link
    if new_status == "delivered":
        delivery_svc = DeliveryService()
        await delivery_svc.send_delivery(callback.message.bot, order, customer)

    from keyboards.builders import owner_order_detail_kb
    await callback.message.edit_reply_markup(
        reply_markup=owner_order_detail_kb(order_id, new_status)
    )


@router.callback_query(F.data.startswith("owner:orders:filter:"))
async def owner_filter_orders(callback: CallbackQuery, db, db_user, owner_store):
    if not owner_store:
        await callback.answer("No store.", show_alert=True)
        return

    status_filter = callback.data.split(":")[3]
    order_repo = OrderRepo(db)
    orders = await order_repo.list_by_store(
        str(owner_store["_id"]),
        status=status_filter,
        limit=20
    )

    if not orders:
        await callback.answer(f"No {status_filter} orders.", show_alert=True)
        return

    emoji = STATUS_EMOJI.get(status_filter, "📦")
    lines = [f"{emoji} <b>{status_filter.title()} Orders</b>\n"]
    for o in orders:
        eid = str(o["_id"])[-8:].upper()
        lines.append(f"• <b>#{eid}</b> — ₹{o['total']:,.2f}")

    from keyboards.builders import owner_orders_list_kb
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=owner_orders_list_kb(orders),
        parse_mode="HTML"
    )
    await callback.answer()
