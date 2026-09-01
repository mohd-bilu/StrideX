from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CouponForm, OfferForm
from .models import Coupon, Offer


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
            coupon.usage_limit is not None
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


def offer_list(request):
    search_query = request.GET.get(
        "search",
        ""
    ).strip()

    offers = (
        Offer.objects
        .select_related(
            "product",
            "category",
        )
        .all()
    )

    if search_query:
        offers = offers.filter(
            Q(name__icontains=search_query)
            | Q(product__product_name__icontains=search_query)
            | Q(category__category_name__icontains=search_query)
        )

    paginator = Paginator(
        offers,
        10
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    now = timezone.now()

    for offer in page_obj:

        if not offer.is_active:
            offer.display_status = "INACTIVE"

        elif offer.expiry_date < now:
            offer.display_status = "EXPIRED"

        elif offer.start_date > now:
            offer.display_status = "UPCOMING"

        else:
            offer.display_status = "ACTIVE"

    context = {
        "offers": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
        "total_offers": offers.count(),
    }

    return render(
        request,
        "coupon_offer/offer_list.html",
        context
    )


def offer_add(request):
    if request.method == "POST":
        form = OfferForm(
            request.POST
        )

        if form.is_valid():
            offer = form.save()

            messages.success(
                request,
                f"Offer {offer.name} created successfully."
            )

            return redirect(
                "coupon_offer:offer_list"
            )

    else:
        form = OfferForm()

    context = {
        "form": form,
        "page_title": "Add Offer",
        "submit_text": "Create Offer",
    }

    return render(
        request,
        "coupon_offer/offer_form.html",
        context
    )


def offer_edit(request, offer_id):
    offer = get_object_or_404(
        Offer,
        id=offer_id
    )

    if request.method == "POST":
        form = OfferForm(
            request.POST,
            instance=offer
        )

        if form.is_valid():
            offer = form.save()

            messages.success(
                request,
                f"Offer {offer.name} updated successfully."
            )

            return redirect(
                "coupon_offer:offer_list"
            )

    else:
        form = OfferForm(
            instance=offer
        )

    context = {
        "form": form,
        "offer": offer,
        "page_title": "Edit Offer",
        "submit_text": "Update Offer",
    }

    return render(
        request,
        "coupon_offer/offer_form.html",
        context
    )


def offer_delete(request, offer_id):
    offer = get_object_or_404(
        Offer,
        id=offer_id
    )

    if request.method == "POST":
        offer_name = offer.name

        offer.delete()

        messages.success(
            request,
            f"Offer {offer_name} deleted successfully."
        )

        return redirect(
            "coupon_offer:offer_list"
        )

    return redirect(
        "coupon_offer:offer_list"
    )