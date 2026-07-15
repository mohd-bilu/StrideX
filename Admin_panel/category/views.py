from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CategoryForm
from .models import Category


def add_category(request):

    if request.method == "POST":

        form = CategoryForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Category added successfully.",
            )

            return redirect(
                "category_list"
            )

    else:

        form = CategoryForm()

    context = {
        "form": form,
    }

    return render(
        request,
        "category/add_category.html",
        context,
    )


def category_list(request):

    search_query = request.GET.get(
        "search",
        ""
    ).strip()

    categories = Category.objects.filter(
        is_deleted=False,
    )

    if search_query:

        categories = categories.filter(
            Q(category_name__icontains=search_query)
            |
            Q(description__icontains=search_query)
        )

    total_categories = categories.count()

    active_categories = categories.filter(
        is_active=True,
    ).count()

    inactive_categories = categories.filter(
        is_active=False,
    ).count()

    paginator = Paginator(
        categories,
        5,
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "total_categories": total_categories,
        "active_categories": active_categories,
        "inactive_categories": inactive_categories,
    }

    return render(
        request,
        "category/category_list.html",
        context,
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

            form.save()

            messages.success(
                request,
                "Category updated successfully.",
            )

            return redirect(
                "category_list"
            )

    else:

        form = CategoryForm(
            instance=category,
        )

    context = {
        "form": form,
        "category": category,
    }

    return render(
        request,
        "category/edit_category.html",
        context,
    )


def delete_category(request, category_id):

    category = get_object_or_404(
        Category,
        id=category_id,
        is_deleted=False,
    )

    category.is_deleted = True

    category.save()

    messages.success(
        request,
        "Category deleted successfully.",
    )

    return redirect(
        "category_list"
    )