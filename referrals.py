"""TeleStore — Owner referral config & leaderboard."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.repos import ReferralRepo, UserRepo
from states.forms import ReferralConfigStates

router = Router(name="owner_referrals")


@router.callback_query(F.data == "owner:referrals")
async def owner_referrals_menu(callback: CallbackQuery, db, db_user, owner_store):
    if not owner_store:
        await callback.answer("No store.", show_alert=True)
        return

    referral_repo = ReferralRepo(db)
    config = await referral_repo.get_config(str(owner_store["_id"]))
    stats = await referral_repo.get_store_stats(str(owner_store["_id"]))

    total_refs = stats.get("total_referrals", 0)
    total_conversions = stats.get("conversions", 0)

    reward_text = "❌ Not configured"
    if config:
        if config.get("reward_type") == "discount":
            reward_text = f"🎁 {config['reward_value']}% discount"
        elif config.get("reward_type") == "cashback":
            reward_text = f"💰 ₹{config['reward_value']} cashback"

    text = (
        f"🤝 <b>Referral Program</b>\n"
        f"🏪 {owner_store['name']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Reward: {reward_text}\n\n"
        f"📊 Total referrals: <b>{total_refs}</b>\n"
        f"✅ Conversions: <b>{total_conversions}</b>\n"
    )

    from keyboards.builders import owner_referrals_kb
    await callback.message.edit_text(text, reply_markup=owner_referrals_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "owner:referrals:config")
async def owner_referral_config_start(callback: CallbackQuery, state: FSMContext, db_user):
    await state.set_state(ReferralConfigStates.selecting_type)
    from keyboards.builders import referral_reward_type_kb
    await callback.message.edit_text(
        "🎁 <b>Configure Referral Reward</b>\n\nSelect the reward type:",
        reply_markup=referral_reward_type_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("referral:type:"), ReferralConfigStates.selecting_type)
async def referral_type_selected(callback: CallbackQuery, state: FSMContext):
    reward_type = callback.data.split(":")[2]
    await state.update_data(reward_type=reward_type)
    await state.set_state(ReferralConfigStates.entering_value)

    if reward_type == "discount":
        prompt = "Enter discount percentage (e.g. 10 for 10%):"
    else:
        prompt = "Enter cashback amount in ₹ (e.g. 50):"

    await callback.message.edit_text(f"🎁 <b>Reward Value</b>\n\n{prompt}", parse_mode="HTML")
    await callback.answer()


@router.message(ReferralConfigStates.entering_value)
async def referral_value_entered(message: Message, db, db_user, state: FSMContext, owner_store):
    if not owner_store:
        await state.clear()
        return

    try:
        value = float(message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Please enter a valid positive number:")
        return

    data = await state.get_data()
    reward_type = data["reward_type"]

    referral_repo = ReferralRepo(db)
    await referral_repo.set_config(
        store_id=str(owner_store["_id"]),
        reward_type=reward_type,
        reward_value=value,
    )

    await state.clear()
    reward_str = f"{value:.0f}% discount" if reward_type == "discount" else f"₹{value:.2f} cashback"
    await message.answer(
        f"✅ <b>Referral reward configured!</b>\n\n"
        f"🎁 Reward: {reward_str}\n\n"
        f"Customers who refer others will earn this reward.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "owner:referrals:leaderboard")
async def owner_referral_leaderboard(callback: CallbackQuery, db, db_user, owner_store):
    if not owner_store:
        await callback.answer("No store.", show_alert=True)
        return

    referral_repo = ReferralRepo(db)
    top = await referral_repo.get_leaderboard(str(owner_store["_id"]), limit=10)

    lines = [f"🏆 <b>Referral Leaderboard</b>\n🏪 {owner_store['name']}\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, entry in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = entry.get("username") or entry.get("first_name") or f"User{i+1}"
        refs = entry.get("total_referrals", 0)
        conversions = entry.get("conversions", 0)
        lines.append(f"{medal} @{name} — <b>{refs}</b> refs ({conversions} converted)")

    if not top:
        lines.append("No referrals yet.")

    from keyboards.builders import owner_referrals_kb
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=owner_referrals_kb(),
        parse_mode="HTML"
    )
    await callback.answer()
