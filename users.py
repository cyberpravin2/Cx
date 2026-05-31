"""TeleStore — Admin user management."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.repos import UserRepo, OrderRepo, StoreRepo
from utils.helpers import is_admin
from states.forms import AdminUserStates

router = Router(name="admin_users")


@router.callback_query(F.data == "admin:users")
async def admin_users_menu(callback: CallbackQuery, db_user):
    if not is_admin(db_user):
        await callback.answer("⛔ No access.", show_alert=True)
        return

    from keyboards.builders import admin_users_menu_kb
    await callback.message.edit_text(
        "👥 <b>User Management</b>\n\nSearch for a user or view recent signups:",
        reply_markup=admin_users_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:users:search")
async def admin_users_search_start(callback: CallbackQuery, state: FSMContext, db_user):
    if not is_admin(db_user):
        await callback.answer("⛔", show_alert=True)
        return

    await state.set_state(AdminUserStates.searching)
    await callback.message.edit_text(
        "🔍 Enter username or user ID to search:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminUserStates.searching)
async def admin_users_search_result(message: Message, db, db_user, state: FSMContext):
    if not is_admin(db_user):
        await state.clear()
        return

    query = message.text.strip().lstrip("@")
    user_repo = UserRepo(db)

    # Try numeric ID first
    user = None
    if query.isdigit():
        user = await user_repo.get_by_telegram_id(int(query))
    if not user:
        user = await user_repo.get_by_username(query)

    await state.clear()

    if not user:
        await message.answer(f"❌ User not found: <code>{query}</code>", parse_mode="HTML")
        return

    await _show_user_detail(message, user, db)


async def _show_user_detail(target, user, db):
    order_repo = OrderRepo(db)
    store_repo = StoreRepo(db)
    total_orders = await order_repo.count_by_user(str(user["_id"]))
    owns_store = await store_repo.get_by_owner(str(user["_id"]))

    uid = user.get("telegram_id", "?")
    username = f"@{user['username']}" if user.get("username") else "No username"
    name = user.get("first_name", "Unknown")
    status = "🚫 Banned" if user.get("is_banned") else "✅ Active"

    text = (
        f"👤 <b>User Profile</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"👤 Name: {name}\n"
        f"📛 Username: {username}\n"
        f"Status: {status}\n"
        f"🛒 Orders: <b>{total_orders}</b>\n"
    )
    if owns_store:
        text += f"🏪 Owns store: <b>{owns_store['name']}</b>\n"

    from keyboards.builders import admin_user_detail_kb
    kb = admin_user_detail_kb(str(user["_id"]), user.get("is_banned", False))
    if hasattr(target, "message"):
        await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:user:ban:"))
async def admin_ban_user(callback: CallbackQuery, db, db_user):
    if not is_admin(db_user):
        await callback.answer("⛔", show_alert=True)
        return

    target_id = callback.data.split(":")[3]
    user_repo = UserRepo(db)
    await user_repo.set_banned(target_id, True)
    await callback.answer("🚫 User banned.")

    try:
        user = await user_repo.get_by_id(target_id)
        await callback.message.bot.send_message(
            chat_id=user["telegram_id"],
            text="🚫 You have been banned from this platform."
        )
    except Exception:
        pass

    from keyboards.builders import admin_user_detail_kb
    await callback.message.edit_reply_markup(
        reply_markup=admin_user_detail_kb(target_id, is_banned=True)
    )


@router.callback_query(F.data.startswith("admin:user:unban:"))
async def admin_unban_user(callback: CallbackQuery, db, db_user):
    if not is_admin(db_user):
        await callback.answer("⛔", show_alert=True)
        return

    target_id = callback.data.split(":")[3]
    user_repo = UserRepo(db)
    await user_repo.set_banned(target_id, False)
    await callback.answer("✅ User unbanned.")

    try:
        user = await user_repo.get_by_id(target_id)
        await callback.message.bot.send_message(
            chat_id=user["telegram_id"],
            text="✅ Your account has been restored. You can use the platform again."
        )
    except Exception:
        pass

    from keyboards.builders import admin_user_detail_kb
    await callback.message.edit_reply_markup(
        reply_markup=admin_user_detail_kb(target_id, is_banned=False)
    )
