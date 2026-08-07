from datetime import timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Min, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from Admin_panel.category.models import Category
from .forms import (ProductForm,VariantForm,)
from .models import (Product,Variant,VariantImage,)

def product_list(request):
    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "")
    max_price = request.GET.get("price", "")
    sort = request.GET.get("sort", "")
    page = request.GET.get("page")

    products = Product.objects.filter(is_deleted=False).select_related("category").prefetch_related("variants", "variants__images").annotate(
        variant_count=Count("variants", filter=Q(variants__is_deleted=False)),
        min_price=Min("variants__price", filter=Q(variants__is_active=True, variants__is_deleted=False)),
    ).distinct()

    if search:
        products = products.filter(Q(product_name__icontains=search) | Q(category__category_name__icontains=search))

    if category:
        products = products.filter(category_id=category)

    if max_price:
        products = products.filter(min_price__lte=max_price)

    if sort == "low":
        products = products.order_by("min_price")
    elif sort == "high":
        products = products.order_by("-min_price")
    elif sort == "az":
        products = products.order_by("product_name")
    elif sort == "za":
        products = products.order_by("-product_name")
    elif sort == "oldest":
        products = products.order_by("created_at")
    else:
        products = products.order_by("-created_at")

    paginator = Paginator(products, 5)
    page_obj = paginator.get_page(page)

    categories = Category.objects.filter(is_active=True, is_deleted=False)
    total_products = Product.objects.filter(is_deleted=False).count()
    low_stock_products = Variant.objects.filter(is_active=True, is_deleted=False, stock__gt=0, stock__lte=5).count()
    out_of_stock_products = Variant.objects.filter(is_active=True, is_deleted=False, stock=0).count()
    new_arrivals = Product.objects.filter(is_active=True, is_deleted=False, created_at__gte=timezone.now() - timedelta(days=30)).count()

    context = {
        "page_obj": page_obj,
        "products": page_obj,
        "categories": categories,
        "search_query": search,
        "selected_category": category,
        "selected_price": max_price,
        "selected_sort": sort,
        "total_products": total_products,
        "low_stock_products": low_stock_products,
        "out_of_stock_products": out_of_stock_products,
        "new_arrivals": new_arrivals,
    }

    return render(request, "Product/product_list.html", context)
def add_product(request):

    if request.method == "POST":

        form = ProductForm(request.POST)

        if form.is_valid():

            product = form.save()

            messages.success(
                request,
                "Product created successfully. Now add variants."
            )

            return redirect(
                "add_variant",
                product_id=product.id
            )

    else:

        form = ProductForm()

    context = {
        "form": form,
    }

    return render(
        request,
        "product/add_product.html",
        context,
    )

def edit_product(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id,
        is_deleted=False,
    )

    if (
        request.method == "POST"
        and request.POST.get("toggle_status")
    ):

        product.is_active = (
            request.POST.get("new_status") == "True"
        )

        product.save(
            update_fields=["is_active"]
        )

        messages.success(
            request,
            "Product status updated successfully.",
        )

        return redirect(
            "product_list",
        )

    if request.method == "POST":

        form = ProductForm(
            request.POST,
            instance=product,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Product updated successfully.",
            )

            return redirect(
                "product_list",
            )

    else:

        form = ProductForm(
            instance=product,
        )

    context = {
        "form": form,
        "product": product,
    }

    return render(
        request,
        "product/edit_product.html",
        context,
    )
def delete_product(request, product_id):
    product = get_object_or_404(Product,id=product_id,is_deleted=False,)

    if request.method == "POST":
        product.is_deleted = True
        product.save()

        messages.success(request,"Product deleted successfully.",)

    return redirect("product_list")

def variant_list(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_deleted=False,
    )

    search_query = request.GET.get(
        "search",
        "",
    ).strip()

    variants = product.variants.filter(is_deleted=False,).order_by("-id",)
    if search_query:
        variants = variants.filter(
            Q(
                sku__icontains=search_query,
            )
            | Q(
                color__icontains=search_query,
            )
            | Q(
                size__icontains=search_query,
            )
        )

    paginator = Paginator(
        variants,
        10,
    )

    page_number = request.GET.get(
        "page",
    )

    page_obj = paginator.get_page(
        page_number,
    )

    context = {
        "product": product,
        "page_obj": page_obj,
        "search_query": search_query,
    }

    return render(
        request,
        "product/variant_list.html",
        context,
    )

