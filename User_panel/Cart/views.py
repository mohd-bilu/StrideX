from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import (Cart,CartItem,Wishlist,WishlistItem,)
from Admin_panel.product.models import Variant

@login_required
def cart(request):

    cart = Cart.objects.filter(
        user=request.user
    ).prefetch_related(
        "items__variant__images",
        "items__variant__product",
    ).first()

    subtotal = 0
    if cart:
        for item in cart.items.all():
            subtotal += item.variant.price * item.quantity
    context = {
        "cart": cart,
        "subtotal": subtotal,
        "shipping": 0,
        "discount": 0,
        "total": subtotal,
    }

    return render(
        request,
        "Cart/cart.html",
        context,
    )


@login_required
def add_to_cart(request, variant_id):

    variant = get_object_or_404(
        Variant,
        id=variant_id,
        is_active=True,
        is_deleted=False,
    )

    product = variant.product

    if not product.is_active or product.is_deleted:
        messages.error(request, "This product is unavailable.")
        return redirect("product_detail", slug=product.slug)

    if variant.stock <= 0:
        messages.error(request, "Product is out of stock.")
        return redirect("product_detail", slug=product.slug)

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant,
    )

    if not created:

        if cart_item.quantity < variant.stock:

            cart_item.quantity += 1
            cart_item.save()

        else:

            messages.error(
                request,
                "Maximum available stock reached."
            )

            return redirect(
                "product_detail",
                slug=product.slug,
            )

    messages.success(
        request,
        "Product added to cart."
    )
    WishlistItem.objects.filter(
        wishlist__user=request.user,
        variant=variant,
    ).delete()

    return redirect("cart",)

def remove_from_cart(request, item_id):
    pass

@login_required
def update_cart(request, item_id):

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user,
    )

    action = request.GET.get("action")

    if action == "increase":

        if cart_item.quantity >= 5:

            messages.warning(
                request,
                "Maximum quantity allowed is 5.",
            )

        elif cart_item.quantity >= cart_item.variant.stock:

            messages.error(
                request,
                "Maximum stock reached.",
            )

        else:

            cart_item.quantity += 1
            cart_item.save()

    elif action == "decrease":

        if cart_item.quantity > 1:

            cart_item.quantity -= 1
            cart_item.save()

        else:

            messages.warning(
                request,
                "Minimum quantity is 1.",
            )

    return redirect("cart")
@login_required
def remove_from_cart(request, item_id):

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user,
    )

    cart_item.delete()

    messages.success(
        request,
        "Product removed from cart.",
    )

    return redirect("cart")

@login_required
def wishlist(request):

    search = request.GET.get("search", "").strip()

    wishlist = (
        Wishlist.objects.filter(user=request.user)
        .prefetch_related(
            "items__variant__product",
            "items__variant__images",
        )
        .first()
    )

    items = wishlist.items.all() if wishlist else []

    if search:
        items = items.filter(
            Q(variant__product__product_name__icontains=search)
        )

    return render(
        request,
        "Cart/wishlist.html",
        {
            "wishlist": wishlist,
            "items": items,
            "search": search,
        },
    )

@login_required
def add_to_wishlist(request, variant_id):
    variant = get_object_or_404(
        Variant,
        id=variant_id,
        is_active=True,
        is_deleted=False,
    )

    wishlist, created = Wishlist.objects.get_or_create(user=request.user)

    item, created = WishlistItem.objects.get_or_create(
        wishlist=wishlist,
        variant=variant,
    )

    if created:

        messages.success(request,"Product added to wishlist.",)
    else:

        messages.info(
            request,
            "Product is already in your wishlist.",
        )

    return redirect(request.META.get("HTTP_REFERER", "wishlist"))


@login_required
def remove_from_wishlist(request, item_id):
    item = get_object_or_404(
        WishlistItem,
        id=item_id,
        wishlist__user=request.user,
    )

    item.delete()

    messages.success(request, "Product removed from wishlist.")

    return redirect("wishlist")