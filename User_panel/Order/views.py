import io
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.utils import timezone
from django.views.decorators.cache import never_cache
from xhtml2pdf import pisa
from types import SimpleNamespace
from Admin_panel.coupon_offer.models import Coupon, CouponUsage, Offer
from Admin_panel.product.models import Variant
from User_panel.Authentication.models import Address, User
from User_panel.Cart.models import Cart
from .models import Order, OrderItem

REFERRAL_REWARD = Decimal("200.00")


def reward_referrer_for_order(order):
    user = order.user

    if not user.referred_by_id:
        return Decimal("0.00")

    if user.referral_reward_given:
        return Decimal("0.00")

    if order.order_status != "DELIVERED":
        return Decimal("0.00")

    if order.payment_method == "COD":
        order.payment_status = "PAID"
        order.save(update_fields=["payment_status"])

    if order.payment_status != "PAID":
        return Decimal("0.00")

    if Order.objects.filter(
        user=user,
        order_status="DELIVERED"
    ).exclude(
        id=order.id
    ).exists():
        return Decimal("0.00")

    from User_panel.Wallet.models import Wallet, WalletTransaction

    referrer = User.objects.select_for_update().get(
        id=user.referred_by_id
    )

    wallet, created = Wallet.objects.select_for_update().get_or_create(
        user=referrer,
        defaults={"balance": Decimal("0.00")}
    )

    reference = f"REFERRAL-{order.order_id}"

    existing_reward = WalletTransaction.objects.filter(
        wallet=wallet,
        reference=reference,
        transaction_type="CREDIT"
    ).exists()

    if existing_reward:
        user.referral_reward_given = True
        user.save(update_fields=["referral_reward_given"])
        return Decimal("0.00")

    wallet.balance += REFERRAL_REWARD
    wallet.save(
        update_fields=["balance", "updated_at"]
    )

    WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="CREDIT",
        amount=REFERRAL_REWARD,
        description=f"Referral reward for order {order.order_id}",
        reference=reference
    )

    user.referral_reward_given = True
    user.save(
        update_fields=["referral_reward_given"]
    )

    return REFERRAL_REWARD
def get_best_offer(variant, now=None):
    if now is None:
        now = timezone.now()

    offers = Offer.objects.filter(
        is_active=True,
        start_date__lte=now,
        expiry_date__gte=now,
    ).filter(
        Q(
            offer_type="PRODUCT",
            product_id=variant.product_id,
        )
        | Q(
            offer_type="CATEGORY",
            category_id=variant.product.category_id,
        )
    )

    best_offer = None
    best_discount = Decimal("0.00")

    for offer in offers:
        if offer.discount_type == "PERCENTAGE":
            discount = (
                variant.price
                * offer.discount_value
            ) / Decimal("100")
        else:
            discount = min(
                offer.discount_value,
                variant.price,
            )

        discount = max(
            Decimal("0.00"),
            min(
                discount,
                variant.price,
            ),
        )

        if discount > best_discount:
            best_offer = offer
            best_discount = discount

    return best_offer, best_discount

def calculate_coupon_discount(coupon, amount):
    if not coupon or amount <= 0:
        return Decimal("0.00")

    if coupon.discount_type == "PERCENTAGE":
        discount = (
            amount * coupon.discount_value
        ) / Decimal("100")

        if coupon.maximum_discount is not None:
            discount = min(
                discount,
                coupon.maximum_discount,
            )
    else:
        discount = min(
            coupon.discount_value,
            amount,
        )

    return max(
        Decimal("0.00"),
        min(discount, amount),
    )


def get_valid_coupon(request, subtotal):
    coupon_code = request.session.get(
        "checkout_coupon_code"
    )

    if not coupon_code:
        return None, Decimal("0.00"), None

    now = timezone.now()

    coupon = (
        Coupon.objects
        .filter(
            code__iexact=coupon_code.strip(),
            is_active=True,
            start_date__lte=now,
            expiry_date__gte=now,
        )
        .first()
    )

    if not coupon:
        return None, Decimal("0.00"), "The applied coupon is no longer valid."

    if (
        coupon.usage_limit is not None
        and coupon.used_count >= coupon.usage_limit
    ):
        return None, Decimal("0.00"), "This coupon usage limit has been reached."

    already_used = CouponUsage.objects.filter(
        coupon=coupon,
        user=request.user,
    ).exists()

    if already_used:
        return None, Decimal("0.00"), "You have already used this coupon."

    if subtotal < coupon.minimum_purchase:
        return (
            None,
            Decimal("0.00"),
            f"Minimum purchase of ₹{coupon.minimum_purchase:.2f} is required.",
        )

    discount = calculate_coupon_discount(
        coupon,
        subtotal,
    )

    return coupon, discount, None


