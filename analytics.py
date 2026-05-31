"""TeleStore — Admin platform-wide analytics."""
from aiogram import Router, F
from aiogram.types import CallbackQuery
import datetime

from database.repos import AnalyticsRepo, OrderRepo, UserRepo, StoreRepo
from utils.helpers import is_admin

router = Router(name="admin_analytics")


@router.callback_query(F.data == "admin:analytics")
async def admin_analytics_menu(callback: CallbackQuery, db, db_user):
    if not is_admin(db_user):
        await callback.answer("⛔", show_alert=True)
        return

    from keyboards.builders import admin_analytics_period_kb
    await callback.message.edit_text(
        "📊 <b>Platform Analytics</b>\n\nSelect a time period:",
        reply_markup=admin_analytics_period_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:analytics:"))
async def admin_analytics_period(callback: CallbackQuery, db, db_user):
    if not is_admin(db_user):
        await callback.answer("⛔", show_alert=True)
        return

    period = callback.data.split(":")[2]
    analytics_repo = AnalyticsRepo(db)
    order_repo = OrderRepo(db)
    user_repo = UserRepo(db)
    store_repo = StoreRepo(db)

    now = datetime.datetime.utcnow()
    if period == "today":
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
        label = "Today"
    elif period == "week":
        since = now - datetime.timedelta(days=7)
        label = "Last 7 Days"
    elif period == "month":
        since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        label = "This Month"
    else:  # year
        since = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        label = "This Year"

    revenue = await analytics_repo.platform_revenue_since(since)
    orders = await order_repo.count_since(since)
    new_users = await user_repo.count_since(since)
    new_stores = await store_repo.count_since(since)

    # Top stores by revenue
    top_stores = await analytics_repo.top_stores_since(since, limit=5)

    lines = [
        f"📊 <b>Platform Analytics — {label}</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"",
        f"💰 Revenue: <b>₹{revenue:,.2f}</b>",
        f"🛒 Orders: <b>{orders:,}</b>",
        f"👥 New users: <b>{new_users:,}</b>",
        f"🏪 New stores: <b>{new_stores:,}</b>",
    ]

    if top_stores:
        lines += ["", "🏆 <b>Top Stores:</b>"]
        for i, s in enumerate(top_stores, 1):
            lines.append(f"  {i}. {s['name']} — ₹{s.get('revenue', 0):,.2f}")

    # 7-day bar chart
    if period in ("week", "today"):
        daily = await analytics_repo.daily_revenue_since(since, days=7)
        if daily:
            max_val = max(daily.values()) if daily else 1
            lines += ["", "📈 <b>Daily Revenue:</b>"]
            for day_str, val in sorted(daily.items())[-7:]:
                bar_len = int((val / max_val) * 10) if max_val > 0 else 0
                bar = "█" * bar_len + "░" * (10 - bar_len)
                short_day = day_str[-5:]
                lines.append(f"  {short_day} {bar} ₹{val:,.0f}")

    from keyboards.builders import admin_analytics_period_kb
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_analytics_period_kb(),
        parse_mode="HTML"
    )
    await callback.answer()
