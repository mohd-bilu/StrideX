from decimal import Decimal
import razorpay

from django.conf import settings
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.utils import timezone
from django.views.decorators.cache import never_cache
from xhtml2pdf import pisa

from Admin_panel.product.models import Variant
from Admin_panel.coupon_offer.models import Coupon, CouponUsage, Offer
from User_panel.Authentication.models import Address
from User_panel.Cart.models import Cart
from .models import Order, OrderItem


def get_cart_subtotal(cart):
    subtotal = Decimal("0.00")

    if not cart:
        return subtotal

    for item in cart.items.select_related("variant").all():
        subtotal += item.variant.price * item.quantity

    return subtotal


def calculate_coupon_discount(coupon, subtotal):
    if coupon.discount_type == "PERCENTAGE":
        discount = (
            subtotal
            * coupon.discount_value
            / Decimal("100")
        )

        if coupon.maximum_discount is not None:
            discount = min(
                discount,
                coupon.maximum_discount
            )

    elif coupon.discount_type == "FIXED":
        discount = coupon.discount_value

    else:
        discount = Decimal("0.00")

    discount = min(
        discount,
        subtotal
    )

    return discount.quantize(
        Decimal("0.01")
    )


def validate_coupon(coupon, subtotal, user):
    now = timezone.now()

    if not coupon.is_active:
        return (
            False,
            "This coupon is currently inactive.",
            Decimal("0.00")
        )

    if now < coupon.start_date:
        return (
            False,
            "This coupon is not active yet.",
            Decimal("0.00")
        )

    if now > coupon.expiry_date:
        return (
            False,
            "This coupon has expired.",
            Decimal("0.00")
        )

    if (
        coupon.usage_limit is not None
        and coupon.used_count >= coupon.usage_limit
    ):
        return (
            False,
            "This coupon usage limit has been reached.",
            Decimal("0.00")
        )

    if CouponUsage.objects.filter(
        coupon=coupon,
        user=user,
    ).exists():
        return (
            False,
            "You have already used this coupon.",
            Decimal("0.00")
        )

    if subtotal < coupon.minimum_purchase:
        return (
            False,
            (
                f"Minimum purchase amount for this coupon "
                f"is ₹{coupon.minimum_purchase:.2f}."
            ),
            Decimal("0.00")
        )

    discount = calculate_coupon_discount(
        coupon,
        subtotal
    )

    if discount <= 0:
        return (
            False,
            "This coupon does not provide a valid discount.",
            Decimal("0.00")
        )

    return (
        True,
        "",
        discount
    )


def get_best_offer_for_variant(variant):
    now = timezone.now()

    offers = Offer.objects.filter(
        is_active=True,
        start_date__lte=now,
        expiry_date__gte=now,
    ).filter(
        Q(
            offer_type="PRODUCT",
            product=variant.product,
        )
        | Q(
            offer_type="CATEGORY",
            category=variant.product.category,
        )
    )

    best_offer = None
    best_discount = Decimal("0.00")

    for offer in offers:

        if offer.discount_type == "PERCENTAGE":
            discount = (
                variant.price
                * offer.discount_value
                / Decimal("100")
            )

        elif offer.discount_type == "FIXED":
            discount = offer.discount_value

        else:
            discount = Decimal("0.00")

        discount = min(
            discount,
            variant.price
        )

        if discount > best_discount:
            best_discount = discount
            best_offer = offer

    return (
        best_offer,
        best_discount.quantize(
            Decimal("0.01")
        ),
    )


def calculate_cart_offer_discount(cart_items):
    offer_discount = Decimal("0.00")

    for item in cart_items:

        offer, discount_per_unit = (
            get_best_offer_for_variant(
                item.variant
            )
        )

        if offer:
            offer_discount += (
                discount_per_unit
                * item.quantity
            )

    return offer_discount.quantize(
        Decimal("0.01")
    )


