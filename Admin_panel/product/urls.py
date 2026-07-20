from django.urls import path
from . import views


urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("add/", views.add_product, name="add_product"),
    path("edit/<int:product_id>/", views.edit_product, name="edit_product"),
    path("delete/<int:product_id>/", views.delete_product, name="delete_product"),
    path("<int:product_id>/variants/", views.variant_list, name="variant_list"),
    path("<int:product_id>/variants/add/", views.add_variant, name="add_variant"),
    path("variant/<int:variant_id>/edit/", views.edit_variant, name="edit_variant"),
    path("variant/<int:variant_id>/delete/", views.delete_variant, name="delete_variant"),
    path("variant/image/<int:image_id>/delete/", views.delete_variant_image, name="delete_variant_image"),
    path("variant/image/<int:image_id>/primary/",views.make_primary_image,name="make_primary_image",),
]