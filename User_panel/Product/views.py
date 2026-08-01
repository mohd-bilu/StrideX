from django.shortcuts import render,get_object_or_404,redirect
from django.db.models import Prefetch
from Admin_panel.product.models import Product, Variant
from Admin_panel.category.models import Category
from django.db.models import Q


def product_list(request):

    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "")
    max_price = request.GET.get("price", "")
    products = (
        Product.objects.filter(
            is_active=True,
            is_deleted=False,
            variants__is_active=True,
            variants__is_deleted=False,
        )
        .select_related("category")
        .prefetch_related(
            "images",
            "variants",
            "variants__images",
        )
        .distinct()
    )

    if search:
        products = products.filter(
            Q(product_name__icontains=search) |
            Q(category__category_name__icontains=search)
        )
    if category:
        products = products.filter(
            category_id=category
        )
    if max_price:
        products = products.filter(
            variants__price__lte=max_price
        )
    categories = Category.objects.filter(
        is_active=True,
        is_deleted=False,
    )
    context = {
        "products": products,
        "search": search,
        "categories": categories,
        "selected_category": category,
        "selected_price": max_price,
    }

    return render(request,"Product/shop.html",context)

def product_detail(request, product_id):

    product = get_object_or_404(
        Product.objects.prefetch_related(
            "variants__images",
        ),
        id=product_id,
        is_active=True,
        is_deleted=False,
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

    context = {
        "product": product,
        "variant": variant,
        "active_variants": active_variants,
        "variant_data": variant_data,
        "colors": colors,
        "similar_products": similar_products,
    }

    return render(
        request,
        "Product/product_detail.html",
        context,
    )