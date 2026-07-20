from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import (get_object_or_404, redirect, render)
from .forms import (ProductForm, VariantForm,)

from .models import ( Product,ProductImage,Variant,VariantImage,)

def product_list(request):
    search_query = request.GET.get("search", "").strip()

    products = Product.objects.filter(is_deleted=False,).select_related("category")

    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(category__category_name__icontains=search_query)
        )

    total_products = products.count()

    active_products = products.filter(is_active=True,).count()

    inactive_products = products.filter(is_active=False,).count()

    paginator = Paginator(products, 10)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "total_products": total_products,
        "active_products": active_products,
        "inactive_products": inactive_products,
    }

    return render( request,"product/product_list.html",context,)

def add_product(request):

    if request.method == "POST":

        form = ProductForm(request.POST)

        if form.is_valid():

            product = form.save()

            messages.success(
                request,
                "Product created successfully. Now add the first variant."
            )

            return redirect(
                "add_variant",
                product.id,
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

            variant = form.save(commit=False)

            variant.is_active = (
                request.POST.get("is_active") == "True"
            )

            variant.save()

            if images:

                total_images = (
                    variant.images.count() + len(images)
                )

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

                for index, image in enumerate(images):

                    VariantImage.objects.create(
                        variant=variant,
                        image=image,
                        is_primary=(
                            not has_primary and index == 0
                        ),
                    )

            messages.success(
                request,
                "Variant updated successfully.",
            )

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
def delete_variant_image(request, image_id):

    image = get_object_or_404(
        VariantImage,
        id=image_id,
    )

    variant = image.variant

    if request.method == "POST":

        if variant.images.count() <= 3:

            messages.error(
                request,
                "A variant must have at least 3 images.",
            )

            return redirect(
                "edit_variant",
                variant.id,
            )

        image.delete()

        messages.success(
            request,
            "Image deleted successfully.",
        )

    return redirect(
        "edit_variant",
        variant.id,
    )

def make_primary_image(request, image_id):
    image = get_object_or_404(
        VariantImage,
        id=image_id,
    )

    variant = image.variant

    if request.method == "POST":
        VariantImage.objects.filter(
            variant=variant,
        ).update(
            is_primary=False,
        )

        image.is_primary = True
        image.save()

        messages.success(
            request,
            "Primary image updated.",
        )

    return redirect(
        "edit_variant",
        variant.id,
    )