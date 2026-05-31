"""TeleStore — Super admin main panel."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from utils.helpers import is_admin
from database.repos import UserRepo, StoreRepo, OrderRepo, AnalyticsRepo

router = Router(name="admin_panel")


async def _admin_stats(db) -> dict:
    user_repo = UserRepo(db)
    store_repo = StoreRepo(db)
    order_repo = OrderRepo(db)

    total_users = await user_repo.count()
    total_stores = await store_repo.count()
    active_stores = await store_repo.count_active()
    total_orders = await order_repo.count_all()

    analytics_repo = AnalyticsRepo(db)
    today_revenue = await analytics_repo.platform_revenue_today()
    month_revenue = await analytics_repo.platform_revenue_month()

    return {
        "total_users": total_users,
        "total_stores": total_stores,
        "active_stores": active_stores,
        "total_orders": total_orders,
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
    }


@router.message(Command("admin"))
async def admin_command(message: Message, db, db_user):
    if not is_admin(db_user):
        return

    stats = await _admin_stats(db)
    text = (
        f"🛡️ <b>Admin Panel</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Users: <b>{stats['total_users']:,}</b>\n"
        f"🏪 Stores: <b>{stats['total_stores']:,}</b> "
        f"(<b>{stats['active_stores']}</b> active)\n"
        f"🛒 Orders: <b>{stats['total_orders']:,}</b>\n\n"
        f"💰 Today: <b>₹{stats['today_revenue']:,.2f}</b>\n"
        f"📈 This month: <b>₹{stats['month_revenue']:,.2f}</b>"
    )
    from keyboards.builders import admin_main_kb
    await message.answer(text, reply_markup=admin_main_kb(), parse_mode="HTML")


@router.callback_query(F.data == "admin:panel")
async def admin_panel_cb(callback: CallbackQuery, db, db_user):
    if not is_admin(db_user):
        await callback.answer("⛔ No access.", show_alert=True)
        return

    stats = await _admin_stats(db)
    text = (
        f"🛡️ <b>Admin Panel</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Users: <b>{stats['total_users']:,}</b>\n"
        f"🏪 Stores: <b>{stats['total_stores']:,}</b> "
        f"(<b>{stats['active_stores']}</b> active)\n"
        f"🛒 Orders: <b>{stats['total_orders']:,}</b>\n\n"
        f"💰 Today: <b>₹{stats['today_revenue']:,.2f}</b>\n"
        f"📈 This month: <b>₹{stats['month_revenue']:,.2f}</b>"
    )
    from keyboards.builders import admin_main_kb
    await callback.message.edit_text(text, reply_markup=admin_main_kb(), parse_mode="HTML")
    await callback.answer()
