from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CouponForm, OfferForm
from .models import Coupon, Offer


def coupon_list(request):
    search = request.GET.get("search", "").strip()
    coupons = Coupon.objects.all()

    if search:
        coupons = coupons.filter(
            Q(code__icontains=search)
            | Q(discount_type__icontains=search)
        )

    paginator = Paginator(coupons, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    now = timezone.localtime(timezone.now())

    for coupon in page_obj:
        if not coupon.is_active:
            coupon.display_status = "INACTIVE"
        elif coupon.expiry_date <= now:
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

    active_count = Coupon.objects.filter(
        is_active=True,
        start_date__lte=now,
        expiry_date__gt=now,
    ).filter(
        Q(usage_limit__isnull=True)
        | Q(used_count__lt=Q("usage_limit"))
    ).count()

    return render(
        request,
        "coupon_offer/coupon_list.html",
        {
            "coupons": page_obj,
            "search": search,
            "active_count": active_count,
        },
    )


def coupon_add(request):
    if request.method == "POST":
        form = CouponForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Coupon created successfully.")
            return redirect("coupon_offer:coupon_list")
    else:
        form = CouponForm()

    return render(
        request,
        "coupon_offer/coupon_add.html",
        {"form": form},
    )


def coupon_edit(request, coupon_id):
    coupon = get_object_or_404(Coupon, pk=coupon_id)

    if request.method == "POST":
        form = CouponForm(request.POST, instance=coupon)

        if form.is_valid():
            form.save()
            messages.success(request, "Coupon updated successfully.")
            return redirect("coupon_offer:coupon_list")
    else:
        form = CouponForm(instance=coupon)

    return render(
        request,
        "coupon_offer/coupon_edit.html",
        {
            "form": form,
            "coupon": coupon,
        },
    )


def coupon_delete(request, coupon_id):
    if request.method != "POST":
        return redirect("coupon_offer:coupon_list")

    coupon = get_object_or_404(Coupon, pk=coupon_id)
    coupon.delete()

    messages.success(request, "Coupon deleted successfully.")
    return redirect("coupon_offer:coupon_list")


def offer_list(request):
    search = request.GET.get("search", "").strip()

    offers = Offer.objects.select_related(
        "product",
        "category",
    )

    if search:
        offers = offers.filter(
            Q(name__icontains=search)
            | Q(offer_type__icontains=search)
            | Q(discount_type__icontains=search)
            | Q(product__product_name__icontains=search)
            | Q(category__name__icontains=search)
        )

    paginator = Paginator(offers, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    now = timezone.localtime(timezone.now())

    for offer in page_obj:
        if not offer.is_active:
            offer.display_status = "INACTIVE"
        elif offer.expiry_date <= now:
            offer.display_status = "EXPIRED"
        elif offer.start_date > now:
            offer.display_status = "UPCOMING"
        else:
            offer.display_status = "ACTIVE"

    active_count = Offer.objects.filter(
        is_active=True,
        start_date__lte=now,
        expiry_date__gt=now,
    ).count()

    return render(
        request,
        "coupon_offer/offer_list.html",
        {
            "offers": page_obj,
            "search": search,
            "active_count": active_count,
        },
    )


def offer_add(request):
    if request.method == "POST":
        form = OfferForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Offer created successfully.")
            return redirect("coupon_offer:offer_list")
    else:
        form = OfferForm()

    return render(
        request,
        "coupon_offer/offer_form.html",
        {
            "form": form,
            "page_title": "Add Offer",
            "submit_text": "Create Offer",
        },
    )


def offer_edit(request, offer_id):
    offer = get_object_or_404(Offer, pk=offer_id)

    if request.method == "POST":
        form = OfferForm(request.POST, instance=offer)

        if form.is_valid():
            form.save()
            messages.success(request, "Offer updated successfully.")
            return redirect("coupon_offer:offer_list")
    else:
        form = OfferForm(instance=offer)

    return render(
        request,
        "coupon_offer/offer_form.html",
        {
            "form": form,
            "offer": offer,
            "page_title": "Edit Offer",
            "submit_text": "Update Offer",
        },
    )


def offer_delete(request, offer_id):
    if request.method != "POST":
        return redirect("coupon_offer:offer_list")

    offer = get_object_or_404(Offer, pk=offer_id)
    offer.delete()

    messages.success(request, "Offer deleted successfully.")
    return redirect("coupon_offer:offer_list")