from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Min, Prefetch, Q
from django.shortcuts import  redirect, render
from django.utils import timezone

from Admin_panel.category.models import Category
from Admin_panel.coupon_offer.models import Offer
from Admin_panel.product.models import Product, Variant
from User_panel.Cart.models import WishlistItem


def get_best_offer(variant, now=None):
    if now is None:
        now = timezone.now()

    offers = Offer.objects.filter(
        is_active=True,
        start_date__lte=now,
        expiry_date__gt=now,
    ).filter(
        Q(
            offer_type="PRODUCT",
            product_id=variant.product_id,
        )
        | Q(
            offer_type="CATEGORY",
            category_id=variant.product.category_id,
        )
    )

    best_offer = None
    best_discount = Decimal("0.00")

    for offer in offers:
        if offer.discount_type == "PERCENTAGE":
            discount = (
                variant.price * offer.discount_value
            ) / Decimal("100")
        else:
            discount = min(
                offer.discount_value,
                variant.price,
            )

        discount = max(
            Decimal("0.00"),
            min(discount, variant.price),
        )

        if discount > best_discount:
            best_offer = offer
            best_discount = discount

    return best_offer, best_discount


def category_list(request):
    categories = Category.objects.filter(
        is_deleted=False,
    ).order_by("category_name")

    paginator = Paginator(categories, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "Product/category_list.html",
        {
            "categories": page_obj,
            "page_obj": page_obj,
        },
    )


def product_list(request):
    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "")
    max_price = request.GET.get("price", "")
    sort = request.GET.get("sort", "")
    page = request.GET.get("page")
    selected_size = request.GET.get("size", "")

    products = (
        Product.objects.filter(
            is_deleted=False,
            category__is_active=True,
            category__is_deleted=False,
            variants__is_deleted=False,
        )
        .select_related("category")
        .prefetch_related(
            "images",
            Prefetch(
                "variants",
                queryset=Variant.objects.filter(
                    is_deleted=False,
                ).prefetch_related("images"),
            ),
        )
        .annotate(min_price=Min("variants__price"))
        .distinct()
    )

    if search:
        products = products.filter(
            Q(product_name__icontains=search)
            | Q(category__category_name__icontains=search)
        )

    if category:
        products = products.filter(category_id=category)

    if max_price:
        products = products.filter(min_price__lte=max_price)

    if selected_size:
        products = products.filter(variants__size=selected_size)

    if sort == "low":
        products = products.order_by("min_price")
    elif sort == "high":
        products = products.order_by("-min_price")
    elif sort == "az":
        products = products.order_by("product_name")
    elif sort == "za":
        products = products.order_by("-product_name")
    else:
        products = products.order_by("-created_at")

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(page)

    categories = Category.objects.filter(
        is_active=True,
        is_deleted=False,
    )

    sizes = (
        Variant.objects.filter(
            is_active=True,
            is_deleted=False,
            product__is_active=True,
            product__is_deleted=False,
        )
        .values_list("size", flat=True)
        .distinct()
        .order_by("size")
    )

    wishlist_variant_ids = []

    if request.user.is_authenticated:
        wishlist_variant_ids = list(
            WishlistItem.objects.filter(
                wishlist__user=request.user
            ).values_list(
                "variant_id",
                flat=True,
            )
        )

    context = {
        "products": page_obj,
        "page_obj": page_obj,
        "categories": categories,
        "search": search,
        "selected_category": category,
        "selected_price": max_price,
        "selected_sort": sort,
        "wishlist_variant_ids": wishlist_variant_ids,
        "sizes": sizes,
        "selected_size": selected_size,
    }

    return render(
        request,
        "Product/shop.html",
        context,
    )
def product_detail(request, product_id):
    product = (
        Product.objects
        .select_related("category")
        .prefetch_related("variants__images")
        .filter(
            id=product_id,
            is_active=True,
            is_deleted=False,
            category__is_active=True,
            category__is_deleted=False,
        )
        .first()
    )

    if product is None:
        return render(
            request,
            "Product/product_unavailable.html",
            status=404,
        )

    active_variants = list(
        product.variants.filter(
            is_active=True,
            is_deleted=False,
        )
        .prefetch_related("images")
        .order_by("color", "size")
    )

    variant = active_variants[0] if active_variants else None

    if variant is None:
        return redirect("product:product_list")

    now = timezone.now()
    variant_data = []

    for item in active_variants:
        offer, discount = get_best_offer(item, now)

        offer_price = max(
            Decimal("0.00"),
            item.price - discount,
        )

        variant_data.append(
            {
                "id": item.id,
                "color": item.color,
                "size": item.size,
                "price": str(item.price),
                "stock": item.stock,
                "offer_name": offer.name if offer else "",
                "discount_type": offer.discount_type if offer else "",
                "discount_value": (
                    str(offer.discount_value)
                    if offer
                    else "0.00"
                ),
                "discount": str(discount),
                "offer_price": str(offer_price),
                "has_offer": bool(
                    offer and discount > 0
                ),
                "images": [
                    image.image.url
                    for image in item.images.all()
                ],
            }
        )

    selected_offer, selected_discount = get_best_offer(
        variant,
        now,
    )

    selected_offer_price = max(
        Decimal("0.00"),
        variant.price - selected_discount,
    )

    colors = []

    for item in active_variants:
        color = item.color.strip()

        if color and color not in colors:
            colors.append(color)

    similar_products = (
        Product.objects.filter(
            category=product.category,
            is_active=True,
            is_deleted=False,
            category__is_active=True,
            category__is_deleted=False,
            variants__is_active=True,
            variants__is_deleted=False,
        )
        .exclude(id=product.id)
        .prefetch_related(
            Prefetch(
                "variants",
                queryset=Variant.objects.filter(
                    is_active=True,
                    is_deleted=False,
                ).prefetch_related("images"),
            )
        )
        .distinct()
    )

    wishlist_variant_ids = []

    if request.user.is_authenticated:
        wishlist_variant_ids = list(
            WishlistItem.objects.filter(
                wishlist__user=request.user
            ).values_list(
                "variant_id",
                flat=True,
            )
        )

    context = {
        "product": product,
        "variant": variant,
        "active_variants": active_variants,
        "variant_data": variant_data,
        "colors": colors,
        "similar_products": similar_products,
        "wishlist_variant_ids": wishlist_variant_ids,
        "selected_offer": selected_offer,
        "selected_discount": selected_discount,
        "selected_offer_price": selected_offer_price,
    }

    return render(
        request,
        "Product/product_detail.html",
        context,
    )