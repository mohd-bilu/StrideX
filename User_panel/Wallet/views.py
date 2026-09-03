from decimal import Decimal, InvalidOperation

import razorpay

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from .models import Wallet, WalletTransaction

@login_required
def wallet(request):
    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    transactions = wallet.transactions.all()

    context = {
        "wallet": wallet,
        "transactions": transactions,
    }

    return render(
        request,
        "Wallet/wallet.html",
        context
    )


@login_required
def add_money(request):
    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":

        amount_value = request.POST.get(
            "amount",
            ""
        ).strip()

        if not amount_value:
            messages.error(
                request,
                "Please enter an amount."
            )

            return redirect(
                "wallet:add_money"
            )

        try:
            amount = Decimal(
                amount_value
            )
        except InvalidOperation:
            messages.error(
                request,
                "Please enter a valid amount."
            )

            return redirect(
                "wallet:add_money"
            )

        if amount < Decimal("1.00"):
            messages.error(
                request,
                "Minimum top-up amount is ₹1."
            )

            return redirect(
                "wallet:add_money"
            )

        amount = amount.quantize(
            Decimal("0.01")
        )

        if not settings.RAZORPAY_KEY_ID:
            messages.error(
                request,
                "Online payment is not configured yet."
            )

            return redirect(
                "wallet:add_money"
            )

        if not settings.RAZORPAY_KEY_SECRET:
            messages.error(
                request,
                "Online payment is not configured yet."
            )

            return redirect(
                "wallet:add_money"
            )

        try:

            client = razorpay.Client(
                auth=(
                    settings.RAZORPAY_KEY_ID,
                    settings.RAZORPAY_KEY_SECRET,
                )
            )

            amount_in_paise = int(
                amount * Decimal("100")
            )

            razorpay_order = client.order.create(
                data={
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "receipt": (
                        f"WALLET-{request.user.id}-"
                        f"{int(amount_in_paise)}"
                    ),
                }
            )

        except Exception as error:

            print(
                "RAZORPAY WALLET ORDER ERROR:",
                error
            )

            messages.error(
                request,
                "Unable to start payment. Please try again."
            )

            return redirect(
                "wallet:add_money"
            )

        context = {
            "wallet": wallet,
            "amount": amount,
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": razorpay_order["id"],
            "razorpay_amount": amount_in_paise,
        }

        return render(
            request,
            "Wallet/add_money_payment.html",
            context
        )

    context = {
        "wallet": wallet,
        "selected_amount": "",
    }

    return render(
        request,
        "Wallet/add_money.html",
        context
    )

@login_required
@transaction.atomic
def payment_success(request):
    if request.method != "POST":
        return redirect(
            "wallet:add_money"
        )

    razorpay_payment_id = request.POST.get(
        "razorpay_payment_id",
        ""
    ).strip()

    razorpay_order_id = request.POST.get(
        "razorpay_order_id",
        ""
    ).strip()

    razorpay_signature = request.POST.get(
        "razorpay_signature",
        ""
    ).strip()

    if not all([
        razorpay_payment_id,
        razorpay_order_id,
        razorpay_signature,
    ]):
        messages.error(
            request,
            "Payment verification data is missing."
        )

        return redirect(
            "wallet:add_money"
        )

    try:

        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET,
            )
        )

        client.utility.verify_payment_signature(
            {
                "razorpay_order_id":
                    razorpay_order_id,

                "razorpay_payment_id":
                    razorpay_payment_id,

                "razorpay_signature":
                    razorpay_signature,
            }
        )

    except Exception as error:

        print(
            "RAZORPAY SIGNATURE ERROR:",
            error
        )

        messages.error(
            request,
            "Payment verification failed."
        )

        return redirect(
            "wallet:add_money"
        )

    try:

        payment = client.payment.fetch(
            razorpay_payment_id
        )

        if payment.get("status") != "captured":
            messages.error(
                request,
                "Payment has not been captured."
            )

            return redirect(
                "wallet:add_money"
            )

        amount_paise = int(
            payment.get(
                "amount",
                0
            )
        )

        amount = (
            Decimal(amount_paise)
            / Decimal("100")
        )

    except Exception as error:

        print(
            "RAZORPAY PAYMENT FETCH ERROR:",
            error
        )

        messages.error(
            request,
            "Unable to verify payment status."
        )

        return redirect(
            "wallet:add_money"
        )

    wallet = (
        Wallet.objects
        .select_for_update()
        .get(
            user=request.user
        )
    )

    existing_transaction = (
        WalletTransaction.objects
        .filter(
            wallet=wallet,
            reference=razorpay_payment_id,
        )
        .first()
    )

    if existing_transaction:
        messages.success(
            request,
            "Wallet has already been credited."
        )

        return redirect(
            "wallet:wallet"
        )

    wallet.balance += amount

    wallet.save(
        update_fields=[
            "balance",
            "updated_at",
        ]
    )

    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="CREDIT",
        amount=amount,
        description="Wallet top-up",
        reference=razorpay_payment_id,
    )

    messages.success(
        request,
        f"₹{amount:.2f} added to your wallet successfully."
    )

    return redirect(
        "wallet:wallet"
    )