@login_required
def checkout(request):
    cart = (
        Cart.objects.filter(
            user=request.user
        )
        .prefetch_related(
            "items__variant__images",
            "items__variant__product",
        )
        .first()
    )

    addresses = Address.objects.filter(
        user=request.user
    )

    default_address = addresses.filter(
        is_default=True
    ).first()

    selected_address_id = request.GET.get(
        "address"
    )

    selected_address = None

    if selected_address_id:
        selected_address = addresses.filter(
            id=selected_address_id
        ).first()

    if not selected_address:
        selected_address = default_address

    cart_items = []

    subtotal = Decimal("0.00")
    offer_discount = Decimal("0.00")
    coupon_discount = Decimal("0.00")
    discount = Decimal("0.00")
    shipping = Decimal("0.00")

    if cart:

        cart_items = list(
            cart.items.select_related(
                "variant",
                "variant__product",
                "variant__product__category",
            ).prefetch_related(
                "variant__images"
            )
        )

        for item in cart_items:

            item_total = (
                item.variant.price
                * item.quantity
            )

            item.item_total = (
                item_total
            )

            item.offer = None
            item.offer_discount = Decimal(
                "0.00"
            )

            item.offer_item_total = (
                item_total
            )

            offer, item_offer_discount = (
                get_best_offer_for_variant(
                    item.variant
                )
            )

            if offer:

                item.offer = offer

                item.offer_discount = (
                    item_offer_discount
                    * item.quantity
                )

                item.offer_item_total = (
                    item_total
                    - item.offer_discount
                )

                offer_discount += (
                    item.offer_discount
                )

            subtotal += item_total

    offer_discount = offer_discount.quantize(
        Decimal("0.01")
    )

    offer_subtotal = (
        subtotal
        - offer_discount
    )

    if offer_subtotal < 0:
        offer_subtotal = Decimal("0.00")

    coupon = None

    coupon_code = request.session.get(
        "checkout_coupon_code"
    )

    if coupon_code and offer_subtotal > 0:

        coupon = (
            Coupon.objects
            .filter(
                code__iexact=coupon_code
            )
            .first()
        )

        if coupon:

            valid, error, calculated_coupon_discount = (
                validate_coupon(
                    coupon,
                    offer_subtotal,
                    request.user,
                )
            )

            if valid:

                coupon_discount = (
                    calculated_coupon_discount
                )

            else:

                request.session.pop(
                    "checkout_coupon_code",
                    None
                )

                request.session.modified = True

                coupon = None

                coupon_discount = Decimal(
                    "0.00"
                )

    discount = (
        offer_discount
        + coupon_discount
    )

    total = (
        subtotal
        - discount
        + shipping
    )

    if total < 0:
        total = Decimal("0.00")

    context = {
        "cart": cart,
        "cart_items": cart_items,
        "addresses": addresses,
        "default_address": default_address,
        "selected_address": selected_address,

        "subtotal": subtotal,

        "offer_discount": offer_discount,
        "offer_subtotal": offer_subtotal,

        "coupon_discount": coupon_discount,

        "discount": discount,

        "shipping": shipping,
        "total": total,

        "payment_method": "COD",

        "coupon": coupon,

        "coupon_code": (
            coupon.code
            if coupon
            else ""
        ),
    }

    return render(
        request,
        "user_order/checkout.html",
        context,
    )


@login_required
def apply_coupon(request):
    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid request."
            },
            status=400
        )

    coupon_code = request.POST.get(
        "coupon_code",
        ""
    ).strip().upper()

    if not coupon_code:
        return JsonResponse(
            {
                "success": False,
                "message": "Please enter a coupon code."
            },
            status=400
        )

    existing_coupon_code = request.session.get(
        "checkout_coupon_code"
    )

    if existing_coupon_code:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "A coupon is already applied. "
                    "Remove it before applying another coupon."
                )
            },
            status=400
        )

    cart = (
        Cart.objects
        .filter(
            user=request.user
        )
        .prefetch_related(
            "items__variant__product",
            "items__variant__product__category",
        )
        .first()
    )

    if not cart:
        return JsonResponse(
            {
                "success": False,
                "message": "Your cart is empty."
            },
            status=400
        )

    cart_items = list(
        cart.items.select_related(
            "variant",
            "variant__product",
            "variant__product__category",
        )
    )

    if not cart_items:
        return JsonResponse(
            {
                "success": False,
                "message": "Your cart is empty."
            },
            status=400
        )

    subtotal = Decimal("0.00")

    for item in cart_items:

        variant = item.variant

        if (
            not variant.is_active
            or variant.is_deleted
            or not variant.product.is_active
            or variant.product.is_deleted
        ):
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        f"{variant.product.product_name} "
                        "is no longer available."
                    )
                },
                status=400
            )

        if item.quantity > variant.stock:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        f"Only {variant.stock} quantity of "
                        f"{variant.product.product_name} "
                        "is available."
                    )
                },
                status=400
            )

        subtotal += (
            variant.price
            * item.quantity
        )

    offer_discount = (
        calculate_cart_offer_discount(
            cart_items
        )
    )

    offer_subtotal = (
        subtotal
        - offer_discount
    )

    if offer_subtotal < 0:
        offer_subtotal = Decimal("0.00")

    coupon = (
        Coupon.objects
        .filter(
            code__iexact=coupon_code
        )
        .first()
    )

    if not coupon:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid coupon code."
            },
            status=404
        )

    valid, error, coupon_discount = (
        validate_coupon(
            coupon,
            offer_subtotal,
            request.user,
        )
    )

    if not valid:
        return JsonResponse(
            {
                "success": False,
                "message": error
            },
            status=400
        )

    request.session[
        "checkout_coupon_code"
    ] = coupon.code

    request.session.modified = True

    shipping = Decimal("0.00")

    total = (
        subtotal
        - offer_discount
        - coupon_discount
        + shipping
    )

    if total < 0:
        total = Decimal("0.00")

    total_discount = (
        offer_discount
        + coupon_discount
    )

    return JsonResponse(
        {
            "success": True,
            "message": (
                f"Coupon {coupon.code} "
                "applied successfully."
            ),
            "coupon_code": coupon.code,

            "offer_discount": str(
                offer_discount
            ),

            "coupon_discount": str(
                coupon_discount
            ),

            "discount": str(
                total_discount
            ),

            "subtotal": str(
                subtotal
            ),

            "offer_subtotal": str(
                offer_subtotal
            ),

            "shipping": str(
                shipping
            ),

            "total": str(
                total
            ),
        }
    )


@login_required
def remove_coupon(request):
    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid request."
            },
            status=400
        )

    request.session.pop(
        "checkout_coupon_code",
        None
    )

    request.session.modified = True

    cart = (
        Cart.objects
        .filter(
            user=request.user
        )
        .prefetch_related(
            "items__variant__product",
            "items__variant__product__category",
        )
        .first()
    )

    subtotal = Decimal("0.00")
    offer_discount = Decimal("0.00")

    if cart:

        cart_items = list(
            cart.items.select_related(
                "variant",
                "variant__product",
                "variant__product__category",
            )
        )

        for item in cart_items:

            item_subtotal = (
                item.variant.price
                * item.quantity
            )

            subtotal += item_subtotal

            offer, item_offer_discount = (
                get_best_offer_for_variant(
                    item.variant
                )
            )

            if offer:

                offer_discount += (
                    item_offer_discount
                    * item.quantity
                )

    offer_discount = offer_discount.quantize(
        Decimal("0.01")
    )

    offer_subtotal = (
        subtotal
        - offer_discount
    )

    if offer_subtotal < 0:
        offer_subtotal = Decimal("0.00")

    shipping = Decimal("0.00")

    total = (
        offer_subtotal
        + shipping
    )

    return JsonResponse(
        {
            "success": True,
            "message": "Coupon removed successfully.",

            "coupon_code": "",

            "offer_discount": str(
                offer_discount
            ),

            "coupon_discount": "0.00",

            "discount": str(
                offer_discount
            ),

            "subtotal": str(
                subtotal
            ),

            "offer_subtotal": str(
                offer_subtotal
            ),

            "shipping": str(
                shipping
            ),

            "total": str(
                total
            ),
        }
    )
def available_coupons(request):
    if not request.user.is_authenticated:
        return redirect("login")

    now = timezone.now()

    used_coupon_ids = CouponUsage.objects.filter(
        user=request.user
    ).values_list(
        "coupon_id",
        flat=True
    )

    coupons = Coupon.objects.filter(
        is_active=True,
    ).exclude(
        id__in=used_coupon_ids
    ).filter(
        Q(
            expiry_date__gte=now
        )
        |
        Q(
            start_date__gt=now
        )
    ).order_by(
        "start_date",
        "-created_at"
    )

    for coupon in coupons:

        if coupon.start_date > now:
            coupon.display_status = "UPCOMING"

        elif coupon.expiry_date < now:
            coupon.display_status = "EXPIRED"

        elif (
            coupon.usage_limit is not None
            and coupon.used_count >= coupon.usage_limit
        ):
            coupon.display_status = "EXHAUSTED"

        else:
            coupon.display_status = "ACTIVE"

    context = {
        "coupons": coupons,
    }

    return render(
        request,
        "user_order/available_coupons.html",
        context
    )
@login_required
def create_razorpay_order(request):
    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid request.",
            },
            status=400,
        )

    address_id = request.POST.get(
        "address"
    )

    if not address_id:
        return JsonResponse(
            {
                "success": False,
                "message": "Please select a delivery address.",
            },
            status=400,
        )

    address = Address.objects.filter(
        id=address_id,
        user=request.user,
    ).first()

    if not address:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid delivery address.",
            },
            status=400,
        )

    cart = (
        Cart.objects
        .filter(
            user=request.user
        )
        .prefetch_related(
            "items__variant__product",
            "items__variant__product__category",
        )
        .first()
    )

    if not cart:
        return JsonResponse(
            {
                "success": False,
                "message": "Your cart is empty.",
            },
            status=400,
        )

    cart_items = list(
        cart.items.select_related(
            "variant",
            "variant__product",
            "variant__product__category",
        )
    )

    if not cart_items:
        return JsonResponse(
            {
                "success": False,
                "message": "Your cart is empty.",
            },
            status=400,
        )

    try:
        subtotal = Decimal("0.00")
        offer_discount = Decimal("0.00")

        for item in cart_items:

            variant = item.variant

            if (
                not variant.is_active
                or variant.is_deleted
                or not variant.product.is_active
                or variant.product.is_deleted
            ):
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            f"{variant.product.product_name} "
                            "is no longer available."
                        ),
                    },
                    status=400,
                )

            if variant.stock <= 0:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            f"{variant.product.product_name} "
                            "is out of stock."
                        ),
                    },
                    status=400,
                )

            if item.quantity > variant.stock:
                return JsonResponse(
                    {
                        "success": False,
                        "message": (
                            f"Only {variant.stock} quantity of "
                            f"{variant.product.product_name} "
                            "is available."
                        ),
                    },
                    status=400,
                )

            item_subtotal = (
                variant.price
                * item.quantity
            )

            offer, offer_discount_per_unit = (
                get_best_offer_for_variant(
                    variant
                )
            )

            item_offer_discount = Decimal(
                "0.00"
            )

            if offer:
                item_offer_discount = (
                    offer_discount_per_unit
                    * item.quantity
                )

            subtotal += item_subtotal
            offer_discount += item_offer_discount

        offer_discount = offer_discount.quantize(
            Decimal("0.01")
        )

        offer_subtotal = (
            subtotal
            - offer_discount
        )

        if offer_subtotal < 0:
            offer_subtotal = Decimal("0.00")

        coupon = None
        coupon_discount = Decimal("0.00")

        coupon_code = request.session.get(
            "checkout_coupon_code"
        )

        if coupon_code:

            coupon = (
                Coupon.objects
                .filter(
                    code__iexact=coupon_code
                )
                .first()
            )

            if coupon:

                valid, error, calculated_coupon_discount = (
                    validate_coupon(
                        coupon,
                        offer_subtotal,
                        request.user,
                    )
                )

                if not valid:

                    request.session.pop(
                        "checkout_coupon_code",
                        None
                    )

                    request.session.modified = True

                    coupon = None

                    return JsonResponse(
                        {
                            "success": False,
                            "message": error,
                        },
                        status=400,
                    )

                coupon_discount = (
                    calculated_coupon_discount
                )

        total_discount = (
            offer_discount
            + coupon_discount
        )

        shipping = Decimal("0.00")

        total_amount = (
            subtotal
            - total_discount
            + shipping
        )

        if total_amount < 0:
            total_amount = Decimal("0.00")

        amount_in_paise = int(
            total_amount
            * Decimal("100")
        )

        if amount_in_paise <= 0:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid order amount.",
                },
                status=400,
            )

        if not settings.RAZORPAY_KEY_ID:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Razorpay is not configured."
                    ),
                },
                status=500,
            )

        if not settings.RAZORPAY_KEY_SECRET:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Razorpay is not configured."
                    ),
                },
                status=500,
            )

        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET,
            )
        )

        razorpay_order = client.order.create(
            {
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": (
                    f"ORDER-{request.user.id}-"
                    f"{int(timezone.now().timestamp())}"
                ),
            }
        )

        request.session[
            "razorpay_checkout"
        ] = {
            "address_id": address.id,
            "amount": str(total_amount),
            "razorpay_order_id": razorpay_order["id"],
        }

        request.session.modified = True

        return JsonResponse(
            {
                "success": True,
                "key": settings.RAZORPAY_KEY_ID,
                "razorpay_order_id": (
                    razorpay_order["id"]
                ),
                "amount": amount_in_paise,
                "currency": "INR",
                "name": "STRIDEX",
                "description": "StrideX Order",
            }
        )

    except Exception as error:

        print(
            "RAZORPAY ORDER ERROR:",
            error
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Unable to start online payment. "
                    "Please try again."
                ),
            },
            status=500,
        )
@login_required
def razorpay_payment_cancelled(request):
    request.session.pop("razorpay_checkout", None)
    request.session.modified = True

    messages.warning(
        request,
        "Payment was cancelled. You can try again."
    )

    return redirect("order:checkout")
@login_required
def razorpay_payment_failed(request):
    checkout_data = request.session.get("razorpay_checkout")

    if not checkout_data:
        messages.error(request, "Payment failed. Please try again.")
        return redirect("order:checkout")

    expected_amount = Decimal(checkout_data.get("amount", "0.00"))

    return render(
        request,
        "user_order/payment_failed.html",
        {
            "amount": expected_amount,
        },
    )
@login_required
def place_order(request):
    if request.method != "POST":
        return redirect(
            "order:checkout"
        )

    address_id = request.POST.get(
        "address"
    )

    payment_method = request.POST.get(
        "payment_method",
        "COD"
    ).strip().upper()

    if payment_method not in [
        "COD",
        "WALLET",
    ]:
        messages.error(
            request,
            "Invalid payment method."
        )

        return redirect(
            "order:checkout"
        )

    if not address_id:
        messages.error(
            request,
            "Please select a delivery address."
        )

        return redirect(
            "order:checkout"
        )

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user,
    )

    cart = (
        Cart.objects
        .filter(
            user=request.user
        )
        .prefetch_related(
            "items__variant__product",
        )
        .first()
    )

    if not cart:
        messages.error(
            request,
            "Your cart is empty."
        )

        return redirect(
            "cart"
        )

    cart_items = list(
        cart.items.select_related(
            "variant",
            "variant__product",
            "variant__product__category",
        )
    )

    if not cart_items:
        messages.error(
            request,
            "Your cart is empty."
        )

        return redirect(
            "cart"
        )

    try:
        with transaction.atomic():

            variant_ids = [
                item.variant_id
                for item in cart_items
            ]

            locked_variants = (
                Variant.objects
                .select_for_update()
                .filter(
                    id__in=variant_ids
                )
                .select_related(
                    "product",
                    "product__category",
                )
            )

            variants = {
                variant.id: variant
                for variant in locked_variants
            }

            subtotal = Decimal("0.00")
            offer_discount = Decimal("0.00")

            item_calculations = []

            for item in cart_items:

                variant = variants.get(
                    item.variant_id
                )

                if not variant:
                    raise ValueError(
                        "One of the products in your cart "
                        "is no longer available."
                    )

                if (
                    not variant.is_active
                    or variant.is_deleted
                    or not variant.product.is_active
                    or variant.product.is_deleted
                ):
                    raise ValueError(
                        f"{variant.product.product_name} "
                        "is no longer available."
                    )

                if variant.stock <= 0:
                    raise ValueError(
                        f"{variant.product.product_name} "
                        "is out of stock."
                    )

                if item.quantity > variant.stock:
                    raise ValueError(
                        f"Only {variant.stock} quantity of "
                        f"{variant.product.product_name} "
                        "is available."
                    )

                item_subtotal = (
                    variant.price
                    * item.quantity
                )

                offer, offer_discount_per_unit = (
                    get_best_offer_for_variant(
                        variant
                    )
                )

                item_offer_discount = Decimal(
                    "0.00"
                )

                if offer:
                    item_offer_discount = (
                        offer_discount_per_unit
                        * item.quantity
                    )

                subtotal += item_subtotal

                offer_discount += (
                    item_offer_discount
                )

                item_calculations.append(
                    {
                        "item": item,
                        "variant": variant,
                        "offer": offer,
                        "offer_discount": (
                            item_offer_discount
                        ),
                    }
                )

            offer_discount = offer_discount.quantize(
                Decimal("0.01")
            )

            offer_subtotal = (
                subtotal
                - offer_discount
            )

            if offer_subtotal < 0:
                offer_subtotal = Decimal(
                    "0.00"
                )

            coupon = None
            coupon_discount = Decimal("0.00")

            coupon_code = request.session.get(
                "checkout_coupon_code"
            )

            if coupon_code:

                coupon = (
                    Coupon.objects
                    .select_for_update()
                    .filter(
                        code__iexact=coupon_code
                    )
                    .first()
                )

                if not coupon:

                    request.session.pop(
                        "checkout_coupon_code",
                        None
                    )

                    request.session.modified = True

                    raise ValueError(
                        "The applied coupon is no longer available."
                    )

                valid, error, calculated_coupon_discount = (
                    validate_coupon(
                        coupon,
                        offer_subtotal,
                        request.user,
                    )
                )

                if not valid:

                    request.session.pop(
                        "checkout_coupon_code",
                        None
                    )

                    request.session.modified = True

                    raise ValueError(
                        error
                    )

                coupon_discount = (
                    calculated_coupon_discount
                )

            total_discount = (
                offer_discount
                + coupon_discount
            )

            shipping = Decimal("0.00")

            total_amount = (
                subtotal
                - total_discount
                + shipping
            )

            if total_amount < 0:
                total_amount = Decimal(
                    "0.00"
                )

            wallet = None

            if payment_method == "WALLET":

                from User_panel.Wallet.models import Wallet

                wallet = (
                    Wallet.objects
                    .select_for_update()
                    .filter(
                        user=request.user
                    )
                    .first()
                )

                if not wallet:
                    raise ValueError(
                        "You do not have a wallet yet."
                    )

                if wallet.balance < total_amount:
                    raise ValueError(
                        "Insufficient wallet balance."
                    )

                wallet.balance -= total_amount

                wallet.save(
                    update_fields=[
                        "balance",
                        "updated_at",
                    ]
                )

            order = Order.objects.create(
                user=request.user,
                address=address,
                payment_method=payment_method,
                payment_status=(
                    "PAID"
                    if payment_method == "WALLET"
                    else "PENDING"
                ),
                subtotal=subtotal,
                discount=total_discount,
                shipping_charge=shipping,
                total_amount=total_amount,
                order_status="PENDING",
            )

            for calculation in item_calculations:

                item = calculation["item"]
                variant = calculation["variant"]

                original_item_total = (
                    variant.price
                    * item.quantity
                )

                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    quantity=item.quantity,
                    price=variant.price,
                    total_price=original_item_total,
                    status="PENDING",
                )

                variant.stock -= item.quantity

                variant.save(
                    update_fields=[
                        "stock"
                    ]
                )

            if coupon:

                CouponUsage.objects.create(
                    coupon=coupon,
                    user=request.user,
                    order=order,
                )

                coupon.used_count += 1

                coupon.save(
                    update_fields=[
                        "used_count"
                    ]
                )

            if payment_method == "WALLET":

                from User_panel.Wallet.models import (
                    WalletTransaction
                )

                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type="DEBIT",
                    amount=total_amount,
                    description=(
                        f"Payment for order "
                        f"{order.order_id}"
                    ),
                    reference=order.order_id,
                )

            cart.items.all().delete()

            request.session.pop(
                "checkout_coupon_code",
                None
            )

            request.session.modified = True

        messages.success(
            request,
            "Your order has been placed successfully."
        )

        return redirect(
            "order:order_success",
            order_id=order.order_id,
        )

    except ValueError as error:

        print(
            "PLACE ORDER VALIDATION ERROR:",
            error
        )

        messages.error(
            request,
            str(error)
        )

        return redirect(
            "order:checkout"
        )

    except Exception as error:

        print(
            "PLACE ORDER ERROR:",
            error
        )

        messages.error(
            request,
            "Unable to place the order. Please try again."
        )

        return redirect(
            "order:checkout"
        )

@login_required
@transaction.atomic
def razorpay_payment_success(request):
    if request.method != "POST":
        return redirect(
            "order:checkout"
        )

    razorpay_payment_id = request.POST.get(
        "razorpay_payment_id",
        ""
    ).strip()

    razorpay_order_id = request.POST.get(
        "razorpay_order_id",
        ""
    ).strip()

    razorpay_signature = request.POST.get(
        "razorpay_signature",
        ""
    ).strip()

    checkout_data = request.session.get(
        "razorpay_checkout"
    )

    if not checkout_data:
        messages.error(
            request,
            "Payment session expired. Please try again."
        )

        return redirect(
            "order:checkout"
        )

    session_order_id = checkout_data.get(
        "razorpay_order_id"
    )

    if session_order_id != razorpay_order_id:
        messages.error(
            request,
            "Invalid payment order."
        )

        return redirect(
            "order:checkout"
        )

    if not all([
        razorpay_payment_id,
        razorpay_order_id,
        razorpay_signature,
    ]):
        messages.error(
            request,
            "Payment verification data is missing."
        )

        return redirect(
            "order:checkout"
        )

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET,
        )
    )

    try:

        client.utility.verify_payment_signature(
            {
                "razorpay_order_id":
                    razorpay_order_id,

                "razorpay_payment_id":
                    razorpay_payment_id,

                "razorpay_signature":
                    razorpay_signature,
            }
        )

    except Exception as error:

        print(
            "RAZORPAY SIGNATURE ERROR:",
            error
        )

        messages.error(
            request,
            "Payment verification failed."
        )

        return redirect(
            "order:checkout"
        )

    try:

        payment = client.payment.fetch(
            razorpay_payment_id
        )

    except Exception as error:

        print(
            "RAZORPAY PAYMENT FETCH ERROR:",
            error
        )

        messages.error(
            request,
            "Unable to verify payment."
        )

        return redirect(
            "order:checkout"
        )

    if payment.get("status") != "captured":

        messages.error(
            request,
            "Payment was not completed."
        )

        return redirect(
            "order:checkout"
        )

    paid_amount = (
        Decimal(
            str(
                payment.get(
                    "amount",
                    0
                )
            )
        )
        / Decimal("100")
    )

    expected_amount = Decimal(
        checkout_data.get(
            "amount",
            "0"
        )
    )

    if paid_amount != expected_amount:

        messages.error(
            request,
            "Payment amount verification failed."
        )

        return redirect(
            "order:checkout"
        )

    address_id = checkout_data.get(
        "address_id"
    )

    address = Address.objects.filter(
        id=address_id,
        user=request.user,
    ).first()

    if not address:

        messages.error(
            request,
            "Delivery address not found."
        )

        return redirect(
            "order:checkout"
        )

    cart = (
        Cart.objects
        .filter(
            user=request.user
        )
        .first()
    )

    if not cart:

        messages.error(
            request,
            "Your cart is empty."
        )

        return redirect(
            "cart"
        )

    cart_items = list(
        cart.items.select_related(
            "variant",
            "variant__product",
            "variant__product__category",
        )
    )

    if not cart_items:

        messages.error(
            request,
            "Your cart is empty."
        )

        return redirect(
            "cart"
        )

    variant_ids = [
        item.variant_id
        for item in cart_items
    ]

    locked_variants = (
        Variant.objects
        .select_for_update()
        .filter(
            id__in=variant_ids
        )
        .select_related(
            "product",
            "product__category",
        )
    )

    variants = {
        variant.id: variant
        for variant in locked_variants
    }

    subtotal = Decimal("0.00")
    offer_discount = Decimal("0.00")
    item_calculations = []

    for item in cart_items:

        variant = variants.get(
            item.variant_id
        )

        if not variant:

            messages.error(
                request,
                "One of the products is no longer available."
            )

            return redirect(
                "order:checkout"
            )

        if (
            not variant.is_active
            or variant.is_deleted
            or not variant.product.is_active
            or variant.product.is_deleted
        ):

            messages.error(
                request,
                f"{variant.product.product_name} "
                "is no longer available."
            )

            return redirect(
                "order:checkout"
            )

        if variant.stock <= 0:

            messages.error(
                request,
                f"{variant.product.product_name} "
                "is out of stock."
            )

            return redirect(
                "order:checkout"
            )

        if item.quantity > variant.stock:

            messages.error(
                request,
                f"Only {variant.stock} quantity of "
                f"{variant.product.product_name} "
                "is available."
            )

            return redirect(
                "order:checkout"
            )

        item_subtotal = (
            variant.price
            * item.quantity
        )

        offer, offer_discount_per_unit = (
            get_best_offer_for_variant(
                variant
            )
        )

        item_offer_discount = Decimal(
            "0.00"
        )

        if offer:

            item_offer_discount = (
                offer_discount_per_unit
                * item.quantity
            )

        subtotal += item_subtotal
        offer_discount += item_offer_discount

        item_calculations.append(
            {
                "item": item,
                "variant": variant,
                "offer_discount": (
                    item_offer_discount
                ),
            }
        )

    offer_discount = offer_discount.quantize(
        Decimal("0.01")
    )

    offer_subtotal = (
        subtotal
        - offer_discount
    )

    if offer_subtotal < 0:
        offer_subtotal = Decimal("0.00")

    coupon = None
    coupon_discount = Decimal("0.00")

    coupon_code = request.session.get(
        "checkout_coupon_code"
    )

    if coupon_code:

        coupon = (
            Coupon.objects
            .select_for_update()
            .filter(
                code__iexact=coupon_code
            )
            .first()
        )

        if not coupon:

            messages.error(
                request,
                "The applied coupon is no longer available."
            )

            return redirect(
                "order:checkout"
            )

        valid, error, calculated_coupon_discount = (
            validate_coupon(
                coupon,
                offer_subtotal,
                request.user,
            )
        )

        if not valid:

            messages.error(
                request,
                error
            )

            return redirect(
                "order:checkout"
            )

        coupon_discount = (
            calculated_coupon_discount
        )

    total_discount = (
        offer_discount
        + coupon_discount
    )

    shipping = Decimal("0.00")

    total_amount = (
        subtotal
        - total_discount
        + shipping
    )

    if total_amount < 0:
        total_amount = Decimal("0.00")

    if total_amount != expected_amount:

        messages.error(
            request,
            (
                "Order amount changed while "
                "payment was being completed. "
                "Please try again."
            )
        )

        return redirect(
            "order:checkout"
        )

    order = Order.objects.create(
        user=request.user,
        address=address,
        payment_method="RAZORPAY",
        payment_status="PAID",
        coupon=coupon,
        subtotal=subtotal,
        discount=total_discount,
        shipping_charge=shipping,
        total_amount=total_amount,
        order_status="PENDING",
    )

    for calculation in item_calculations:

        item = calculation["item"]
        variant = calculation["variant"]

        original_item_total = (
            variant.price
            * item.quantity
        )

        OrderItem.objects.create(
            order=order,
            variant=variant,
            quantity=item.quantity,
            price=variant.price,
            total_price=original_item_total,
            status="PENDING",
        )

        variant.stock -= item.quantity

        variant.save(
            update_fields=[
                "stock"
            ]
        )

    if coupon:

        CouponUsage.objects.create(
            coupon=coupon,
            user=request.user,
            order=order,
        )

        coupon.used_count += 1

        coupon.save(
            update_fields=[
                "used_count"
            ]
        )

    cart.items.all().delete()

    request.session.pop(
        "checkout_coupon_code",
        None
    )

    request.session.pop(
        "razorpay_checkout",
        None
    )

    request.session.modified = True

    messages.success(
        request,
        "Your order has been placed successfully."
    )

    return redirect(
        "order:order_success",
        order_id=order.order_id,
    )
