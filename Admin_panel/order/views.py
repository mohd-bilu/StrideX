from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from User_panel.Order.models import Order, OrderItem


@never_cache
@login_required(login_url="admin_login")
@staff_member_required
def order_list(request):
    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()
    sort = request.GET.get("sort", "newest").strip()

    orders = (
        Order.objects
        .select_related("user", "address")
        .prefetch_related(
            "items__variant__product",
            "items__variant__images",
        )
    )

    if search:
        orders = orders.filter(
            Q(order_id__icontains=search)
            | Q(user__full_name__icontains=search)
            | Q(user__email__icontains=search)
            | Q(
                items__variant__product__product_name__icontains=search
            )
        ).distinct()

    if status:
        orders = orders.filter(
            order_status=status
        )

    if sort == "oldest":
        orders = orders.order_by("created_at")
    elif sort == "highest":
        orders = orders.order_by("-total_amount")
    elif sort == "lowest":
        orders = orders.order_by("total_amount")
    else:
        orders = orders.order_by("-created_at")

    pending_orders = Order.objects.filter(
        order_status__in=[
            "PENDING",
            "PROCESSING",
            "SHIPPED",
            "OUT_FOR_DELIVERY",
        ]
    ).count()

    total_revenue = (
        Order.objects
        .exclude(order_status="CANCELLED")
        .aggregate(
            total=Sum("total_amount")
        )
        .get("total")
        or 0
    )

    cancelled_returned = Order.objects.filter(
        order_status__in=[
            "CANCELLED",
            "RETURN_REQUESTED",
            "RETURNED",
        ]
    ).count()

    paginator = Paginator(
        orders,
        10,
    )

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    status_choices = Order.STATUS_CHOICES

    return render(
        request,
        "order/order_list.html",
        {
            "orders": page_obj,
            "page_obj": page_obj,
            "search": search,
            "status": status,
            "sort": sort,
            "status_choices": status_choices,
            "pending_orders": pending_orders,
            "total_revenue": total_revenue,
            "cancelled_returned": cancelled_returned,
        },
    )


@never_cache
@login_required(login_url="admin_login")
@staff_member_required
def return_list(request):
    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()

    return_items = (
        OrderItem.objects
        .select_related(
            "order",
            "order__user",
            "order__address",
            "variant",
            "variant__product",
        )
        .prefetch_related(
            "variant__images",
        )
        .filter(
            status__in=[
                "RETURN_REQUESTED",
                "RETURNED",
                "REJECTED",
            ]
        )
        .order_by("-created_at")
    )

    if search:
        return_items = return_items.filter(
            Q(order__order_id__icontains=search)
            | Q(order__user__full_name__icontains=search)
            | Q(order__user__email__icontains=search)
            | Q(
                variant__product__product_name__icontains=search
            )
        ).distinct()

    if status:
        status_aliases = {
            "pending": "RETURN_REQUESTED",
            "approved": "RETURNED",
            "rejected": "REJECTED",
            "RETURN_REQUESTED": "RETURN_REQUESTED",
            "RETURNED": "RETURNED",
            "REJECTED": "REJECTED",
        }

        selected_status = status_aliases.get(status)

        if selected_status:
            return_items = return_items.filter(
                status=selected_status
            )

    total_returns = OrderItem.objects.filter(
        status__in=[
            "RETURN_REQUESTED",
            "RETURNED",
            "REJECTED",
        ]
    ).count()

    pending_returns = OrderItem.objects.filter(
        status="RETURN_REQUESTED"
    ).count()

    approved_returns = OrderItem.objects.filter(
        status="RETURNED"
    ).count()

    rejected_returns = OrderItem.objects.filter(
        status="REJECTED"
    ).count()

    paginator = Paginator(
        return_items,
        10,
    )

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "order/return_list.html",
        {
            "return_items": page_obj,
            "page_obj": page_obj,
            "search": search,
            "status": status,
            "total_returns": total_returns,
            "pending_returns": pending_returns,
            "approved_returns": approved_returns,
            "rejected_returns": rejected_returns,
        },
    )

@never_cache
@login_required(login_url="admin_login")
@staff_member_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects
        .select_related(
            "user",
            "address",
        )
        .prefetch_related(
            "items__variant__product",
            "items__variant__images",
        ),
        order_id=order_id,
    )

    order_items = order.items.all()

    has_returned_items = order_items.filter(
        status="RETURNED"
    ).exists()

    has_return_requested_items = order_items.filter(
        status="RETURN_REQUESTED"
    ).exists()

    return render(
        request,
        "order/order_detail.html",
        {
            "order": order,
            "order_items": order_items,
            "has_returned_items": has_returned_items,
            "has_return_requested_items": has_return_requested_items,
        },
    )


@never_cache
@login_required(login_url="admin_login")
@staff_member_required
@transaction.atomic
def update_order_status(request, order_id):
    if request.method != "POST":
        return redirect(
            "admin_order:order_detail",
            order_id=order_id,
        )

    order = get_object_or_404(
        Order,
        order_id=order_id,
    )

    new_status = request.POST.get(
        "order_status",
        "",
    ).strip()

    valid_statuses = dict(
        Order.STATUS_CHOICES
    )

    if new_status not in valid_statuses:
        messages.error(
            request,
            "Invalid order status.",
        )

        return redirect(
            "admin_order:order_detail",
            order_id=order.order_id,
        )

    current_status = order.order_status

    allowed_transitions = {
        "PENDING": [
            "SHIPPED",
            "CANCELLED",
        ],
        "PROCESSING": [
            "SHIPPED",
            "CANCELLED",
        ],
        "SHIPPED": [
            "OUT_FOR_DELIVERY",
        ],
        "OUT_FOR_DELIVERY": [
            "DELIVERED",
        ],
        "DELIVERED": [],
        "CANCELLED": [],
        "RETURN_REQUESTED": [],
        "RETURNED": [],
    }

    if new_status == current_status:
        messages.info(
            request,
            "Order is already in this status.",
        )

        return redirect(
            "admin_order:order_detail",
            order_id=order.order_id,
        )

    if new_status not in allowed_transitions.get(
        current_status,
        [],
    ):
        messages.error(
            request,
            f"Cannot change order from "
            f"{valid_statuses.get(current_status, current_status)} "
            f"to "
            f"{valid_statuses.get(new_status, new_status)}.",
        )

        return redirect(
            "admin_order:order_detail",
            order_id=order.order_id,
        )

    order.order_status = new_status

    if new_status == "DELIVERED":
        order.payment_status = "PAID"

    order.save()

    if new_status == "CANCELLED":
        cancellable_items = order.items.filter(
            status__in=[
                "PENDING",
                "PROCESSING",
            ]
        ).select_related("variant")

        for item in cancellable_items:
            item.variant.stock += item.quantity
            item.variant.save(
                update_fields=[
                    "stock",
                ]
            )

            item.status = "CANCELLED"
            item.save(
                update_fields=[
                    "status",
                ]
            )

    else:
        order.items.filter(
            status__in=[
                "PENDING",
                "PROCESSING",
                "SHIPPED",
                "OUT_FOR_DELIVERY",
            ]
        ).update(
            status=new_status
        )

    messages.success(
        request,
        f"Order {order.order_id} updated to "
        f"{valid_statuses[new_status]}.",
    )

    return redirect(
        "admin_order:order_detail",
        order_id=order.order_id,
    )


@never_cache
@login_required(login_url="admin_login")
@staff_member_required
@transaction.atomic
def update_return_status(request, item_id):
    if request.method != "POST":
        return redirect(
            "admin_order:return_list"
        )

    item = get_object_or_404(
        OrderItem.objects.select_related(
            "order",
            "variant",
            "variant__product",
        ),
        id=item_id,
    )

    new_status = request.POST.get(
        "return_status",
        "",
    ).strip()

    rejection_reason = request.POST.get(
        "rejection_reason",
        "",
    ).strip()

    if new_status not in [
        "RETURNED",
        "REJECTED",
    ]:
        messages.error(
            request,
            "Invalid return status.",
        )

        return redirect(
            "admin_order:return_list"
        )

    if item.status != "RETURN_REQUESTED":
        messages.error(
            request,
            "This item does not have a pending return request.",
        )

        return redirect(
            "admin_order:return_list"
        )

    if new_status == "REJECTED" and not rejection_reason:
        messages.error(
            request,
            "Rejection reason is required.",
        )

        return redirect(
            "admin_order:return_list"
        )

    if new_status == "RETURNED":
        item.status = "RETURNED"
        item.rejection_reason = None

        item.save(
            update_fields=[
                "status",
                "rejection_reason",
            ]
        )

        item.variant.stock += item.quantity

        item.variant.save(
            update_fields=[
                "stock",
            ]
        )

        messages.success(
            request,
            f"Return approved for "
            f"{item.variant.product.product_name}.",
        )

    elif new_status == "REJECTED":
        item.status = "REJECTED"
        item.rejection_reason = rejection_reason

        item.save(
            update_fields=[
                "status",
                "rejection_reason",
            ]
        )

        messages.success(
            request,
            f"Return rejected for "
            f"{item.variant.product.product_name}.",
        )

    return redirect(
        "admin_order:return_list"
    )