from django.urls import path

from . import views


app_name = "coupon_offer"


urlpatterns = [
    path(
        "coupons/",
        views.coupon_list,
        name="coupon_list",
    ),
    path(
        "coupons/add/",
        views.coupon_add,
        name="coupon_add",
    ),
    path(
        "coupons/edit/<int:coupon_id>/",
        views.coupon_edit,
        name="coupon_edit",
    ),
    path(
        "coupons/delete/<int:coupon_id>/",
        views.coupon_delete,
        name="coupon_delete",
    ),
]