@login_required
def order_success(request, order_id):
    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user,
    )

    return render(
        request,
        "user_order/order_success.html",
        {
            "order": order,
        },
    )


@login_required
def order_list(request):
    search = request.GET.get(
        "search",
        ""
    ).strip()

    status = request.GET.get(
        "status",
        ""
    ).strip()

    orders = (
        Order.objects
        .filter(
            user=request.user
        )
        .prefetch_related(
            "items__variant__product",
        )
        .order_by(
            "-created_at"
        )
    )

    if search:
        orders = orders.filter(
            order_id__icontains=search
        )

    if status:
        orders = orders.filter(
            order_status=status
        )

    paginator = Paginator(
        orders,
        5
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    return render(
        request,
        "user_order/order_list.html",
        {
            "orders": page_obj,
            "page_obj": page_obj,
            "search": search,
            "status": status,
        },
    )


@login_required(login_url="login")
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items__variant__product",
            "items__variant__images",
        ),
        order_id=order_id,
        user=request.user,
    )

    order_items = order.items.all()

    has_returnable_items = order_items.filter(
        status="DELIVERED"
    ).exists()

    return render(
        request,
        "user_order/order_detail.html",
        {
            "order": order,
            "order_items": order_items,
            "has_returnable_items": has_returnable_items,
        },
    )


