from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from urllib3 import request

from .forms import CategoryForm
from .models import Category


def add_category(request):
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Category added successfully.",
            )

            return redirect("category_list")

    else:
        form = CategoryForm()

    return render(
        request,
        "category/add_category.html",
        {
            "form": form,
        },
    )

@never_cache
@login_required(login_url="admin_login")
def category_list(request):
    search_query = request.GET.get("search", "").strip()

    categories = Category.objects.filter(
        is_deleted=False,
    ).annotate(
        product_count=Count(
            "products",
            filter=Q(
                products__is_deleted=False,
            ),
        )
    ).order_by("-created_at")

    if search_query:
        categories = categories.filter(
            Q(category_name__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    total_categories = categories.count()

    active_categories = categories.filter(
        is_active=True,
    ).count()

    inactive_categories = categories.filter(
        is_active=False,
    ).count()

    paginator = Paginator(categories, 5)

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "category/category_list.html",
        {
            "page_obj": page_obj,
            "search_query": search_query,
            "total_categories": total_categories,
            "active_categories": active_categories,
            "inactive_categories": inactive_categories,
        },
    )


def edit_category(request, category_id):
    category = get_object_or_404(
        Category,
        id=category_id,
        is_deleted=False,
    )

    if request.method == "POST":

        form = CategoryForm(
            request.POST,
            request.FILES,
            instance=category,
        )

        if form.is_valid():

            category = form.save(commit=False)

            if request.POST.get("remove_image"):

                if category.image:
                    category.image.delete(save=False)

                category.image = None

            category.save()

            messages.success(
                request,
                "Category updated successfully.",
            )

            return redirect(
                "category_list",
            )

    else:

        form = CategoryForm(
            instance=category,
        )

    return render(
        request,
        "category/edit_category.html",
        {
            "form": form,
            "category": category,
        },
    )

def delete_category(request, category_id):
    category = get_object_or_404(
        Category,
        id=category_id,
        is_deleted=False,
    )

    category.is_deleted = True

    category.slug = (
        f"deleted-{category.id}-{category.slug}"
    )

    category.save()

    messages.success(
        request,
        "Category deleted successfully.",
    )

    return redirect("category_list")