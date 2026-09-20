from decimal import Decimal

import razorpay
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from Admin_panel.product.models import Variant
from Admin_panel.coupon_offer.models import Coupon, CouponUsage, Offer
from User_panel.Authentication.models import Address
from User_panel.Cart.models import Cart
from User_panel.Order.models import Order, OrderItem

def get_cart_subtotal(cart):
    subtotal = Decimal("0.00")
    if not cart:
        return subtotal
    for item in cart.items.select_related("variant"):
        subtotal += item.variant.price * item.quantity
    return subtotal

def calculate_coupon_discount(coupon, subtotal):
    if coupon.discount_type == "PERCENTAGE":
        discount = subtotal * coupon.discount_value / Decimal("100")
        if coupon.maximum_discount is not None:
            discount = min(discount, coupon.maximum_discount)
    elif coupon.discount_type == "FIXED":
        discount = coupon.discount_value
    else:
        return Decimal("0.00")
    return min(discount, subtotal).quantize(Decimal("0.01"))

def validate_coupon(coupon, subtotal, user):
    now = timezone.localtime(timezone.now())
    if not coupon.is_active:
        return False, "This coupon is currently inactive.", Decimal("0.00")
    if now < timezone.localtime(coupon.start_date):
        return False, "This coupon is not active yet.", Decimal("0.00")
    if now >= timezone.localtime(coupon.expiry_date):
        return False, "This coupon has expired.", Decimal("0.00")
    if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
        return False, "This coupon usage limit has been reached.", Decimal("0.00")
    if CouponUsage.objects.filter(coupon=coupon, user=user).exists():
        return False, "You have already used this coupon.", Decimal("0.00")
    if subtotal < coupon.minimum_purchase:
        return False, f"Minimum purchase amount for this coupon is ₹{coupon.minimum_purchase:.2f}.", Decimal("0.00")
    discount = calculate_coupon_discount(coupon, subtotal)
    if discount <= 0:
        return False, "This coupon does not provide a valid discount.", Decimal("0.00")
    return True, "", discount

def get_best_offer_for_variant(variant):
    now = timezone.now()
    offers = Offer.objects.filter(
        is_active=True,
        start_date__lte=now,
        expiry_date__gt=now,
    ).filter(
        Q(offer_type="PRODUCT", product=variant.product)
        | Q(offer_type="CATEGORY", category=variant.product.category)
    )
    best_offer = None
    best_discount = Decimal("0.00")
    for offer in offers:
        if offer.discount_type == "PERCENTAGE":
            discount = variant.price * offer.discount_value / Decimal("100")
        elif offer.discount_type == "FIXED":
            discount = offer.discount_value
        else:
            continue
        discount = min(discount, variant.price)
        if discount > best_discount:
            best_offer = offer
            best_discount = discount
    return best_offer, best_discount.quantize(Decimal("0.01"))
def get_buy_now_item(request):
    if not request.session.get("buy_now"):
        return None

    variant_id = request.session.get("buy_now_variant_id")
    quantity = request.session.get("buy_now_quantity", 1)

    if not variant_id:
        return None

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 1

    quantity = max(quantity, 1)

    variant = (
        Variant.objects
        .select_related(
            "product",
            "product__category",
        )
        .prefetch_related("images")
        .filter(
            id=variant_id,
            is_active=True,
            is_deleted=False,
            product__is_active=True,
            product__is_deleted=False,
            product__category__is_active=True,
            product__category__is_deleted=False,
        )
        .first()
    )

    if variant is None:
        raise ValueError(
            "The selected product is no longer available."
        )

    if variant.stock < quantity:
        raise ValueError(
            f"Only {variant.stock} quantity of "
            f"{variant.product.product_name} is available."
        )

    return variant, quantity


