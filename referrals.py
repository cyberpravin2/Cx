"""TeleStore — Customer referral handler."""
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.repos import ReferralRepo, StoreRepo, UserRepo
from config.settings import settings

router = Router(name="referrals")


@router.callback_query(F.data.startswith("referral:view:"))
async def view_referral(callback: CallbackQuery, db, db_user):
    store_id = callback.data.split(":")[2]
    store_repo = StoreRepo(db)
    store = await store_repo.get_by_id(store_id)
    if not store:
        await callback.answer("Store not found.", show_alert=True)
        return

    referral_repo = ReferralRepo(db)
    ref_config = await referral_repo.get_config(store_id)
    ref_stats = await referral_repo.get_user_stats(store_id, str(db_user["_id"]))

    bot_username = settings.BOT_USERNAME
    ref_link = f"https://t.me/{bot_username}?start=ref_{store_id}_{db_user['_id']}"

    reward_text = ""
    if ref_config:
        if ref_config.get("reward_type") == "discount":
            reward_text = f"🎁 Reward: {ref_config['reward_value']}% discount coupon"
        elif ref_config.get("reward_type") == "cashback":
            reward_text = f"💰 Reward: ₹{ref_config['reward_value']} cashback"

    lines = [
        f"🤝 <b>Referral Program</b>",
        f"🏪 {store['name']}",
        "",
        f"Your referral link:",
        f"<code>{ref_link}</code>",
        "",
    ]
    if reward_text:
        lines += [reward_text, ""]
    if ref_stats:
        lines += [
            f"📊 <b>Your Stats</b>",
            f"👥 Referred: <b>{ref_stats.get('total_referrals', 0)}</b>",
            f"✅ Converted: <b>{ref_stats.get('conversions', 0)}</b>",
            f"🏆 Rewards earned: <b>{ref_stats.get('rewards_earned', 0)}</b>",
        ]

    from keyboards.builders import referral_kb
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=referral_kb(store_id, ref_link),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("referral:leaderboard:"))
async def referral_leaderboard(callback: CallbackQuery, db, db_user):
    store_id = callback.data.split(":")[2]
    referral_repo = ReferralRepo(db)
    top = await referral_repo.get_leaderboard(store_id, limit=10)

    lines = ["🏆 <b>Referral Leaderboard</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, entry in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = entry.get("username") or entry.get("first_name") or f"User{i+1}"
        lines.append(f"{medal} @{name} — <b>{entry.get('total_referrals',0)}</b> referrals")

    if not top:
        lines.append("No referrals yet. Be the first!")

    from keyboards.builders import back_to_store_kb
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_store_kb(store_id),
        parse_mode="HTML"
    )
    await callback.answer()
