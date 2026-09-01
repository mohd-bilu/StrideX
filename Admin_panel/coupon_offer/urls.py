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
    path(
        "offers/",
        views.offer_list,
        name="offer_list",
    ),
    path(
        "offers/add/",
        views.offer_add,
        name="offer_add",
    ),
    path(
        "offers/edit/<int:offer_id>/",
        views.offer_edit,
        name="offer_edit",
    ),
    path(
        "offers/delete/<int:offer_id>/",
        views.offer_delete,
        name="offer_delete",
    ),
]