def get_checkout_items(request, force_buy_now=False):
    if force_buy_now or request.session.get("buy_now"):
        buy_now_item = get_buy_now_item(request)

        if not buy_now_item:
            raise ValueError(
                "The selected Buy Now product is no longer available."
            )

        return [buy_now_item], True

    cart = Cart.objects.filter(user=request.user).first()

    if not cart:
        raise ValueError("Your cart is empty.")

    cart_items = list(
        cart.items.select_related(
            "variant",
            "variant__product",
            "variant__product__category",
        ).prefetch_related("variant__images")
    )

    if not cart_items:
        raise ValueError("Your cart is empty.")

    items = []

    for item in cart_items:
        variant = item.variant

        if item.quantity > variant.stock:
            raise ValueError(
                f"Only {variant.stock} quantity of "
                f"{variant.product.product_name} is available."
            )

        items.append((variant, item.quantity))

    return items, False
def calculate_checkout_totals(items):
    original_subtotal = Decimal("0.00")
    offer_discount = Decimal("0.00")
    item_calculations = []
    for variant, quantity in items:
        original_item_total = variant.price * quantity
        offer, discount_per_unit = get_best_offer_for_variant(variant)
        offer_item_total = (variant.price - discount_per_unit) * quantity
        item_offer_discount = discount_per_unit * quantity
        original_subtotal += original_item_total
        offer_discount += item_offer_discount
        item_calculations.append({
            "variant": variant,
            "quantity": quantity,
            "offer": offer,
            "offer_discount": discount_per_unit,
            "original_item_total": original_item_total,
            "offer_item_total": offer_item_total,
            "item_offer_discount": item_offer_discount,
        })
    offer_discount = offer_discount.quantize(Decimal("0.01"))
    offer_subtotal = max(original_subtotal - offer_discount, Decimal("0.00"))
    return original_subtotal, offer_subtotal, offer_discount, item_calculations

def calculate_cart_offer_discount(cart_items):
    offer_discount = Decimal("0.00")
    for item in cart_items:
        _, discount_per_unit = get_best_offer_for_variant(item.variant)
        offer_discount += discount_per_unit * item.quantity
    return offer_discount.quantize(Decimal("0.01"))

def get_cart_totals(cart):
    if not cart:
        return Decimal("0.00"), Decimal("0.00"), Decimal("0.00")
    items = [(item.variant, item.quantity) for item in cart.items.select_related("variant__product__category")]
    return calculate_checkout_totals(items)[0:3]


def get_coupon_for_checkout(request, subtotal):
    coupon_code = request.session.get("checkout_coupon_code")
    if not coupon_code:
        return None, Decimal("0.00")
    coupon = Coupon.objects.filter(code__iexact=coupon_code).first()
    if not coupon:
        request.session.pop("checkout_coupon_code", None)
        request.session.modified = True
        return None, Decimal("0.00")
    valid, _, discount = validate_coupon(coupon, subtotal, request.user)
    if not valid:
        request.session.pop("checkout_coupon_code", None)
        request.session.modified = True
        return None, Decimal("0.00")
    return coupon, discount

def clear_checkout_session(request, clear_buy_now=True):
    request.session.pop("checkout_coupon_code", None)
    request.session.pop("razorpay_checkout", None)
    if clear_buy_now:
        request.session.pop("buy_now", None)
        request.session.pop("buy_now_variant_id", None)
        request.session.pop("buy_now_quantity", None)
    request.session.modified = True

