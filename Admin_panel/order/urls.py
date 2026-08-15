from django.urls import path
from . import views

app_name = "admin_order"

urlpatterns = [
    path("", views.order_list, name="order_list"),
    path("returns/", views.return_list, name="return_list"),
    path("<str:order_id>/", views.order_detail, name="order_detail"),
    path("<str:order_id>/update-status/", views.update_order_status, name="update_order_status"),
    path("returns/<int:item_id>/status/",views.update_return_status,name="update_return_status"),
]