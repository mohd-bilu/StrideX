from django.urls import path
from . import views

app_name = "checkout"

urlpatterns = [
    path("", views.checkout, name="checkout"),
    path("coupons/", views.available_coupons, name="available_coupons"),
    path("coupon/apply/", views.apply_coupon, name="apply_coupon"),
    path("coupon/remove/", views.remove_coupon, name="remove_coupon"),
    path("create-razorpay-order/", views.create_razorpay_order, name="create_razorpay_order"),
    path("razorpay-payment-success/", views.razorpay_payment_success, name="razorpay_payment_success"),
    path("razorpay-payment-cancelled/", views.razorpay_payment_cancelled, name="razorpay_payment_cancelled"),
    path("razorpay-payment-failed/", views.razorpay_payment_failed, name="razorpay_payment_failed"),
]