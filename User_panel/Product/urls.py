from django.urls import path
from . import views

app_name = "product"

urlpatterns = [
    path("categories/", views.category_list, name="category_list"),
    path("", views.product_list, name="product_list"),
    path("<int:product_id>/", views.product_detail, name="product_detail"),
]