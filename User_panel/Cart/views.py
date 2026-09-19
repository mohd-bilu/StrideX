from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from Admin_panel.coupon_offer.models import Offer
from Admin_panel.product.models import Variant
from .models import Cart, CartItem, Wishlist, WishlistItem


def get_best_offer(variant, now=None):
    now = now or timezone.now()

    offers = Offer.objects.filter(
        is_active=True,
        start_date__lte=now,
        expiry_date__gt=now,
    ).filter(
        Q(
            offer_type="PRODUCT",
            product=variant.product,
        )
        | Q(
            offer_type="CATEGORY",
            category=variant.product.category,
        )
    )

    best_offer = None
    best_discount = Decimal("0.00")

    for offer in offers:
        if offer.discount_type == "PERCENTAGE":
            discount = (
                variant.price
                * offer.discount_value
                / Decimal("100")
            )
        elif offer.discount_type == "FIXED":
            discount = offer.discount_value
        else:
            continue

        discount = min(
            discount,
            variant.price,
        )

        if discount > best_discount:
            best_discount = discount
            best_offer = offer

    return best_offer, best_discount


def get_cart_totals(cart):
    original_subtotal = Decimal("0.00")
    subtotal = Decimal("0.00")
    offer_discount = Decimal("0.00")

    now = timezone.now()

    for item in cart.items.select_related(
        "variant__product__category"
    ):
        original_price = item.variant.price

        offer, discount = get_best_offer(
            item.variant,
            now,
        )

        item.offer = offer
        item.offer_discount = discount
        item.offer_price = original_price - discount
        item.item_subtotal = (
            item.offer_price * item.quantity
        )

        original_subtotal += (
            original_price * item.quantity
        )

        subtotal += item.item_subtotal

        offer_discount += (
            discount * item.quantity
        )

    return (
        original_subtotal,
        subtotal,
        offer_discount,
    )

@login_required(login_url="login")
def cart(request):
    cart = (
        Cart.objects.filter(
            user=request.user
        )
        .prefetch_related(
            "items__variant__images",
            "items__variant__product__category",
        )
        .first()
    )

    original_subtotal = Decimal("0.00")
    subtotal = Decimal("0.00")
    offer_discount = Decimal("0.00")

    if cart:
        (
            original_subtotal,
            subtotal,
            offer_discount,
        ) = get_cart_totals(cart)

    context = {
        "cart": cart,
        "original_subtotal": original_subtotal,
        "subtotal": subtotal,
        "offer_discount": offer_discount,
        "discount": offer_discount,
        "shipping": Decimal("0.00"),
        "total": subtotal,
    }

    return render(
        request,
        "Cart/cart.html",
        context,
    )


def add_to_cart(request, variant_id):
    if not request.user.is_authenticated:
        return JsonResponse({
            "success": False,
            "login_required": True,
            "message": "Please login first.",
        }, status=401)
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
        if request.headers.get(
            "X-Requested-With"
        ) == "XMLHttpRequest":
            return JsonResponse({
                "success": False,
                "message": "Out of stock.",
            })

        messages.error(
            request,
            "Out of stock.",
        )

        return redirect("cart")

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant,
    )

    if not created:
        if item.quantity >= min(
            5,
            variant.stock,
        ):
            if request.headers.get(
                "X-Requested-With"
            ) == "XMLHttpRequest":
                return JsonResponse({
                    "success": False,
                    "message": "Maximum quantity reached.",
                })

            messages.error(
                request,
                "Maximum quantity reached.",
            )

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

    if request.headers.get(
        "X-Requested-With"
    ) == "XMLHttpRequest":
        wishlist_count = WishlistItem.objects.filter(
            wishlist__user=request.user
        ).count()

        remaining_stock = (
            variant.stock - item.quantity
        )

        warning = ""

        if (
            remaining_stock > 0
            and remaining_stock <= 2
        ):
            warning = (
                f"Only {remaining_stock} "
                "left in stock."
            )

        return JsonResponse({
            "success": True,
            "message": "Added to cart.",
            "cart_count": cart_count,
            "wishlist_count": wishlist_count,
            "warning": warning,
        })

    messages.success(
        request,
        "Added to cart.",
    )

    return redirect("cart")


