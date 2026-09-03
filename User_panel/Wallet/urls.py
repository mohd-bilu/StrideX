from django.urls import path

from . import views


app_name = "wallet"


urlpatterns = [
    path(
        "",
        views.wallet,
        name="wallet",
    ),
    path(
        "add-money/",
        views.add_money,
        name="add_money",
    ),
    path(
        "payment-success/",
        views.payment_success,
        name="payment_success",
    ),
]