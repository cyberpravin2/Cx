"""TeleStore — Customer checkout & payment handler."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, ContentType
from aiogram.fsm.context import FSMContext

from database.repos import CartRepo, OrderRepo, PaymentRepo, StoreRepo, CouponRepo
from services.payments import UPIService, OxaPayService, StarsService
from states.forms import CheckoutStates

router = Router(name="payments")


@router.callback_query(F.data == "checkout:start")
async def checkout_start(callback: CallbackQuery, db, db_user, state: FSMContext):
    """Begin checkout — show payment method selector."""
    cart_repo = CartRepo(db)
    cart = await cart_repo.get(str(db_user["_id"]))
    if not cart or not cart.get("items"):
        await callback.answer("Your cart is empty.", show_alert=True)
        return

    store_repo = StoreRepo(db)
    store = await store_repo.get_by_id(cart["store_id"])
    if not store:
        await callback.answer("Store not found.", show_alert=True)
        return

    # Calculate total
    subtotal = sum(i["price"] * i["qty"] for i in cart["items"])
    discount = 0.0
    coupon = None
    if cart.get("coupon_code"):
        coupon_repo = CouponRepo(db)
        coupon = await coupon_repo.get_by_code(cart["coupon_code"])
        if coupon:
            if coupon["type"] == "percentage":
                discount = subtotal * coupon["value"] / 100
            else:
                discount = min(coupon["value"], subtotal)
    total = subtotal - discount

    await state.update_data(
        cart_id=str(cart["_id"]),
        store_id=cart["store_id"],
        total=total,
        coupon_code=cart.get("coupon_code"),
    )

    methods = []
    if store.get("upi_id"):
        methods.append("upi")
    if store.get("oxapay_key"):
        methods.append("oxapay")
    if store.get("stars_enabled"):
        methods.append("stars")

    if not methods:
        await callback.answer("⚠️ No payment methods configured for this store.", show_alert=True)
        return

    text = (
        f"💳 <b>Checkout</b>\n\n"
        f"💰 Total: <b>₹{total:,.2f}</b>\n\n"
        f"Select a payment method:"
    )
    from keyboards.builders import payment_method_kb
    await callback.message.edit_text(
        text,
        reply_markup=payment_method_kb(methods, cart["store_id"]),
        parse_mode="HTML"
    )
    await state.set_state(CheckoutStates.selecting_method)
    await callback.answer()


@router.callback_query(F.data.startswith("pay:upi:"), CheckoutStates.selecting_method)
async def pay_upi(callback: CallbackQuery, db, db_user, state: FSMContext):
    """Show UPI payment instructions."""
    store_id = callback.data.split(":")[2]
    data = await state.get_data()
    total = data.get("total", 0)

    store_repo = StoreRepo(db)
    store = await store_repo.get_by_id(store_id)
    if not store:
        await callback.answer("Store not found.", show_alert=True)
        return

    upi_svc = UPIService(store)
    instructions = upi_svc.get_instructions(total)

    text = (
        f"📲 <b>UPI Payment</b>\n\n"
        f"{instructions}\n\n"
        f"💰 Amount: <b>₹{total:,.2f}</b>\n\n"
        f"After payment, send the screenshot/UTR below:"
    )

    from keyboards.builders import cancel_payment_kb
    if store.get("upi_qr_file_id"):
        await callback.message.answer_photo(
            photo=store["upi_qr_file_id"],
            caption=text,
            reply_markup=cancel_payment_kb(store_id),
            parse_mode="HTML"
        )
        await callback.message.delete()
    else:
        await callback.message.edit_text(
            text,
            reply_markup=cancel_payment_kb(store_id),
            parse_mode="HTML"
        )

    await state.update_data(payment_method="upi")
    await state.set_state(CheckoutStates.awaiting_upi_proof)
    await callback.answer()


@router.message(CheckoutStates.awaiting_upi_proof)
async def receive_upi_proof(message: Message, db, db_user, state: FSMContext):
    """Receive UPI payment proof from customer."""
    data = await state.get_data()
    store_id = data["store_id"]
    total = data["total"]

    # Accept photo or text (UTR number)
    proof_file_id = None
    proof_text = None

    if message.photo:
        proof_file_id = message.photo[-1].file_id
    elif message.document:
        proof_file_id = message.document.file_id
    elif message.text:
        proof_text = message.text.strip()
    else:
        await message.answer("Please send a screenshot or UTR number.")
        return

    # Create order
    cart_repo = CartRepo(db)
    cart = await cart_repo.get(str(db_user["_id"]))
    order_repo = OrderRepo(db)
    order = await order_repo.create(
        user_id=str(db_user["_id"]),
        store_id=store_id,
        items=cart["items"],
        total=total,
        coupon_code=data.get("coupon_code"),
        payment_method="upi",
    )

    # Create payment record
    payment_repo = PaymentRepo(db)
    payment = await payment_repo.create(
        order_id=str(order["_id"]),
        user_id=str(db_user["_id"]),
        store_id=store_id,
        amount=total,
        method="upi",
        proof_file_id=proof_file_id,
        proof_text=proof_text,
    )

    # Clear cart
    await cart_repo.clear(str(db_user["_id"]))

    # Notify store owner
    from services.notifications import notify_owner_new_order
    await notify_owner_new_order(
        message.bot, db, order, payment, db_user, proof_file_id, proof_text
    )

    await state.clear()
    await message.answer(
        f"✅ <b>Payment proof submitted!</b>\n\n"
        f"📋 Order ID: <code>{str(order['_id'])[-8:].upper()}</code>\n"
        f"💰 Amount: <b>₹{total:,.2f}</b>\n\n"
        f"⏳ Your order will be confirmed once payment is verified.\n"
        f"You'll receive a notification when it's confirmed.",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("pay:oxapay:"), CheckoutStates.selecting_method)
async def pay_oxapay(callback: CallbackQuery, db, db_user, state: FSMContext):
    """Create OxaPay invoice."""
    store_id = callback.data.split(":")[2]
    data = await state.get_data()
    total = data.get("total", 0)

    store_repo = StoreRepo(db)
    store = await store_repo.get_by_id(store_id)
    if not store or not store.get("oxapay_key"):
        await callback.answer("OxaPay not configured.", show_alert=True)
        return

    await callback.answer("⏳ Creating invoice...")

    # Create order first
    cart_repo = CartRepo(db)
    cart = await cart_repo.get(str(db_user["_id"]))
    order_repo = OrderRepo(db)
    order = await order_repo.create(
        user_id=str(db_user["_id"]),
        store_id=store_id,
        items=cart["items"],
        total=total,
        coupon_code=data.get("coupon_code"),
        payment_method="oxapay",
    )

    oxapay_svc = OxaPayService(store)
    result = await oxapay_svc.create_invoice(
        amount=total,
        order_id=str(order["_id"]),
        user_id=str(db_user["_id"]),
    )

    if not result or not result.get("payLink"):
        await callback.message.edit_text(
            "❌ Failed to create payment link. Please try another method.",
            parse_mode="HTML"
        )
        return

    # Create payment record
    payment_repo = PaymentRepo(db)
    await payment_repo.create(
        order_id=str(order["_id"]),
        user_id=str(db_user["_id"]),
        store_id=store_id,
        amount=total,
        method="oxapay",
        external_id=result.get("trackId"),
    )

    await cart_repo.clear(str(db_user["_id"]))

    from keyboards.builders import oxapay_payment_kb
    await callback.message.edit_text(
        f"🔗 <b>Crypto Payment</b>\n\n"
        f"💰 Amount: <b>₹{total:,.2f}</b>\n\n"
        f"Click the button below to pay securely via OxaPay.\n"
        f"Your order will be confirmed automatically after payment.",
        reply_markup=oxapay_payment_kb(result["payLink"], store_id),
        parse_mode="HTML"
    )
    await state.clear()


@router.callback_query(F.data.startswith("pay:stars:"), CheckoutStates.selecting_method)
async def pay_stars(callback: CallbackQuery, db, db_user, state: FSMContext):
    """Send Telegram Stars invoice."""
    store_id = callback.data.split(":")[2]
    data = await state.get_data()
    total = data.get("total", 0)

    store_repo = StoreRepo(db)
    store = await store_repo.get_by_id(store_id)

    cart_repo = CartRepo(db)
    cart = await cart_repo.get(str(db_user["_id"]))
    order_repo = OrderRepo(db)
    order = await order_repo.create(
        user_id=str(db_user["_id"]),
        store_id=store_id,
        items=cart["items"],
        total=total,
        coupon_code=data.get("coupon_code"),
        payment_method="stars",
    )

    stars_svc = StarsService()
    stars_count = stars_svc.inr_to_stars(total)

    await callback.message.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Order from {store['name']}",
        description=f"Payment for {len(cart['items'])} item(s)",
        payload=stars_svc.make_payload(str(order["_id"]), store_id),
        currency="XTR",
        prices=[{"label": "Total", "amount": stars_count}],
    )
    await cart_repo.clear(str(db_user["_id"]))
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("pay:cancel:"))
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    store_id = callback.data.split(":")[2]
    from keyboards.builders import back_to_store_kb
    await callback.message.edit_text(
        "❌ Payment cancelled.",
        reply_markup=back_to_store_kb(store_id),
        parse_mode="HTML"
    )
    await callback.answer()
