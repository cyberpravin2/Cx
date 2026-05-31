"""TeleStore — Customer support ticket handler."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.repos import TicketRepo, StoreRepo
from states.forms import TicketStates

router = Router(name="tickets")


@router.callback_query(F.data.startswith("ticket:create:"))
async def ticket_create_start(callback: CallbackQuery, state: FSMContext):
    store_id = callback.data.split(":")[2]
    await state.update_data(store_id=store_id)
    await state.set_state(TicketStates.entering_subject)
    await callback.message.edit_text(
        "🎫 <b>Create Support Ticket</b>\n\n"
        "Enter the subject of your issue:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(TicketStates.entering_subject)
async def ticket_subject(message: Message, state: FSMContext):
    subject = message.text.strip()
    if len(subject) < 3:
        await message.answer("⚠️ Subject too short. Please enter at least 3 characters:")
        return
    await state.update_data(subject=subject)
    await state.set_state(TicketStates.entering_message)
    await message.answer(
        f"📝 Subject: <b>{subject}</b>\n\n"
        f"Now describe your issue in detail. You may also attach a photo:",
        parse_mode="HTML"
    )


@router.message(TicketStates.entering_message)
async def ticket_message(message: Message, db, db_user, state: FSMContext):
    data = await state.get_data()
    store_id = data["store_id"]
    subject = data["subject"]

    body = message.text or message.caption or ""
    media_file_id = None
    if message.photo:
        media_file_id = message.photo[-1].file_id
    elif message.document:
        media_file_id = message.document.file_id

    ticket_repo = TicketRepo(db)
    ticket = await ticket_repo.create(
        user_id=str(db_user["_id"]),
        store_id=store_id,
        subject=subject,
        body=body,
        media_file_id=media_file_id,
    )

    # Notify store owner
    store_repo = StoreRepo(db)
    store = await store_repo.get_by_id(store_id)
    if store:
        from services.notifications import notify_owner_new_ticket
        await notify_owner_new_ticket(message.bot, db, ticket, db_user, store)

    await state.clear()
    ticket_id = str(ticket["_id"])[-8:].upper()
    await message.answer(
        f"✅ <b>Ticket created!</b>\n\n"
        f"🎫 Ticket ID: <code>{ticket_id}</code>\n"
        f"📌 Subject: {subject}\n\n"
        f"The store owner will reply shortly.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "tickets:list")
async def list_tickets(callback: CallbackQuery, db, db_user):
    ticket_repo = TicketRepo(db)
    tickets = await ticket_repo.list_by_user(str(db_user["_id"]), limit=10)

    if not tickets:
        await callback.answer("You have no support tickets.", show_alert=True)
        return

    STATUS_EMOJI = {"open": "🟢", "closed": "🔴", "replied": "💬"}
    lines = ["🎫 <b>Your Support Tickets</b>\n"]
    for t in tickets:
        tid = str(t["_id"])[-8:].upper()
        emoji = STATUS_EMOJI.get(t.get("status", "open"), "🎫")
        lines.append(f"{emoji} <b>#{tid}</b> — {t['subject']}")

    from keyboards.builders import tickets_list_kb
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=tickets_list_kb(tickets),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ticket:view:"))
async def view_ticket(callback: CallbackQuery, db, db_user):
    ticket_id = callback.data.split(":")[2]
    ticket_repo = TicketRepo(db)
    ticket = await ticket_repo.get_by_id(ticket_id)

    if not ticket or str(ticket["user_id"]) != str(db_user["_id"]):
        await callback.answer("Ticket not found.", show_alert=True)
        return

    tid = str(ticket["_id"])[-8:].upper()
    STATUS_EMOJI = {"open": "🟢", "closed": "🔴", "replied": "💬"}
    emoji = STATUS_EMOJI.get(ticket.get("status", "open"), "🎫")

    lines = [
        f"🎫 <b>Ticket #{tid}</b>",
        f"Status: {emoji} {ticket.get('status','open').title()}",
        f"Subject: <b>{ticket['subject']}</b>",
        "",
        f"<b>Messages:</b>",
    ]
    for msg in ticket.get("messages", []):
        sender = "You" if msg.get("from_user") else "Support"
        lines.append(f"\n👤 <b>{sender}:</b>\n{msg.get('body','')}")

    from keyboards.builders import ticket_detail_kb
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=ticket_detail_kb(ticket_id, ticket.get("status")),
        parse_mode="HTML"
    )
    await callback.answer()
