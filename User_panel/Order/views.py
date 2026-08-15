from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import (get_object_or_404, redirect, render)

from User_panel.Authentication.models import Address
from User_panel.Cart.models import Cart
from Admin_panel.product.models import Variant
from django.core.paginator import Paginator
from .models import Order, OrderItem

from io import BytesIO

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
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

    cart_items = []
    subtotal = Decimal("0.00")
    discount = Decimal("0.00")
    shipping = Decimal("0.00")
    total = Decimal("0.00")

    if cart:
        cart_items = list(cart.items.all())

        for item in cart_items:
            item_total = item.variant.price * item.quantity
            item.item_total = item_total
            subtotal += item_total

    total = subtotal - discount + shipping

    context = {
        "cart": cart,
        "cart_items": cart_items,
        "addresses": addresses,
        "default_address": default_address,
        "subtotal": subtotal,
        "discount": discount,
        "shipping": shipping,
        "total": total,
        "payment_method": "COD",
    }

    return render(
        request,
        "user_order/checkout.html",
        context,
    )


@login_required
def place_order(request):
    if request.method != "POST":
        return redirect("order:checkout")

    address_id = request.POST.get("address")

    if not address_id:
        messages.error(
            request,
            "Please select a delivery address."
        )
        return redirect("order:checkout")

    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user,
    )

    cart = (
        Cart.objects.filter(
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
        return redirect("cart")

    cart_items = list(
        cart.items.select_related(
            "variant",
            "variant__product",
        )
    )

    if not cart_items:
        messages.error(
            request,
            "Your cart is empty."
        )
        return redirect("cart")

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
                .select_related("product")
            )

            variants = {
                variant.id: variant
                for variant in locked_variants
            }

            subtotal = Decimal("0.00")

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

                subtotal += (
                    variant.price * item.quantity
                )

            discount = Decimal("0.00")
            shipping = Decimal("0.00")

            total_amount = (
                subtotal
                - discount
                + shipping
            )

            order = Order.objects.create(
                user=request.user,
                address=address,
                payment_method="COD",
                payment_status="PENDING",
                subtotal=subtotal,
                discount=discount,
                shipping_charge=shipping,
                total_amount=total_amount,
                order_status="PENDING",
            )

            for item in cart_items:

                variant = variants[
                    item.variant_id
                ]

                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    quantity=item.quantity,
                    price=variant.price,
                    total_price=(
                        variant.price * item.quantity
                    ),
                    status="PENDING",
                )

                variant.stock -= item.quantity

                variant.save(
                    update_fields=["stock"]
                )

            cart.items.all().delete()

        messages.success(
            request,
            "Your order has been placed successfully."
        )

        return redirect(
            "order:order_success",
            order_id=order.order_id,
        )

    except ValueError as error:
        print("PLACE ORDER VALIDATION ERROR:", error)
        messages.error(
            request,
            str(error)
        )
        return redirect("order:checkout")

    except Exception as error:
        print("PLACE ORDER ERROR:", error)
        messages.error(
            request,
            str(error)
        )
        return redirect("order:checkout")


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
    search = request.GET.get("search", "").strip()

    orders = (
        Order.objects.filter(
            user=request.user
        )
        .prefetch_related(
            "items__variant__product",
        )
        .order_by("-created_at")
    )

    if search:
        orders = orders.filter(
            order_id__icontains=search
        )

    paginator = Paginator(
        orders,
        5
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
        },
    )


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items__variant__product",
            "items__variant__images",
        ),
        order_id=order_id,
        user=request.user,
    )

    return render(
        request,
        "user_order/order_detail.html",
        {
            "order": order,
            "order_items": order.items.all(),
        },
    )
@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items__variant__product",
        ),
        order_id=order_id,
        user=request.user,
    )

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    normal_style = styles["Normal"]

    elements = []

    elements.append(
        Paragraph(
            "StrideX",
            title_style,
        )
    )

    elements.append(
        Paragraph(
            "Order Invoice",
            heading_style,
        )
    )

    elements.append(
        Spacer(
            1,
            10,
        )
    )

    order_info = [
        [
            Paragraph("<b>Order ID</b>", normal_style),
            order.order_id,
        ],
        [
            Paragraph("<b>Order Date</b>", normal_style),
            order.created_at.strftime(
                "%d %b %Y, %I:%M %p"
            ),
        ],
        [
            Paragraph("<b>Payment Method</b>", normal_style),
            order.get_payment_method_display(),
        ],
        [
            Paragraph("<b>Payment Status</b>", normal_style),
            order.get_payment_status_display(),
        ],
        [
            Paragraph("<b>Order Status</b>", normal_style),
            order.get_order_status_display(),
        ],
    ]

    order_table = Table(
        order_info,
        colWidths=[
            45 * mm,
            115 * mm,
        ],
    )

    order_table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.lightgrey,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    elements.append(order_table)

    elements.append(
        Spacer(
            1,
            18,
        )
    )

    elements.append(
        Paragraph(
            "Delivery Address",
            heading_style,
        )
    )

    address = order.address

    address_lines = [
        address.full_name,
        address.phone_number,
        address.address_line1,
    ]

    if address.address_line2:
        address_lines.append(
            address.address_line2
        )

    address_lines.extend(
        [
            f"{address.city}, {address.state} - {address.pincode}",
            address.country,
        ]
    )

    for line in address_lines:
        elements.append(
            Paragraph(
                str(line),
                normal_style,
            )
        )

    elements.append(
        Spacer(
            1,
            18,
        )
    )

    elements.append(
        Paragraph(
            "Ordered Products",
            heading_style,
        )
    )

    product_data = [
        [
            "Product",
            "Qty",
            "Price",
            "Total",
        ]
    ]

    for item in order.items.all():

        product_name = (
            item.variant.product.product_name
        )

        product_data.append(
            [
                product_name,
                str(item.quantity),
                f"₹{item.price:.2f}",
                f"₹{item.total_price:.2f}",
            ]
        )

    product_table = Table(
        product_data,
        colWidths=[
            85 * mm,
            20 * mm,
            30 * mm,
            35 * mm,
        ],
        repeatRows=1,
    )

    product_table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.lightgrey,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "RIGHT",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    elements.append(product_table)

    elements.append(
        Spacer(
            1,
            18,
        )
    )

    summary_data = [
        [
            "Subtotal",
            f"₹{order.subtotal:.2f}",
        ],
        [
            "Discount",
            f"- ₹{order.discount:.2f}",
        ],
        [
            "Shipping",
            f"₹{order.shipping_charge:.2f}",
        ],
        [
            "Total",
            f"₹{order.total_amount:.2f}",
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[
            130 * mm,
            40 * mm,
        ],
        hAlign="RIGHT",
    )

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "LINEABOVE",
                    (0, -1),
                    (-1, -1),
                    1,
                    colors.black,
                ),
                (
                    "FONTNAME",
                    (0, -1),
                    (-1, -1),
                    "Helvetica-Bold",
                ),
                (
                    "ALIGN",
                    (1, 0),
                    (1, -1),
                    "RIGHT",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    elements.append(summary_table)

    elements.append(
        Spacer(
            1,
            25,
        )
    )

    elements.append(
        Paragraph(
            "Thank you for shopping with StrideX.",
            normal_style,
        )
    )

    document.build(elements)

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/pdf",
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; filename="Invoice-{order.order_id}.pdf"'
    )

    return response