@login_required(login_url="login")
def update_cart(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user,
        variant__is_active=True,
        variant__is_deleted=False,
        variant__product__is_active=True,
        variant__product__is_deleted=False,
        variant__product__category__is_active=True,
        variant__product__category__is_deleted=False,
    )

    action = request.GET.get("action")

    if action == "increase":
        if cart_item.quantity < min(
            5,
            cart_item.variant.stock,
        ):
            cart_item.quantity += 1
            cart_item.save()
        else:
            return JsonResponse({
                "success": False,
                "message": "Maximum quantity reached.",
            })

    elif action == "decrease":
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()

    else:
        return JsonResponse({
            "success": False,
            "message": "Invalid cart action.",
        })

    (
        original_subtotal,
        subtotal,
        offer_discount,
    ) = get_cart_totals(
        cart_item.cart
    )

    _, item_discount = get_best_offer(
        cart_item.variant
    )

    item_price = (
        cart_item.variant.price
        - item_discount
    )

    item_total = (
        item_price
        * cart_item.quantity
    )

    return JsonResponse({
        "success": True,
        "quantity": cart_item.quantity,
        "item_total": float(item_total),
        "original_item_total": float(
            cart_item.variant.price
            * cart_item.quantity
        ),
        "item_discount": float(
            item_discount
            * cart_item.quantity
        ),
        "original_subtotal": float(
            original_subtotal
        ),
        "subtotal": float(subtotal),
        "discount": float(
            offer_discount
        ),
        "total": float(subtotal),
    })
@login_required(login_url="login")
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
    search = request.GET.get(
        "search",
        "",
    ).strip()

    wishlist = (
        Wishlist.objects.filter(
            user=request.user
        )
        .prefetch_related(
            "items__variant__product",
            "items__variant__images",
        )
        .first()
    )

    items = (
        wishlist.items.all()
        if wishlist
        else []
    )

    if search:
        items = items.filter(
            Q(
                variant__product__product_name__icontains=search
            )
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


def add_to_wishlist(request, variant_id):
    if not request.user.is_authenticated:
        return JsonResponse({
            "success": False,
            "login_required": True,
            "message": "Please login first.",
        }, status=401)
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

    wishlist, created = (
        Wishlist.objects.get_or_create(
            user=request.user
        )
    )

    item = WishlistItem.objects.filter(
        wishlist=wishlist,
        variant=variant,
    ).first()

    if item:
        item.delete()

        if request.headers.get(
            "X-Requested-With"
        ) == "XMLHttpRequest":
            wishlist_count = (
                WishlistItem.objects.filter(
                    wishlist__user=request.user
                ).count()
            )

            return JsonResponse({
                "success": True,
                "added": False,
                "wishlist_count": wishlist_count,
            })

        messages.success(
            request,
            "Product removed from wishlist.",
        )

    else:
        WishlistItem.objects.create(
            wishlist=wishlist,
            variant=variant,
        )

        if request.headers.get(
            "X-Requested-With"
        ) == "XMLHttpRequest":
            wishlist_count = (
                WishlistItem.objects.filter(
                    wishlist__user=request.user
                ).count()
            )

            return JsonResponse({
                "success": True,
                "added": True,
                "wishlist_count": wishlist_count,
            })

        messages.success(
            request,
            "Product added to wishlist.",
        )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "wishlist",
        )
    )

@login_required(login_url="login")
def remove_from_wishlist(request, item_id):
    item = get_object_or_404(
        WishlistItem,
        id=item_id,
        wishlist__user=request.user,
    )

    item.delete()

    messages.success(
        request,
        "Product removed from wishlist.",
    )

    return redirect("wishlist")