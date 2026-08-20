from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CouponForm
from .models import Coupon


def coupon_list(request):
    search_query = request.GET.get(
        "search",
        ""
    ).strip()

    coupons = Coupon.objects.all()

    if search_query:
        coupons = coupons.filter(
            Q(code__icontains=search_query)
        )

    paginator = Paginator(
        coupons,
        10
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    now = timezone.now()

    for coupon in page_obj:
        if not coupon.is_active:
            coupon.display_status = "INACTIVE"
        elif coupon.expiry_date < now:
            coupon.display_status = "EXPIRED"
        elif coupon.start_date > now:
            coupon.display_status = "UPCOMING"
        elif (
            coupon.usage_limit
            and coupon.used_count >= coupon.usage_limit
        ):
            coupon.display_status = "EXHAUSTED"
        else:
            coupon.display_status = "ACTIVE"

    context = {
        "coupons": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
        "total_coupons": coupons.count(),
    }

    return render(
        request,
        "coupon_offer/coupon_list.html",
        context
    )


def coupon_add(request):
    if request.method == "POST":
        form = CouponForm(
            request.POST
        )

        if form.is_valid():
            coupon = form.save()

            messages.success(
                request,
                f"Coupon {coupon.code} created successfully."
            )

            return redirect(
                "coupon_offer:coupon_list"
            )

    else:
        form = CouponForm()

    context = {
        "form": form,
        "page_title": "Add Coupon",
        "submit_text": "Create Coupon",
    }

    return render(
        request,
        "coupon_offer/coupon_add.html",
        context
    )


def coupon_edit(request, coupon_id):
    coupon = get_object_or_404(
        Coupon,
        id=coupon_id
    )

    if request.method == "POST":
        form = CouponForm(
            request.POST,
            instance=coupon
        )

        if form.is_valid():
            coupon = form.save()

            messages.success(
                request,
                f"Coupon {coupon.code} updated successfully."
            )

            return redirect(
                "coupon_offer:coupon_list"
            )

    else:
        form = CouponForm(
            instance=coupon
        )

    context = {
        "form": form,
        "coupon": coupon,
        "page_title": "Edit Coupon",
        "submit_text": "Update Coupon",
    }

    return render(
        request,
        "coupon_offer/coupon_edit.html",
        context
    )


def coupon_delete(request, coupon_id):
    coupon = get_object_or_404(
        Coupon,
        id=coupon_id
    )

    if request.method == "POST":
        code = coupon.code

        coupon.delete()

        messages.success(
            request,
            f"Coupon {code} deleted successfully."
        )

        return redirect(
            "coupon_offer:coupon_list"
        )

    return redirect(
        "coupon_offer:coupon_list"
    )