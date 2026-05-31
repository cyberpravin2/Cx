"""TeleStore — Admin store management."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.repos import StoreRepo, UserRepo, OrderRepo
from utils.helpers import is_admin
from states.forms import AdminStoreStates

router = Router(name="admin_stores")


@router.callback_query(F.data == "admin:stores")
async def admin_stores_list(callback: CallbackQuery, db, db_user):
    if not is_admin(db_user):
        await callback.answer("⛔ No access.", show_alert=True)
        return

    store_repo = StoreRepo(db)
    stores = await store_repo.list_all(limit=20)
    total = await store_repo.count()

    lines = [f"🏪 <b>All Stores</b> ({total} total)\n"]
    for s in stores:
        status = "✅" if s.get("is_active", True) else "🚫"
        lines.append(f"{status} <b>{s['name']}</b> — /store_{str(s['_id'])[-6:]}")

    from keyboards.builders import admin_stores_list_kb
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_stores_list_kb(stores),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:store:view:"))
async def admin_view_store(callback: CallbackQuery, db, db_user):
    if not is_admin(db_user):
        await callback.answer("⛔ No access.", show_alert=True)
        return

    store_id = callback.data.split(":")[3]
    store_repo = StoreRepo(db)
    store = await store_repo.get_by_id(store_id)
    if not store:
        await callback.answer("Store not found.", show_alert=True)
        return

    user_repo = UserRepo(db)
    owner = await user_repo.get_by_id(str(store["owner_id"]))
    order_repo = OrderRepo(db)
    total_orders = await order_repo.count_by_store(store_id)

    owner_str = f"@{owner['username']}" if owner and owner.get("username") else str(store["owner_id"])
    status_str = "✅ Active" if store.get("is_active", True) else "🚫 Suspended"

    text = (
        f"🏪 <b>{store['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Owner: {owner_str}\n"
        f"Status: {status_str}\n"
        f"🛒 Total orders: <b>{total_orders}</b>\n"
    )
    if store.get("support_username"):
        text += f"💬 Support: @{store['support_username']}\n"

    from keyboards.builders import admin_store_detail_kb
    await callback.message.edit_text(
        text,
        reply_markup=admin_store_detail_kb(store_id, store.get("is_active", True)),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:store:suspend:"))
async def admin_suspend_store(callback: CallbackQuery, db, db_user):
    if not is_admin(db_user):
        await callback.answer("⛔", show_alert=True)
        return

    store_id = callback.data.split(":")[3]
    store_repo = StoreRepo(db)
    await store_repo.set_active(store_id, False)
    await callback.answer("🚫 Store suspended.")

    # Notify owner
    store = await store_repo.get_by_id(store_id)
    if store:
        try:
            await callback.message.bot.send_message(
                chat_id=store["owner_id"],
                text=(
                    f"🚫 <b>Your store has been suspended</b>\n\n"
                    f"Store: <b>{store['name']}</b>\n"
                    f"Contact platform support for more info."
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass

    # Reload store detail
    from keyboards.builders import admin_store_detail_kb
    await callback.message.edit_reply_markup(
        reply_markup=admin_store_detail_kb(store_id, is_active=False)
    )


@router.callback_query(F.data.startswith("admin:store:activate:"))
async def admin_activate_store(callback: CallbackQuery, db, db_user):
    if not is_admin(db_user):
        await callback.answer("⛔", show_alert=True)
        return

    store_id = callback.data.split(":")[3]
    store_repo = StoreRepo(db)
    await store_repo.set_active(store_id, True)
    await callback.answer("✅ Store activated.")

    store = await store_repo.get_by_id(store_id)
    if store:
        try:
            await callback.message.bot.send_message(
                chat_id=store["owner_id"],
                text=(
                    f"✅ <b>Your store has been reactivated</b>\n\n"
                    f"Store: <b>{store['name']}</b>\n"
                    f"You're back in business! 🎉"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass

    from keyboards.builders import admin_store_detail_kb
    await callback.message.edit_reply_markup(
        reply_markup=admin_store_detail_kb(store_id, is_active=True)
    )


@router.callback_query(F.data.startswith("admin:store:delete:"))
async def admin_delete_store(callback: CallbackQuery, db, db_user):
    if not is_admin(db_user):
        await callback.answer("⛔", show_alert=True)
        return

    store_id = callback.data.split(":")[3]
    store_repo = StoreRepo(db)
    await store_repo.delete(store_id)
    await callback.answer("🗑️ Store deleted.")

    from keyboards.builders import admin_main_kb
    await callback.message.edit_text(
        "🗑️ Store deleted successfully.",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )
