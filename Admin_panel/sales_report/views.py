from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from User_panel.Order.models import Order, OrderItem


def get_report_dates(request):
    today = timezone.localdate()

    from_date = request.GET.get("from_date", "").strip()
    to_date = request.GET.get("to_date", "").strip()

    if not from_date:
        from_date = today.replace(day=1).isoformat()

    if not to_date:
        to_date = today.isoformat()

    try:
        start_date = datetime.strptime(from_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(to_date, "%Y-%m-%d").date()
    except ValueError:
        return None

    if start_date > end_date:
        return None

    return start_date, end_date


def get_report_queryset(start_date, end_date):
    start_datetime = timezone.make_aware(
        datetime.combine(start_date, datetime.min.time())
    )

    end_datetime = timezone.make_aware(
        datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    )

    return (
        Order.objects
        .filter(
            created_at__gte=start_datetime,
            created_at__lt=end_datetime,
        )
        .select_related("user", "coupon")
        .prefetch_related("items__variant__product")
        .order_by("-created_at")
    )


def get_report_data(start_date, end_date):
    orders = get_report_queryset(start_date, end_date)

    total_orders = orders.count()

    total_revenue = (
        orders.aggregate(
            total=Sum("total_amount")
        ).get("total")
        or Decimal("0.00")
    )

    total_discounts = (
        orders.aggregate(
            total=Sum("discount")
        ).get("total")
        or Decimal("0.00")
    )

    cancelled_amount = (
        orders.filter(
            order_status="CANCELLED"
        ).aggregate(
            total=Sum("total_amount")
        ).get("total")
        or Decimal("0.00")
    )

    returned_amount = (
        orders.filter(
            order_status="RETURNED"
        ).aggregate(
            total=Sum("total_amount")
        ).get("total")
        or Decimal("0.00")
    )

    net_revenue = (
        total_revenue
        - cancelled_amount
        - returned_amount
    )

    delivered_items = OrderItem.objects.filter(
        order__in=orders,
        status="DELIVERED",
    )

    products_sold = (
        delivered_items.aggregate(
            total=Sum("quantity")
        ).get("total")
        or 0
    )

    coupon_discount = (
        orders.filter(
            coupon__isnull=False
        ).aggregate(
            total=Sum("discount")
        ).get("total")
        or Decimal("0.00")
    )

    offer_discount = (
        total_discounts
        - coupon_discount
    )

    daily_sales = []

    current_date = start_date

    while current_date <= end_date:
        day_start = timezone.make_aware(
            datetime.combine(
                current_date,
                datetime.min.time(),
            )
        )

        day_end = day_start + timedelta(days=1)

        day_orders = orders.filter(
            created_at__gte=day_start,
            created_at__lt=day_end,
        )

        day_revenue = (
            day_orders.aggregate(
                total=Sum("total_amount")
            ).get("total")
            or Decimal("0.00")
        )

        day_cancelled = (
            day_orders.filter(
                order_status="CANCELLED"
            ).aggregate(
                total=Sum("total_amount")
            ).get("total")
            or Decimal("0.00")
        )

        day_returned = (
            day_orders.filter(
                order_status="RETURNED"
            ).aggregate(
                total=Sum("total_amount")
            ).get("total")
            or Decimal("0.00")
        )

        day_net = (
            day_revenue
            - day_cancelled
            - day_returned
        )

        daily_sales.append(
            {
                "date": current_date,
                "label": current_date.strftime("%d %b"),
                "revenue": day_net,
                "orders": day_orders.count(),
            }
        )

        current_date += timedelta(days=1)

    return {
        "orders": orders,
        "total_orders": total_orders,
        "products_sold": products_sold,
        "total_revenue": total_revenue,
        "net_revenue": net_revenue,
        "total_discounts": total_discounts,
        "offer_discount": offer_discount,
        "coupon_discount": coupon_discount,
        "cancelled_amount": cancelled_amount,
        "returned_amount": returned_amount,
        "daily_sales": daily_sales,
    }


@never_cache
@login_required(login_url="admin_login")
@staff_member_required
def sales_report(request):
    dates = get_report_dates(request)

    if dates is None:
        return redirect("sales_report:sales_report")

    start_date, end_date = dates

    report = get_report_data(
        start_date,
        end_date,
    )

    paginator = Paginator(
        report["orders"],
        5,
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    chart_labels = [
        day["label"]
        for day in report["daily_sales"]
    ]

    chart_values = [
        float(day["revenue"])
        for day in report["daily_sales"]
    ]

    context = {
        **report,
        "page_obj": page_obj,
        "from_date": start_date.isoformat(),
        "to_date": end_date.isoformat(),
        "chart_labels": chart_labels,
        "chart_values": chart_values,
    }

    return render(
        request,
        "sales_report/sales_report.html",
        context,
    )


@never_cache
@login_required(login_url="admin_login")
@staff_member_required
def sales_report_excel(request):
    dates = get_report_dates(request)

    if dates is None:
        return redirect("sales_report:sales_report")

    start_date, end_date = dates

    report = get_report_data(
        start_date,
        end_date,
    )

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Sales Report"

    worksheet.append(
        [
            "Order ID",
            "Customer",
            "Date",
            "Payment Method",
            "Payment Status",
            "Order Status",
            "Final Total",
        ]
    )

    for cell in worksheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    for order in report["orders"]:
        customer_name = (
            getattr(order.user, "full_name", None)
            or getattr(order.user, "email", "")
        )

        worksheet.append(
            [
                order.order_id,
                customer_name,
                order.created_at.strftime("%d %b %Y"),
                order.get_payment_method_display(),
                order.get_payment_status_display(),
                order.get_order_status_display(),
                float(order.total_amount),
            ]
        )

    for column in worksheet.columns:
        maximum = 0
        column_letter = column[0].column_letter

        for cell in column:
            length = len(str(cell.value or ""))

            if length > maximum:
                maximum = length

        worksheet.column_dimensions[column_letter].width = min(
            maximum + 2,
            30,
        )

    output = BytesIO()

    workbook.save(output)

    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )

    response["Content-Disposition"] = (
        'attachment; filename="StrideX_Sales_Report.xlsx"'
    )

    return response


@never_cache
@login_required(login_url="admin_login")
@staff_member_required
def sales_report_pdf(request):
    dates = get_report_dates(request)

    if dates is None:
        return redirect("sales_report:sales_report")

    start_date, end_date = dates

    report = get_report_data(
        start_date,
        end_date,
    )

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()

    elements = [
        Paragraph(
            "StrideX Sales Report",
            styles["Title"],
        ),
        Spacer(1, 10),
        Paragraph(
            f"Period: {start_date.strftime('%d %b %Y')} "
            f"to {end_date.strftime('%d %b %Y')}",
            styles["Normal"],
        ),
        Spacer(1, 15),
    ]

    summary_data = [
        [
            "Total Orders",
            "Total Revenue",
            "Net Revenue",
            "Discounts",
            "Cancelled",
            "Returned",
        ],
        [
            str(report["total_orders"]),
            f"₹{report['total_revenue']:.2f}",
            f"₹{report['net_revenue']:.2f}",
            f"₹{report['total_discounts']:.2f}",
            f"₹{report['cancelled_amount']:.2f}",
            f"₹{report['returned_amount']:.2f}",
        ],
    ]

    summary_table = Table(summary_data)

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#eeeeee"),
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    table_data = [
        [
            "Order ID",
            "Customer",
            "Date",
            "Payment",
            "Payment Status",
            "Order Status",
            "Final Total",
        ]
    ]

    for order in report["orders"]:
        customer_name = (
            getattr(order.user, "full_name", None)
            or getattr(order.user, "email", "")
        )

        table_data.append(
            [
                order.order_id,
                str(customer_name),
                order.created_at.strftime("%d %b %Y"),
                order.get_payment_method_display(),
                order.get_payment_status_display(),
                order.get_order_status_display(),
                f"₹{order.total_amount:.2f}",
            ]
        )

    sales_table = Table(
        table_data,
        repeatRows=1,
    )

    sales_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#eeeeee"),
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    elements.append(sales_table)

    document.build(elements)

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        'attachment; filename="StrideX_Sales_Report.pdf"'
    )

    return response