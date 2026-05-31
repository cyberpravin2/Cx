"""TeleStore — Admin payment overview."""
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.repos import PaymentRepo, OrderRepo
from utils.helpers import is_admin

router = Router(name="admin_payments")


@router.callback_query(F.data == "admin:payments")
async def admin_payments_overview(callback: CallbackQuery, db, db_user):
    if not is_admin(db_user):
        await callback.answer("⛔", show_alert=True)
        return

    payment_repo = PaymentRepo(db)
    pending = await payment_repo.count_by_status("pending")
    confirmed = await payment_repo.count_by_status("confirmed")
    failed = await payment_repo.count_by_status("failed")

    recent = await payment_repo.list_recent(limit=10)

    lines = [
        "💳 <b>Payment Overview</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        f"⏳ Pending: <b>{pending}</b>",
        f"✅ Confirmed: <b>{confirmed}</b>",
        f"❌ Failed: <b>{failed}</b>",
        "",
        "<b>Recent Payments:</b>",
    ]

    METHOD_EMOJI = {"upi": "📲", "oxapay": "🔗", "stars": "⭐"}
    STATUS_EMOJI = {"pending": "⏳", "confirmed": "✅", "failed": "❌"}
    for p in recent:
        m = METHOD_EMOJI.get(p.get("method", ""), "💳")
        s = STATUS_EMOJI.get(p.get("status", ""), "❓")
        pid = str(p["_id"])[-6:].upper()
        lines.append(f"{m} {s} <code>#{pid}</code> ₹{p.get('amount',0):,.2f}")

    from keyboards.builders import admin_payments_kb
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_payments_kb(),
        parse_mode="HTML"
    )
    await callback.answer()
