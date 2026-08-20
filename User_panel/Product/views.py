from django.shortcuts import render,get_object_or_404,redirect
from django.db.models import Prefetch
from Admin_panel.product.models import Product, Variant
from Admin_panel.category.models import Category
from django.db.models import Q, Min
from django.core.paginator import Paginator
from User_panel.Cart.models import WishlistItem

def category_list(request):
    categories = Category.objects.filter(
        is_active=True,
        is_deleted=False,
    ).order_by("category_name")

    paginator = Paginator(
        categories,
        6
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(
        page_number
    )

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
            is_active=True,
            is_deleted=False,
            category__is_active=True,
            category__is_deleted=False,
            variants__is_active=True,
            variants__is_deleted=False,
        )
        .select_related("category")
        .prefetch_related(
            "images",
            "variants",
            "variants__images",
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

    return render(request, "Product/shop.html", context)

def product_detail(request, product_id):

    product = get_object_or_404(
        Product.objects.prefetch_related(
            "variants__images",
        ),
        id=product_id,
        is_active=True,
        is_deleted=False,
        category__is_active=True,
        category__is_deleted=False,
    )

    variant = (
        product.variants.filter(
            is_active=True,
            is_deleted=False,
        )
        .prefetch_related("images")
        .first()
    )
    active_variants = (
        product.variants.filter(
            is_active=True,
            is_deleted=False,
        )
        .prefetch_related("images")
    )
    variant_data = []

    for item in active_variants:

        variant_data.append(
            {
                "id": item.id,
                "color": item.color,
                "size": item.size,
                "price": str(item.price),
                "stock": item.stock,
                "sku": item.sku,
                "images": [
                    image.image.url
                    for image in item.images.all()
                ],
            }
        )
    colors = []
    for item in active_variants:
        if item.color not in colors:
            colors.append(item.color)

    if variant is None:
        return redirect("product:product_list")

    similar_products = (
        Product.objects.filter(
            category=product.category,
            is_active=True,
            is_deleted=False,
            category__is_active=True,
            category__is_deleted=False,
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
    }

    return render(
        request,
        "Product/product_detail.html",
        context,
    )