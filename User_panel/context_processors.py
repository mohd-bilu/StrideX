from User_panel.Cart.models import CartItem, WishlistItem


def navbar_counts(request):
    cart_count = 0
    wishlist_count = 0

    if request.user.is_authenticated:
        cart_count = CartItem.objects.filter(
            cart__user=request.user
        ).count()

        wishlist_count = WishlistItem.objects.filter(
            wishlist__user=request.user
        ).count()

    return {
        "cart_count": cart_count,
        "wishlist_count": wishlist_count,
    }