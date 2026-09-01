from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Wallet


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