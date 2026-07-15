from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import (get_object_or_404, redirect, render)
from .forms import ProductForm
from .models import (Product, ProductImage)


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

        images = request.FILES.getlist("images")

        if len(images) < 3:
            messages.error(request,"Please upload at least 3 images.",)

        elif form.is_valid():
            product = form.save()

            for index, image in enumerate(images):
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    is_primary=(index == 0),
                )

            messages.success(request,"Product added successfully.",)
            return redirect("product_list")

    else:
        form = ProductForm()

    context = {"form": form,}

    return render(request,"product/add_product.html",context,)

def edit_product(request, product_id):
    product = get_object_or_404(Product,id=product_id,is_deleted=False,)

    if request.method == "POST":
        form = ProductForm(request.POST,instance=product,)

        images = request.FILES.getlist("images")

        if form.is_valid():
            product = form.save()

            for image in images:
                ProductImage.objects.create(
                    product=product,
                    image=image,
                )

            messages.success(request,"Product updated successfully.",)
            return redirect("product_list")

    else:
        form = ProductForm(instance=product,)

    context = {
        "form": form,
        "product": product,
        "images": product.images.all(),
    }

    return render(request,"product/edit_product.html",context,)

def delete_product(request, product_id):
    product = get_object_or_404(Product,id=product_id,is_deleted=False,)

    if request.method == "POST":
        product.is_deleted = True
        product.save()

        messages.success(request,"Product deleted successfully.",)

    return redirect("product_list")