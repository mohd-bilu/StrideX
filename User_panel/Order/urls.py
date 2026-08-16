from django.urls import path
from . import views

app_name = "order"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("place-order/", views.place_order, name="place_order"),
    path("success/<str:order_id>/", views.order_success, name="order_success"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<str:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<str:order_id>/invoice/", views.download_invoice, name="download_invoice"),
    path("orders/<str:order_id>/cancel/", views.cancel_order, name="cancel_order"),
    path("orders/<str:order_id>/cancel-item/<int:item_id>/", views.cancel_order_item, name="cancel_order_item"),
    path("orders/<str:order_id>/return/", views.request_return, name="request_return"),
]