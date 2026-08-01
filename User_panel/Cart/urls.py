from django.urls import path
from . import views

urlpatterns = [
    # Cart
    path("", views.cart, name="cart"),
    path("add/<int:variant_id>/", views.add_to_cart, name="add_to_cart"),
    path("update/<int:item_id>/", views.update_cart, name="update_cart"),
    path("remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),

    # Wishlist
    path("wishlist/", views.wishlist, name="wishlist"),
    path("wishlist/add/<int:variant_id>/", views.add_to_wishlist, name="add_to_wishlist"),
    path("wishlist/remove/<int:item_id>/", views.remove_from_wishlist, name="remove_from_wishlist"),
]