@login_required
@transaction.atomic
def cancel_order(request, order_id):
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

    if order.order_status == "CANCELLED":
        messages.error(
            request,
            "This order is already cancelled.",
        )
        return redirect(
            "order:order_detail",
            order_id=order.order_id,
        )

    if order.order_status not in [
        "PENDING",
        "PROCESSING",
    ]:
        messages.error(
            request,
            "This order cannot be cancelled now.",
        )
        return redirect(
            "order:order_detail",
            order_id=order.order_id,
        )

    reason = request.POST.get(
        "cancel_reason",
        "",
    ).strip()

    order_items = order.items.select_for_update().filter(
        status__in=[
            "PENDING",
            "PROCESSING",
        ]
    )

    for item in order_items:
        variant = Variant.objects.select_for_update().get(
            id=item.variant_id,
        )

        variant.stock += item.quantity

        variant.save(
            update_fields=[
                "stock",
            ]
        )

        item.status = "CANCELLED"
        item.cancel_reason = reason

        item.save(
            update_fields=[
                "status",
                "cancel_reason",
            ]
        )

    order.order_status = "CANCELLED"

    order.save(
        update_fields=[
            "order_status",
            "updated_at",
        ]
    )

    messages.success(
        request,
        "Order cancelled successfully.",
    )

    return redirect(
        "order:order_detail",
        order_id=order.order_id,
    )

@login_required
@transaction.atomic
def cancel_order_item(request, order_id, item_id):
    if request.method != "POST":
        return redirect(
            "order:order_detail",
            order_id=order_id,
        )

    order = get_object_or_404(
        Order,
        order_id=order_id,
        user=request.user,
    )

    order_item = get_object_or_404(
        OrderItem.objects.select_for_update(),
        id=item_id,
        order=order,
    )

    if order_item.status == "CANCELLED":
        messages.error(
            request,
            "This product is already cancelled.",
        )

        return redirect(
            "order:order_detail",
            order_id=order.order_id,
        )

    if order_item.status not in [
        "PENDING",
        "PROCESSING",
    ]:
        messages.error(
            request,
            "This product cannot be cancelled now.",
        )

        return redirect(
            "order:order_detail",
            order_id=order.order_id,
        )

    reason = request.POST.get(
        "cancel_reason",
        "",
    ).strip()

    variant = Variant.objects.select_for_update().get(
        id=order_item.variant_id,
    )

    variant.stock += order_item.quantity

    variant.save(
        update_fields=[
            "stock",
        ]
    )

    order_item.status = "CANCELLED"
    order_item.cancel_reason = reason

    order_item.save(
        update_fields=[
            "status",
            "cancel_reason",
        ]
    )

    remaining_items = order.items.exclude(
        status="CANCELLED"
    )

    if remaining_items.exists():

        order.subtotal = sum(
            item.total_price
            for item in remaining_items
        )

        order.total_amount = (
            order.subtotal
            - order.discount
            + order.shipping_charge
        )

    else:

        order.order_status = "CANCELLED"

    order.save(
        update_fields=[
            "subtotal",
            "total_amount",
            "order_status",
            "updated_at",
        ]
    )

    messages.success(
        request,
        "Product cancelled successfully.",
    )

    return redirect(
        "order:order_detail",
        order_id=order.order_id,
    )

@login_required(login_url="admin_login")
def return_order_item(request, item_id):
    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order__user=request.user,
    )

    if request.method != "POST":
        return redirect(
            "order:order_detail",
            order_id=item.order.order_id,
        )

    if item.status != "DELIVERED":
        messages.error(
            request,
            "Only delivered products can be returned.",
        )
        return redirect(
            "order:order_detail",
            order_id=item.order.order_id,
        )

    return_reason = request.POST.get(
        "return_reason",
        ""
    ).strip()

    if not return_reason:
        messages.error(
            request,
            "Return reason is required.",
        )
        return redirect(
            "order:order_detail",
            order_id=item.order.order_id,
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
        order_id=item.order.order_id,
    )