@login_required(login_url="login")
def download_invoice(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related(
            "address",
        ).prefetch_related(
            "items__variant__product",
            "items__variant__images",
        ),
        order_id=order_id,
        user=request.user,
    )

    invoice_items = order.items.all()

    returned_items = invoice_items.filter(
        status="RETURNED"
    )

    return_requested_items = invoice_items.filter(
        status="RETURN_REQUESTED"
    )

    rejected_items = invoice_items.filter(
        status="REJECTED"
    )

    context = {
        "order": order,
        "invoice_items": invoice_items,
        "returned_items": returned_items,
        "return_requested_items": return_requested_items,
        "rejected_items": rejected_items,
        "has_return_information": (
            returned_items.exists()
            or return_requested_items.exists()
            or rejected_items.exists()
        ),
        "returned_amount": sum(
            item.total_price
            for item in returned_items
        ),
        "return_requested_amount": sum(
            item.total_price
            for item in return_requested_items
        ),
    }

    template = get_template(
        "user_order/invoice_pdf.html"
    )

    html = template.render(
        context,
        request,
    )

    response = HttpResponse(
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="Invoice-{order.order_id}.pdf"'
    )

    pisa_status = pisa.CreatePDF(
        html,
        dest=response,
    )

    if pisa_status.err:
        return HttpResponse(
            "Error generating invoice.",
            status=500,
        )

    return response


@never_cache
@login_required(login_url="login")
@transaction.atomic
def cancel_order(request, order_id):
    if request.method != "POST":
        return redirect("order:order_detail", order_id=order_id)

    order = get_object_or_404(
        Order.objects.select_for_update().prefetch_related("items__variant"),
        order_id=order_id,
        user=request.user,
    )

    if order.order_status not in ["PENDING", "PROCESSING"]:
        messages.error(request, "This order cannot be cancelled.")
        return redirect("order:order_detail", order_id=order.order_id)

    cancel_reason = request.POST.get("cancel_reason", "").strip()

    if not cancel_reason:
        messages.error(request, "Please provide a cancellation reason.")
        return redirect("order:order_detail", order_id=order.order_id)

    items_to_cancel = list(
        order.items.filter(
            status__in=["PENDING", "PROCESSING"]
        )
    )

    if not items_to_cancel:
        messages.error(request, "There are no cancellable products in this order.")
        return redirect("order:order_detail", order_id=order.order_id)

    refund_amount = Decimal("0.00")

    if order.payment_status == "PAID" and order.subtotal > 0:
        for item in items_to_cancel:
            item_gross = item.price * item.quantity
            item_discount = (
                order.discount * item_gross / order.subtotal
            )
            item_refund = item_gross - item_discount

            if item_refund < 0:
                item_refund = Decimal("0.00")

            refund_amount += item_refund

    for item in items_to_cancel:
        variant = (
            Variant.objects
            .select_for_update()
            .get(id=item.variant_id)
        )

        item.status = "CANCELLED"
        item.cancel_reason = cancel_reason
        item.save(update_fields=["status", "cancel_reason"])

        variant.stock += item.quantity
        variant.save(update_fields=["stock"])

    order.order_status = "CANCELLED"
    order.save(update_fields=["order_status", "updated_at"])

    if refund_amount > 0:
        from User_panel.Wallet.models import Wallet, WalletTransaction

        wallet, created = Wallet.objects.select_for_update().get_or_create(
            user=request.user,
            defaults={"balance": Decimal("0.00")},
        )

        refund_reference = f"REFUND-{order.order_id}"

        existing_refund = WalletTransaction.objects.filter(
            wallet=wallet,
            reference=refund_reference,
            transaction_type="CREDIT",
        ).exists()

        if not existing_refund:
            wallet.balance += refund_amount
            wallet.save(update_fields=["balance", "updated_at"])

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="CREDIT",
                amount=refund_amount,
                description=f"Refund for cancelled order {order.order_id}",
                reference=refund_reference,
            )

            messages.success(
                request,
                f"Order cancelled successfully. ₹{refund_amount:.2f} has been refunded to your wallet.",
            )
        else:
            messages.success(request, "Order cancelled successfully.")
    else:
        messages.success(request, "Order cancelled successfully.")

    return redirect(
        "order:order_detail",
        order_id=order.order_id,
    )