@never_cache
@login_required(login_url="login")
def checkout(request):
    if request.session.get("checkout_completed"):
        request.session.pop("checkout_completed", None)
        request.session.modified = True
        messages.info(
            request,
            "This order has already been placed successfully."
        )
        return redirect("order:order_list")   
    buy_now = request.GET.get("buy_now") == "1"
    selected_coupon_code = request.GET.get("coupon", "").strip().upper()

    if selected_coupon_code:
        request.session.pop("checkout_coupon_code", None)
        request.session.modified = True

    if buy_now:
        variant_id = request.GET.get("variant_id")
        quantity = request.GET.get("quantity", "1")

        if not variant_id:
            messages.error(request, "Please select a product before checkout.")
            return redirect("product:product_list")

        try:
            quantity = max(int(quantity), 1)
        except (TypeError, ValueError):
            quantity = 1

        variant = (
            Variant.objects
            .select_related(
                "product",
                "product__category",
            )
            .prefetch_related("images")
            .filter(
                id=variant_id,
                is_active=True,
                is_deleted=False,
                product__is_active=True,
                product__is_deleted=False,
                product__category__is_active=True,
                product__category__is_deleted=False,
            )
            .first()
        )

        if variant is None:
            messages.error(request, "The selected product is no longer available.")
            return redirect("product:product_list")

        if variant.stock < quantity:
            messages.error(
                request,
                "The selected quantity is not available."
            )
            return redirect(
                "product:product_detail",
                product_id=variant.product.id,
            )

        request.session["buy_now"] = True
        request.session["buy_now_variant_id"] = variant.id
        request.session["buy_now_quantity"] = quantity
        request.session.pop("checkout_coupon_code", None)
        request.session.pop("razorpay_checkout", None)
        request.session.modified = True

    else:
        request.session.pop("buy_now", None)
        request.session.pop("buy_now_variant_id", None)
        request.session.pop("buy_now_quantity", None)
        request.session.pop("razorpay_checkout", None)
        request.session.modified = True

    try:
        items, is_buy_now = get_checkout_items(
            request,
            force_buy_now=buy_now,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("product:product_list")

    if not is_buy_now:
        unavailable_item = next(
            (
                variant
                for variant, quantity in items
                if (
                    not variant.is_active
                    or variant.is_deleted
                    or not variant.product.is_active
                    or variant.product.is_deleted
                    or not variant.product.category.is_active
                    or variant.product.category.is_deleted
                )
            ),
            None,
        )

        if unavailable_item:
            messages.error(
                request,
                "One or more products in your cart are no longer available."
            )
            return redirect("cart")

    original_subtotal, offer_subtotal, offer_discount, item_calculations = (
        calculate_checkout_totals(items)
    )

    cart_items = []

    for calculation in item_calculations:
        variant = calculation["variant"]

        cart_items.append({
            "variant": variant,
            "quantity": calculation["quantity"],
            "original_price": variant.price,
            "offer": calculation["offer"],
            "offer_discount": calculation["offer_discount"],
            "offer_price": (
                variant.price -
                calculation["offer_discount"]
            ),
            "item_subtotal": calculation["offer_item_total"],
        })

    coupon, coupon_discount = get_coupon_for_checkout(
        request,
        offer_subtotal,
    )

    shipping = Decimal("0.00")

    total = max(
        original_subtotal -
        offer_discount -
        coupon_discount +
        shipping,
        Decimal("0.00"),
    )

    addresses = list(
        Address.objects.filter(
            user=request.user
        ).order_by(
            "-is_default",
            "-id",
        )
    )

    selected_address = None

    if addresses:
        selected_address = next(
            (
                address
                for address in addresses
                if address.is_default
            ),
            addresses[0],
        )

    context = {
        "cart_items": cart_items,
        "addresses": addresses,
        "selected_address": selected_address,
        "original_subtotal": original_subtotal,
        "subtotal": original_subtotal,
        "offer_discount": offer_discount,
        "coupon": coupon,
        "coupon_discount": coupon_discount,
        "discount": offer_discount + coupon_discount,
        "shipping": shipping,
        "total": total,
        "buy_now": is_buy_now,
    }

    return render(
        request,
        "checkout/checkout.html",
        context,
    )
@login_required(login_url="login")
def apply_coupon(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."}, status=400)
    coupon_code = request.POST.get("coupon_code", "").strip().upper()
    if not coupon_code:
        return JsonResponse({"success": False, "message": "Please enter a coupon code."}, status=400)
    if request.session.get("checkout_coupon_code"):
        return JsonResponse({"success": False, "message": "A coupon is already applied. Remove it before applying another coupon."}, status=400)
    try:
        items, _ = get_checkout_items(request)
    except ValueError as error:
        return JsonResponse({"success": False, "message": str(error)}, status=400)
    subtotal, offer_subtotal, offer_discount, _ = calculate_checkout_totals(items)
    coupon = Coupon.objects.filter(code__iexact=coupon_code).first()
    if not coupon:
        return JsonResponse({"success": False, "message": "Invalid coupon code."}, status=404)
    valid, error, coupon_discount = validate_coupon(coupon, offer_subtotal, request.user)
    if not valid:
        return JsonResponse({"success": False, "message": error}, status=400)
    request.session["checkout_coupon_code"] = coupon.code
    request.session.modified = True
    shipping = Decimal("0.00")
    total = max(subtotal - offer_discount - coupon_discount + shipping, Decimal("0.00"))
    total_discount = offer_discount + coupon_discount
    return JsonResponse({
        "success": True,
        "message": f"Coupon {coupon.code} applied successfully.",
        "coupon_code": coupon.code,
        "offer_discount": str(offer_discount),
        "coupon_discount": str(coupon_discount),
        "discount": str(total_discount),
        "subtotal": str(subtotal),
        "offer_subtotal": str(offer_subtotal),
        "shipping": str(shipping),
        "total": str(total),
    })


@login_required
def remove_coupon(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."}, status=400)
    request.session.pop("checkout_coupon_code", None)
    request.session.modified = True
    try:
        items, _ = get_checkout_items(request)
    except ValueError:
        return JsonResponse({"success": True, "message": "Coupon removed successfully.", "coupon_code": "", "offer_discount": "0.00", "coupon_discount": "0.00", "discount": "0.00", "subtotal": "0.00", "offer_subtotal": "0.00", "shipping": "0.00", "total": "0.00"})
    subtotal, offer_subtotal, offer_discount, _ = calculate_checkout_totals(items)
    shipping = Decimal("0.00")
    return JsonResponse({
        "success": True,
        "message": "Coupon removed successfully.",
        "coupon_code": "",
        "offer_discount": str(offer_discount),
        "coupon_discount": "0.00",
        "discount": str(offer_discount),
        "subtotal": str(subtotal),
        "offer_subtotal": str(offer_subtotal),
        "shipping": str(shipping),
        "total": str(offer_subtotal + shipping),
    })


@login_required
def available_coupons(request):
    now = timezone.localtime(timezone.now())

    next_url = request.GET.get("next", "").strip()

    if next_url in ("None", "null", ""):
        next_url = None

    if next_url and (
        not next_url.startswith("/")
        or next_url.startswith("//")
    ):
        next_url = None

    used_coupon_ids = CouponUsage.objects.filter(
        user=request.user
    ).values_list(
        "coupon_id",
        flat=True
    )

    coupons = Coupon.objects.filter(
        is_active=True,
        start_date__lte=now,
        expiry_date__gt=now,
    ).exclude(
        id__in=used_coupon_ids
    ).order_by(
        "expiry_date",
        "-created_at"
    )

    for coupon in coupons:
        if (
            coupon.usage_limit is not None
            and coupon.used_count >= coupon.usage_limit
        ):
            coupon.display_status = "EXHAUSTED"
        else:
            coupon.display_status = "ACTIVE"

    return render(
        request,
        "checkout/available_coupons.html",
        {
            "coupons": coupons,
            "next_url": next_url,
        },
    )


@login_required
def create_razorpay_order(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."}, status=400)
    address_id = request.POST.get("address")
    if not address_id:
        return JsonResponse({"success": False, "message": "Please select a delivery address."}, status=400)
    address = Address.objects.filter(id=address_id, user=request.user).first()
    if not address:
        return JsonResponse({"success": False, "message": "Invalid delivery address."}, status=400)
    try:
        items, is_buy_now = get_checkout_items(request)
    except ValueError as error:
        return JsonResponse({"success": False, "message": str(error)}, status=400)
    try:
        subtotal, offer_subtotal, offer_discount, _ = calculate_checkout_totals(items)
        coupon, coupon_discount = get_coupon_for_checkout(request, offer_subtotal)
        total_discount = offer_discount + coupon_discount
        shipping = Decimal("0.00")
        total_amount = max(subtotal - total_discount + shipping, Decimal("0.00"))
        amount_in_paise = int(total_amount * Decimal("100"))
        if amount_in_paise <= 0:
            return JsonResponse({"success": False, "message": "Invalid order amount."}, status=400)
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            return JsonResponse({"success": False, "message": "Razorpay is not configured."}, status=500)
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": f"ORDER-{request.user.id}-{int(timezone.now().timestamp())}",
        })
        checkout_data = {
            "address_id": address.id,
            "amount": str(total_amount),
            "razorpay_order_id": razorpay_order["id"],
            "buy_now": is_buy_now,
        }
        if is_buy_now:
            variant, quantity = items[0]
            checkout_data["buy_now_variant_id"] = variant.id
            checkout_data["buy_now_quantity"] = quantity
        request.session["razorpay_checkout"] = checkout_data
        request.session.modified = True
        return JsonResponse({
            "success": True,
            "key": settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": razorpay_order["id"],
            "amount": amount_in_paise,
            "currency": "INR",
            "name": "STRIDEX",
            "description": "StrideX Order",
        })
    except Exception as error:
        print("RAZORPAY ORDER ERROR:", error)
        return JsonResponse({"success": False, "message": "Unable to start online payment. Please try again."}, status=500)


@login_required
def razorpay_payment_cancelled(request):
    checkout_data = request.session.get("razorpay_checkout", {})
    request.session.pop("razorpay_checkout", None)
    request.session.modified = True
    if checkout_data.get("buy_now"):
        variant_id = checkout_data.get("buy_now_variant_id")
        quantity = checkout_data.get("buy_now_quantity", 1)
        if variant_id:
            messages.warning(request, "Payment was cancelled. You can try again.")
            return redirect(f"/checkout/?buy_now=1&variant_id={variant_id}&quantity={quantity}")
    messages.warning(request, "Payment was cancelled. You can try again.")
    return redirect("checkout:checkout")


@login_required
def razorpay_payment_failed(request):
    checkout_data = request.session.get("razorpay_checkout")
    if not checkout_data:
        messages.error(request, "Payment failed. Please try again.")
        return redirect("checkout:checkout")
    expected_amount = Decimal(checkout_data.get("amount", "0.00"))
    return render(request, "checkout/payment_failed.html", {"amount": expected_amount})

@login_required
@transaction.atomic
def razorpay_payment_success(request):
    if request.method != "POST":
        return redirect("checkout:checkout")

    razorpay_payment_id = request.POST.get("razorpay_payment_id", "").strip()
    razorpay_order_id = request.POST.get("razorpay_order_id", "").strip()
    razorpay_signature = request.POST.get("razorpay_signature", "").strip()
    checkout_data = request.session.get("razorpay_checkout")

    if not checkout_data:
        messages.error(request, "Payment session expired. Please try again.")
        return redirect("checkout:checkout")

    if checkout_data.get("razorpay_order_id") != razorpay_order_id:
        messages.error(request, "Invalid payment order.")
        return redirect("checkout:checkout")

    if not all([
        razorpay_payment_id,
        razorpay_order_id,
        razorpay_signature,
    ]):
        messages.error(request, "Payment verification data is missing.")
        return redirect("checkout:checkout")

    client = razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET,
        )
    )

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })

        payment = client.payment.fetch(razorpay_payment_id)

    except Exception as error:
        print("RAZORPAY PAYMENT VERIFICATION ERROR:", error)
        messages.error(request, "Payment verification failed.")
        return redirect("checkout:checkout")

    if payment.get("status") != "captured":
        messages.error(request, "Payment was not completed.")
        return redirect("checkout:checkout")

    paid_amount = (
        Decimal(str(payment.get("amount", 0)))
        / Decimal("100")
    )

    expected_amount = Decimal(
        checkout_data.get("amount", "0.00")
    )

    if paid_amount != expected_amount:
        messages.error(
            request,
            "Payment amount verification failed."
        )
        return redirect("checkout:checkout")

    address = Address.objects.filter(
        id=checkout_data.get("address_id"),
        user=request.user,
    ).first()

    if not address:
        messages.error(
            request,
            "Delivery address not found."
        )
        return redirect("checkout:checkout")

    try:
        if checkout_data.get("buy_now"):
            variant_id = checkout_data.get(
                "buy_now_variant_id"
            )

            quantity = max(
                int(
                    checkout_data.get(
                        "buy_now_quantity",
                        1
                    )
                ),
                1,
            )

            variant = get_object_or_404(
                Variant.objects.select_related(
                    "product",
                    "product__category",
                ),
                id=variant_id,
                is_active=True,
                is_deleted=False,
                product__is_active=True,
                product__is_deleted=False,
                product__category__is_active=True,
                product__category__is_deleted=False,
            )

            items = [
                (variant, quantity)
            ]

        else:
            cart = Cart.objects.filter(
                user=request.user
            ).first()

            if not cart:
                messages.error(
                    request,
                    "Your cart is empty."
                )
                return redirect("cart:cart")

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
                return redirect("cart:cart")

            items = [
                (item.variant, item.quantity)
                for item in cart_items
            ]

        locked_ids = [
            variant.id
            for variant, _ in items
        ]

        locked_variants = {
            variant.id: variant
            for variant in Variant.objects.select_for_update()
            .filter(id__in=locked_ids)
            .select_related(
                "product",
                "product__category",
            )
        }

        locked_items = []

        for variant, quantity in items:
            variant = locked_variants.get(
                variant.id
            )

            if not variant:
                raise ValueError(
                    "One of the products is no longer available."
                )

            if (
                not variant.is_active
                or variant.is_deleted
                or not variant.product.is_active
                or variant.product.is_deleted
                or not variant.product.category.is_active
                or variant.product.category.is_deleted
            ):
                raise ValueError(
                    f"{variant.product.product_name} "
                    f"is no longer available."
                )

            if variant.stock < quantity:
                raise ValueError(
                    f"Only {variant.stock} quantity of "
                    f"{variant.product.product_name} "
                    f"is available."
                )

            locked_items.append(
                (variant, quantity)
            )

        (
            subtotal,
            offer_subtotal,
            offer_discount,
            calculations,
        ) = calculate_checkout_totals(
            locked_items
        )

        coupon, coupon_discount = get_coupon_for_checkout(
            request,
            offer_subtotal,
        )

        total_discount = (
            offer_discount
            + coupon_discount
        )

        shipping = Decimal("0.00")

        total_amount = max(
            subtotal
            - total_discount
            + shipping,
            Decimal("0.00"),
        )

        if total_amount != expected_amount:
            messages.error(
                request,
                "Order amount changed while payment "
                "was being completed. Please try again."
            )
            return redirect("checkout:checkout")

        order = Order.objects.create(
            user=request.user,
            address_full_name=address.full_name,
            address_phone_number=address.phone_number,
            address_line1=address.address_line1,
            address_line2=address.address_line2,
            address_city=address.city,
            address_state=address.state,
            address_pincode=address.pincode,
            address_country=address.country,
            address_type=address.type,
            payment_method="RAZORPAY",
            payment_status="PAID",
            coupon=coupon,
            subtotal=subtotal,
            discount=total_discount,
            shipping_charge=shipping,
            total_amount=total_amount,
            order_status="PENDING",
        )

        for calculation in calculations:
            variant = calculation["variant"]
            quantity = calculation["quantity"]
            offer_item_total = calculation[
                "offer_item_total"
            ]

            item_coupon_discount = Decimal("0.00")

            if (
                coupon_discount > 0
                and offer_subtotal > 0
            ):
                item_coupon_discount = (
                    coupon_discount
                    * offer_item_total
                    / offer_subtotal
                )

            final_item_total = max(
                Decimal("0.00"),
                offer_item_total
                - item_coupon_discount,
            )

            final_unit_price = (
                final_item_total
                / quantity
            )

            OrderItem.objects.create(
                order=order,
                variant=variant,
                quantity=quantity,
                price=final_unit_price,
                total_price=final_item_total,
                status="PENDING",
            )

            variant.stock -= quantity

            variant.save(
                update_fields=["stock"]
            )

        if coupon:
            CouponUsage.objects.create(
                coupon=coupon,
                user=request.user,
                order=order,
            )

            coupon.used_count += 1

            coupon.save(
                update_fields=["used_count"]
            )

        if not checkout_data.get("buy_now"):
            cart = Cart.objects.filter(
                user=request.user
            ).first()

            if cart:
                cart.items.all().delete()

        clear_checkout_session(
            request,
            clear_buy_now=True,
        )

        request.session["checkout_completed"] = True
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
        messages.error(
            request,
            str(error)
        )
        return redirect("checkout:checkout")

    except Exception as error:
        print(
            "RAZORPAY ORDER CREATION ERROR:",
            error
        )
        messages.error(
            request,
            "Unable to complete the order. "
            "Please try again."
        )
        return redirect("checkout:checkout")