def add_variant(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_deleted=False,
    )

    if request.method == "POST":
        form = VariantForm(
            request.POST,
        )

        images = request.FILES.getlist(
            "images",
        )

        if len(images) < 3:
            messages.error(
                request,
                "Please upload at least 3 images.",
            )

        elif form.is_valid():
            variant = form.save(
                commit=False,
            )

            variant.product = product
            variant.save()

            for index, image in enumerate(images):
                VariantImage.objects.create(
                    variant=variant,
                    image=image,
                    is_primary=(
                        index == 0
                    ),
                )


            messages.success(request,"Variant added successfully.")

            return redirect("variant_list",product.id,)

    else:
        form = VariantForm()

    context = {
        "form": form,
        "product": product,
    }

    return render(
        request,
        "product/add_variant.html",
        context,
    )
def edit_variant(request, variant_id):

    variant = get_object_or_404(
        Variant,
        id=variant_id,
    )

    if request.method == "POST":

        form = VariantForm(
            request.POST,
            instance=variant,
        )

        images = request.FILES.getlist("images")
        print("FILES:", request.FILES)
        print("IMAGES:", images)
        print("COUNT:", len(images))    

        if form.is_valid():
            print("FORM VALID:", form.is_valid())
            print(form.errors)
            variant = form.save(commit=False)

            variant.is_active = (
                request.POST.get("is_active") == "True"
            )

            variant.save()
            print("Variant Saved")
            if images:

                total_images = (
                    variant.images.count() + len(images)
                )
                print("Current Images:",variant.images.count())
                print("New Images:",len(images))
                print("Total Images:",variant.images.count()+len(images))
                if total_images > 6:

                    messages.error(
                        request,
                        "Maximum 6 images are allowed.",
                    )

                    return redirect(
                        "edit_variant",
                        variant.id,
                    )

                has_primary = variant.images.filter(
                    is_primary=True
                ).exists()
                print("Starting Image Loop")
                for index, image in enumerate(images):
                    print("Saving:",image.name)
                    VariantImage.objects.create(
                        variant=variant,
                        image=image,
                        is_primary=(
                            not has_primary and index == 0
                        ),
                    )
                print("Image Loop Finished")
            messages.success(
                request,
                "Variant updated successfully.",
            )
            print("RETURNING TO VARIANT LIST")
            return redirect(
                "variant_list",
                variant.product.id,
            )

    else:

        form = VariantForm(
            instance=variant,
        )

    context = {
        "form": form,
        "variant": variant,
        "product": variant.product,
        "images": variant.images.order_by(
            "-is_primary",
            "id",
        ),
    }

    return render(
        request,
        "product/edit_variant.html",
        context,
    )
def delete_variant(request, variant_id):
    variant = get_object_or_404(
        Variant,
        id=variant_id,
        is_deleted=False,
    )

    if request.method == "POST":
        variant.is_deleted = True
        variant.save()

        messages.success(
            request,
            "Variant deleted successfully.",
        )

    return redirect(
        "variant_list",
        variant.product.id,
    )

def delete_variant_image(request,image_id):

    if request.method!="POST":
        return JsonResponse({
            "success":False
        },status=400)

    image=get_object_or_404(
        VariantImage,
        id=image_id
    )

    variant=image.variant

    if variant.images.count()<=3:

        return JsonResponse({
            "success":False,
            "message":"Minimum 3 images required."
        })

    image.delete()

    return JsonResponse({
        "success":True,
        "count":variant.images.count()
    })


def make_primary_image(request,image_id):

    if request.method!="POST":
        return JsonResponse({"success":False},status=400)

    image=get_object_or_404(
        VariantImage,
        id=image_id,
    )

    variant=image.variant

    VariantImage.objects.filter(
        variant=variant,
    ).update(
        is_primary=False,
    )

    image.is_primary=True
    image.save(update_fields=["is_primary"])

    return JsonResponse({
        "success":True,
    })