from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import (Cart,CartItem,Wishlist,WishlistItem,)
from Admin_panel.product.models import Variant
from django.http import JsonResponse

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
        product__is_active=True,
        product__is_deleted=False,
        product__category__is_active=True,
        product__category__is_deleted=False,
    )

    if variant.stock <= 0:

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":

            return JsonResponse({

                "success": False,
                "message": "Out of stock."

            })

        messages.error(request,"Out of stock.")

        return redirect("cart")

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant,
    )

    if not created:

        if item.quantity >= min(5, variant.stock):

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":

                return JsonResponse({

                    "success": False,
                    "message": "Maximum quantity reached."

                })

            messages.error(request,"Maximum quantity reached.")

            return redirect("cart")

        item.quantity += 1

        item.save()

    WishlistItem.objects.filter(

        wishlist__user=request.user,
        variant=variant,

    ).delete()

    cart_count = CartItem.objects.filter(

        cart__user=request.user

    ).count()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":

        wishlist_count = WishlistItem.objects.filter(
            wishlist__user=request.user
        ).count()

        cart_count = CartItem.objects.filter(
            cart__user=request.user
        ).count()

        warning = ""

        remaining_stock = variant.stock - item.quantity

        if remaining_stock > 0 and remaining_stock <= 2:

            warning = f"Only {remaining_stock} left in stock."

        return JsonResponse({

            "success": True,
            "message": "Added to cart.",
            "cart_count": cart_count,
            "wishlist_count": wishlist_count,
            "warning": warning,

        })

    messages.success(request,"Added to cart.")

    return redirect("cart")

@login_required
def update_cart(request, item_id):

    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user,
    )

    action = request.GET.get("action")

    if action == "increase":

        if cart_item.quantity < min(5, cart_item.variant.stock):

            cart_item.quantity += 1
            cart_item.save()

        else:

            return JsonResponse({

                "success": False,
                "message": "Maximum quantity reached."

            })

    elif action == "decrease":

        if cart_item.quantity > 1:

            cart_item.quantity -= 1
            cart_item.save()

    subtotal = sum(

        item.total_price

        for item in cart_item.cart.items.all()

    )

    return JsonResponse({

        "success": True,
        "quantity": cart_item.quantity,
        "item_total": float(cart_item.total_price),
        "subtotal": float(subtotal),
        "total": float(subtotal),

    })
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

    wishlist, created = Wishlist.objects.get_or_create(
        user=request.user
    )

    item = WishlistItem.objects.filter(
        wishlist=wishlist,
        variant=variant,
    ).first()

    if item:

        item.delete()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":

            wishlist_count = WishlistItem.objects.filter(
                wishlist__user=request.user
            ).count()

            return JsonResponse({

                "success": True,
                "added": False,
                "wishlist_count": wishlist_count,

            })

        messages.success(
            request,
            "Product removed from wishlist."
        )

    else:

        WishlistItem.objects.create(
            wishlist=wishlist,
            variant=variant,
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":

            wishlist_count = WishlistItem.objects.filter(
                wishlist__user=request.user
            ).count()

            return JsonResponse({

                "success": True,
                "added": True,
                "wishlist_count": wishlist_count,

            })

        messages.success(
            request,
            "Product added to wishlist."
        )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "wishlist",
        )
    )

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