def calculate_order_totals(request, cart_items, variants):
    original_subtotal = Decimal("0.00")
    offer_discount_total = Decimal("0.00")
    item_calculations = []

    now = timezone.now()

    for cart_item in cart_items:
        variant = variants.get(cart_item.variant_id)

        if not variant:
            raise ValueError(
                "One of the products in your cart is no longer available."
            )

        if (
            not variant.is_active
            or variant.is_deleted
            or not variant.product.is_active
            or variant.product.is_deleted
        ):
            raise ValueError(
                f"{variant.product.product_name} is no longer available."
            )

        if variant.stock <= 0:
            raise ValueError(
                f"{variant.product.product_name} is out of stock."
            )

        if cart_item.quantity > variant.stock:
            raise ValueError(
                f"Only {variant.stock} quantity of "
                f"{variant.product.product_name} is available."
            )

        original_item_total = (
            variant.price * cart_item.quantity
        )

        offer, unit_offer_discount = get_best_offer(
            variant,
            now,
        )

        offer_unit_price = max(
            Decimal("0.00"),
            variant.price - unit_offer_discount,
        )

        offer_item_total = (
            offer_unit_price * cart_item.quantity
        )

        item_offer_discount = (
            original_item_total - offer_item_total
        )

        original_subtotal += original_item_total
        offer_discount_total += item_offer_discount

        item_calculations.append(
            {
                "item": cart_item,
                "variant": variant,
                "offer": offer,
                "original_item_total": original_item_total,
                "offer_item_total": offer_item_total,
                "item_offer_discount": item_offer_discount,
                "unit_price_after_offer": offer_unit_price,
            }
        )

    offer_adjusted_subtotal = (
        original_subtotal - offer_discount_total
    )

    coupon, coupon_discount, coupon_error = get_valid_coupon(
        request,
        offer_adjusted_subtotal,
    )

    if coupon_error:
        raise ValueError(coupon_error)

    total_discount = (
        offer_discount_total + coupon_discount
    )

    shipping = Decimal("0.00")

    total_amount = (
        original_subtotal
        - total_discount
        + shipping
    )

    if total_amount < 0:
        total_amount = Decimal("0.00")

    return {
        "original_subtotal": original_subtotal,
        "offer_adjusted_subtotal": offer_adjusted_subtotal,
        "offer_discount": offer_discount_total,
        "coupon_discount": coupon_discount,
        "total_discount": total_discount,
        "shipping": shipping,
        "total_amount": total_amount,
        "coupon": coupon,
        "item_calculations": item_calculations,
    }