@never_cache
@login_required(login_url="login")
@transaction.atomic
def cancel_order_item(request, order_id, item_id):
    if request.method != "POST":
        return redirect("order:order_detail", order_id=order_id)

    order = get_object_or_404(
        Order.objects.select_for_update(),
        order_id=order_id,
        user=request.user,
    )

    item = get_object_or_404(
        OrderItem.objects.select_related(
            "variant",
            "variant__product",
        ),
        id=item_id,
        order=order,
    )

    if item.status not in ["PENDING", "PROCESSING"]:
        messages.error(
            request,
            "This product cannot be cancelled at this stage.",
        )
        return redirect(
            "order:order_detail",
            order_id=order.order_id,
        )

    cancel_reason = request.POST.get("cancel_reason", "").strip()

    if not cancel_reason:
        messages.error(
            request,
            "Please provide a cancellation reason.",
        )
        return redirect(
            "order:order_detail",
            order_id=order.order_id,
        )

    variant = (
        Variant.objects
        .select_for_update()
        .get(id=item.variant_id)
    )

    refund_amount = Decimal("0.00")

    if order.payment_status == "PAID" and order.subtotal > 0:
        item_gross = item.price * item.quantity
        item_discount = (
            order.discount * item_gross / order.subtotal
        )
        refund_amount = item_gross - item_discount

        if refund_amount < 0:
            refund_amount = Decimal("0.00")

    item.status = "CANCELLED"
    item.cancel_reason = cancel_reason
    item.save(update_fields=["status", "cancel_reason"])

    variant.stock += item.quantity
    variant.save(update_fields=["stock"])

    if refund_amount > 0:
        from User_panel.Wallet.models import Wallet, WalletTransaction

        wallet, created = Wallet.objects.select_for_update().get_or_create(
            user=request.user,
            defaults={"balance": Decimal("0.00")},
        )

        refund_reference = f"REFUND-{order.order_id}-ITEM-{item.id}"

        existing_refund = WalletTransaction.objects.filter(
            wallet=wallet,
            reference=refund_reference,
            transaction_type="CREDIT",
        ).exists()

        if not existing_refund:
            wallet.balance += refund_amount
            wallet.save(update_fields=["balance", "updated_at"])

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="CREDIT",
                amount=refund_amount,
                description=(
                    f"Refund for cancelled item "
                    f"{item.variant.product.product_name} "
                    f"in order {order.order_id}"
                ),
                reference=refund_reference,
            )

    remaining_items = order.items.exclude(
        status="CANCELLED"
    ).exists()

    if not remaining_items:
        order.order_status = "CANCELLED"
        order.save(
            update_fields=[
                "order_status",
                "updated_at",
            ]
        )

    if refund_amount > 0:
        messages.success(
            request,
            f"{item.variant.product.product_name} cancelled successfully. "
            f"₹{refund_amount:.2f} has been refunded to your wallet.",
        )
    else:
        messages.success(
            request,
            f"{item.variant.product.product_name} has been cancelled successfully.",
        )

    return redirect(
        "order:order_detail",
        order_id=order.order_id,
    )

@never_cache
@login_required(login_url="login")
def request_return(request, order_id):
    if request.method != "POST":
        return redirect(
            "order:order_detail",
            order_id=order_id,
        )

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items__variant__product",
            "items__variant__images",
        ),
        order_id=order_id,
        user=request.user,
    )

    item_id = request.POST.get(
        "item_id"
    )

    return_reason = request.POST.get(
        "return_reason",
        "",
    ).strip()

    if not item_id:
        messages.error(
            request,
            "Please select a product to return.",
        )

        return redirect(
            "order:order_detail",
            order_id=order.order_id,
        )

    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order=order,
    )

    if item.status != "DELIVERED":
        messages.error(
            request,
            "Only delivered products can be returned.",
        )

        return redirect(
            "order:order_detail",
            order_id=order.order_id,
        )

    if not return_reason:
        messages.error(
            request,
            "Please provide a return reason.",
        )

        return redirect(
            "order:order_detail",
            order_id=order.order_id,
        )

    item.return_reason = return_reason
    item.status = "RETURN_REQUESTED"

    item.save(
        update_fields=[
            "return_reason",
            "status",
        ]
    )

    messages.success(
        request,
        "Return request submitted successfully.",
    )

    return redirect(
        "order:order_detail",
        order_id=order.order_id,
    )