@login_required(login_url="login")
def place_order(request):
    if request.method != "POST":
        return redirect("checkout:checkout")

    address_id = request.POST.get("address")
    payment_method = request.POST.get(
        "payment_method",
        "COD",
    ).strip().upper()

    if payment_method not in ["COD", "WALLET"]:
        messages.error(request, "Invalid payment method.")
        return redirect("checkout:checkout")

    if not address_id:
        messages.error(
            request,
            "Please select a delivery address.",
        )
        return redirect("checkout:checkout")

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user,
    )

    buy_now = bool(
        request.session.get("buy_now")
    )

    buy_now_variant_id = request.session.get(
        "buy_now_variant_id"
    )

    buy_now_quantity = request.session.get(
        "buy_now_quantity",
        1,
    )

    if buy_now:
        if not buy_now_variant_id:
            messages.error(
                request,
                "The Buy Now product could not be found.",
            )
            return redirect("product:product_list")

        try:
            buy_now_quantity = int(
                buy_now_quantity
            )
        except (TypeError, ValueError):
            buy_now_quantity = 1

        buy_now_quantity = max(
            buy_now_quantity,
            1,
        )

        variant = (
            Variant.objects
            .select_related(
                "product",
                "product__category",
            )
            .filter(
                id=buy_now_variant_id,
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
            messages.error(
                request,
                "The selected product is no longer available.",
            )
            return redirect("product:product_list")

        if variant.stock < buy_now_quantity:
            messages.error(
                request,
                f"Only {variant.stock} quantity of "
                f"{variant.product.product_name} is available.",
            )
            return redirect(
                "product:product_detail",
                product_id=variant.product.id,
            )

        cart_items = [
            SimpleNamespace(
                variant=variant,
                variant_id=variant.id,
                quantity=buy_now_quantity,
            )
        ]

        is_buy_now = True

    else:
        cart = Cart.objects.filter(
            user=request.user
        ).first()

        if not cart:
            messages.error(
                request,
                "Your cart is empty.",
            )
            return redirect("product:product_list")

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
                "Your cart is empty.",
            )
            return redirect("product:product_list")

        is_buy_now = False

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

            for item in cart_items:
                variant = variants.get(
                    item.variant_id
                )

                if not variant:
                    raise ValueError(
                        "One of the selected products "
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

                if variant.stock < item.quantity:
                    raise ValueError(
                        f"Only {variant.stock} quantity of "
                        f"{variant.product.product_name} "
                        "is available."
                    )

            totals = calculate_order_totals(
                request,
                cart_items,
                variants,
            )

            subtotal = totals[
                "original_subtotal"
            ]

            total_discount = totals[
                "total_discount"
            ]

            shipping = totals[
                "shipping"
            ]

            total_amount = totals[
                "total_amount"
            ]

            coupon = totals["coupon"]

            item_calculations = totals[
                "item_calculations"
            ]

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
                address_full_name=address.full_name,
                address_phone_number=address.phone_number,
                address_line1=address.address_line1,
                address_line2=address.address_line2,
                address_city=address.city,
                address_state=address.state,
                address_pincode=address.pincode,
                address_country=address.country,
                address_type=address.type,
                payment_method=payment_method,
                payment_status=(
                    "PAID"
                    if payment_method == "WALLET"
                    else "PENDING"
                ),
                coupon=coupon,
                subtotal=subtotal,
                discount=total_discount,
                shipping_charge=shipping,
                total_amount=total_amount,
                order_status="PENDING",
            )

            coupon_discount = totals[
                "coupon_discount"
            ]

            offer_adjusted_subtotal = totals[
                "offer_adjusted_subtotal"
            ]

            for calculation in item_calculations:
                item = calculation["item"]
                variant = calculation["variant"]
                offer_item_total = calculation[
                    "offer_item_total"
                ]

                item_coupon_discount = Decimal(
                    "0.00"
                )

                if (
                    coupon_discount > 0
                    and offer_adjusted_subtotal > 0
                ):
                    item_coupon_discount = (
                        coupon_discount
                        * offer_item_total
                        / offer_adjusted_subtotal
                    )

                final_item_total = max(
                    Decimal("0.00"),
                    offer_item_total
                    - item_coupon_discount,
                )

                final_unit_price = (
                    final_item_total
                    / item.quantity
                )

                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    quantity=item.quantity,
                    price=final_unit_price,
                    total_price=final_item_total,
                    status="PENDING",
                )

                variant.stock -= item.quantity

                variant.save(
                    update_fields=["stock"]
                )

            if coupon:
                coupon.used_count += 1

                coupon.save(
                    update_fields=["used_count"]
                )

                CouponUsage.objects.create(
                    coupon=coupon,
                    user=request.user,
                    order=order,
                )

            if payment_method == "WALLET":
                from User_panel.Wallet.models import (
                    WalletTransaction,
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

            if not is_buy_now:
                cart.items.all().delete()

            request.session.pop(
                "checkout_coupon_code",
                None,
            )

            request.session.pop(
                "buy_now",
                None,
            )

            request.session.pop(
                "buy_now_variant_id",
                None,
            )

            request.session.pop(
                "buy_now_quantity",
                None,
            )

            request.session.modified = True

        request.session["checkout_completed"] = True
        request.session.modified = True

        messages.success(
            request,
            "Your order has been placed successfully.",
        )

        return redirect(
            "order:order_success",
            order_id=order.order_id,
        )

    except ValueError as error:
        messages.error(
            request,
            str(error),
        )
        return redirect("checkout:checkout")

    except Exception as error:
        print(
            "PLACE ORDER ERROR:",
            repr(error),
        )

        messages.error(
            request,
            "Unable to place the order. Please try again.",
        )

        return redirect("checkout:checkout")

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
        "",
    ).strip()

    status = request.GET.get(
        "status",
        "",
    ).strip()

    orders = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related(
            "items__variant__product",
        )
        .order_by("-created_at")
    )

    if search:
        orders = orders.filter(
            order_id__icontains=search,
        )

    if status:
        orders = orders.filter(
            order_status=status,
        )

    paginator = Paginator(
        orders,
        5,
    )

    page_number = request.GET.get("page")
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
        status="DELIVERED",
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
        Order.objects.prefetch_related(
            "items__variant__product__category"
        ),
        order_id=order_id,
        user=request.user,
        order_status__in=["DELIVERED", "RETURNED"],
    )

    template = get_template("user_order/invoice_pdf.html")

    html = template.render({
        "order": order,
    })

    response = HttpResponse(
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="StrideX-Invoice-{order.order_id}.pdf"'
    )

    pdf = pisa.CreatePDF(
        io.BytesIO(html.encode("UTF-8")),
        dest=response,
        encoding="UTF-8",
    )

    if pdf.err:
        return HttpResponse(
            "Unable to generate invoice.",
            status=500,
        )

    return response
@login_required(login_url="login")
def refund_order_item_to_wallet(
    request,
    order,
    item,
    refund_reference,
):
    if order.payment_status != "PAID":
        return Decimal("0.00")

    refund_amount = max(
        Decimal("0.00"),
        item.total_price,
    )

    if refund_amount <= 0:
        return Decimal("0.00")

    from User_panel.Wallet.models import (
        Wallet,
        WalletTransaction,
    )

    wallet, created = (
        Wallet.objects
        .select_for_update()
        .get_or_create(
            user=request.user,
            defaults={
                "balance": Decimal("0.00"),
            },
        )
    )

    existing_refund = (
        WalletTransaction.objects
        .filter(
            wallet=wallet,
            reference=refund_reference,
            transaction_type="CREDIT",
        )
        .exists()
    )

    if existing_refund:
        return Decimal("0.00")

    wallet.balance += refund_amount

    wallet.save(
        update_fields=[
            "balance",
            "updated_at",
        ]
    )

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

    return refund_amount


@never_cache
@login_required(login_url="login")
@transaction.atomic
def cancel_order(request, order_id):
    if request.method != "POST":
        return redirect(
            "order:order_detail",
            order_id=order_id,
        )

    order = get_object_or_404(
        Order.objects
        .select_for_update()
        .prefetch_related(
            "items__variant"
        ),
        order_id=order_id,
        user=request.user,
    )

    if order.order_status not in [
        "PENDING",
        "PROCESSING",
    ]:
        messages.error(
            request,
            "This order cannot be cancelled.",
        )
        return redirect(
            "order:order_detail",
            order_id=order.order_id,
        )

    cancel_reason = request.POST.get(
        "cancel_reason",
        "",
    ).strip()

    

    items_to_cancel = list(
        order.items.filter(
            status__in=[
                "PENDING",
                "PROCESSING",
            ]
        )
    )

    if not items_to_cancel:
        messages.error(
            request,
            "There are no cancellable products in this order.",
        )
        return redirect(
            "order:order_detail",
            order_id=order.order_id,
        )

    refund_amount = Decimal("0.00")

    for item in items_to_cancel:
        variant = (
            Variant.objects
            .select_for_update()
            .get(id=item.variant_id)
        )

        item.status = "CANCELLED"
        item.cancel_reason = cancel_reason

        item.save(
            update_fields=[
                "status",
                "cancel_reason",
            ]
        )

        variant.stock += item.quantity

        variant.save(
            update_fields=["stock"]
        )

        if order.payment_status == "PAID":
            refund_reference = (
                f"REFUND-{order.order_id}-ITEM-{item.id}"
            )

            refund_amount += (
                refund_order_item_to_wallet(
                    request,
                    order,
                    item,
                    refund_reference,
                )
            )

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
            f"Order cancelled successfully. "
            f"₹{refund_amount:.2f} has been refunded to your wallet.",
        )
    else:
        messages.success(
            request,
            "Order cancelled successfully.",
        )

    return redirect(
        "order:order_detail",
        order_id=order.order_id,
    )


@never_cache
@login_required(login_url="login")
@transaction.atomic
def cancel_order_item(request, order_id, item_id):
    if request.method != "POST":
        return redirect(
            "order:order_detail",
            order_id=order_id,
        )

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

    if item.status not in [
        "PENDING",
        "PROCESSING",
    ]:
        messages.error(
            request,
            "This product cannot be cancelled at this stage.",
        )
        return redirect(
            "order:order_detail",
            order_id=order.order_id,
        )

    cancel_reason = request.POST.get(
        "cancel_reason",
        "",
    ).strip()

    

    variant = (
        Variant.objects
        .select_for_update()
        .get(id=item.variant_id)
    )

    item.status = "CANCELLED"
    item.cancel_reason = cancel_reason

    item.save(
        update_fields=[
            "status",
            "cancel_reason",
        ]
    )

    variant.stock += item.quantity

    variant.save(
        update_fields=["stock"]
    )

    refund_amount = Decimal("0.00")

    if order.payment_status == "PAID":
        refund_reference = (
            f"REFUND-{order.order_id}-ITEM-{item.id}"
        )

        refund_amount = (
            refund_order_item_to_wallet(
                request,
                order,
                item,
                refund_reference,
            )
        )

    remaining_items = order.items.exclude(
        status="CANCELLED",
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
            f"{item.variant.product.product_name} "
            f"cancelled successfully. "
            f"₹{refund_amount:.2f} has been refunded to your wallet.",
        )
    else:
        messages.success(
            request,
            f"{item.variant.product.product_name} "
            "has been cancelled successfully.",
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

    item_id = request.POST.get("item_id")

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