from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.db.models import Count,Prefetch, Q, Sum
from django.db.models.functions import TruncDate
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from Admin_panel.category.models import Category
from Admin_panel.product.models import Product, Variant
from User_panel.Authentication.models import User
from User_panel.Order.models import Order, OrderItem

from .models import AdminPasswordResetOTP
from .utils import generate_admin_otp, send_admin_otp_email


def admin_required(user):
    return user.is_authenticated and user.is_staff


def admin_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("admin_dashboard")

        logout(request)

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        if not email or not password:
            messages.error(
                request,
                "Email and password are required."
            )
            return redirect("admin_login")

        try:
            admin_user = User.objects.get(email__iexact=email)

        except User.DoesNotExist:
            messages.error(
                request,
                "Invalid email or password."
            )
            return redirect("admin_login")

        if not admin_user.is_staff:
            messages.error(
                request,
                "You are not authorized to access the admin panel."
            )
            return redirect("admin_login")

        if not admin_user.is_active:
            messages.error(
                request,
                "This admin account is inactive."
            )
            return redirect("admin_login")

        user = authenticate(
            request,
            username=admin_user.username,
            password=password
        )

        if user is None:
            messages.error(
                request,
                "Invalid email or password."
            )
            return redirect("admin_login")

        if not user.is_staff:
            messages.error(
                request,
                "You are not authorized to access the admin panel."
            )
            return redirect("admin_login")

        login(request, user)

        messages.success(request, "Admin login successful.")
        return redirect("admin_dashboard")

    return render(
        request,
        "Admin_account/admin_login.html"
    )
@never_cache
@login_required(login_url="admin_login")
def admin_dashboard(request):
    if not request.user.is_staff:
        logout(request)
        messages.error(
            request,
            "You are not authorized to access the admin panel."
        )
        return redirect("admin_login")

    now = timezone.now()

    delivered_orders = Order.objects.filter(
        order_status="DELIVERED"
    )

    total_sales = (
        delivered_orders.aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    current_start = now - timedelta(days=30)
    previous_start = now - timedelta(days=60)

    current_sales = (
        delivered_orders.filter(
            created_at__gte=current_start
        ).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    previous_sales = (
        delivered_orders.filter(
            created_at__gte=previous_start,
            created_at__lt=current_start
        ).aggregate(
            total=Sum("total_amount")
        )["total"]
        or 0
    )

    if previous_sales:
        sales_growth = (
            (current_sales - previous_sales)
            / previous_sales
        ) * 100
    elif current_sales:
        sales_growth = 100
    else:
        sales_growth = 0

    active_orders = Order.objects.filter(
        order_status__in=[
            "PENDING",
            "PROCESSING",
            "SHIPPED",
            "OUT_FOR_DELIVERY",
        ]
    ).count()

    total_customers = User.objects.filter(
        is_staff=False,
        is_superuser=False,
    ).count()

    active_variants = Variant.objects.filter(
        is_active=True,
        is_deleted=False,
    )

    total_stock = (
        active_variants.aggregate(
            total=Sum("stock")
        )["total"]
        or 0
    )

    low_stock_count = active_variants.filter(
        stock__gt=0,
        stock__lte=5,
    ).count()

    out_of_stock_count = active_variants.filter(
        stock=0
    ).count()

    variant_count = active_variants.count()

    if variant_count:
        available_variants = active_variants.filter(
            stock__gt=0
        ).count()

        stock_level = (
            available_variants / variant_count
        ) * 100
    else:
        stock_level = 0

    recent_orders = (
        Order.objects
        .select_related("user")
        .prefetch_related(
            "items__variant__product"
        )
        .order_by("-created_at")[:5]
    )

    hottest_products = (
        Product.objects
        .filter(
            is_active=True,
            is_deleted=False,
            variants__is_active=True,
            variants__is_deleted=False,
            variants__order_items__order__order_status="DELIVERED",
        )
        .annotate(
            sold_quantity=Sum(
                "variants__order_items__quantity",
                filter=Q(
                    variants__order_items__order__order_status="DELIVERED"
                ),
            ),
            revenue=Sum(
                "variants__order_items__total_price",
                filter=Q(
                    variants__order_items__order__order_status="DELIVERED"
                ),
            ),
        )
        .filter(
            sold_quantity__gt=0
        )
        .prefetch_related(
            Prefetch(
                "variants",
                queryset=Variant.objects.filter(
                    is_active=True,
                    is_deleted=False,
                ).prefetch_related("images"),
                to_attr="dashboard_variants",
            )
        )
        .order_by(
            "-sold_quantity",
            "product_name",
        )[:5]
    )

    hottest_releases = []

    for product in hottest_products:
        image_url = ""

        variants = getattr(
            product,
            "dashboard_variants",
            []
        )

        for variant in variants:
            image = variant.images.first()

            if image and image.image:
                image_url = image.image.url
                break

        hottest_releases.append({
            "product_name": product.product_name,
            "sold_quantity": product.sold_quantity or 0,
            "revenue": product.revenue or 0,
            "image_url": image_url,
        })

    category_data = (
        Category.objects
        .filter(
            is_active=True,
            is_deleted=False,
        )
        .annotate(
            inventory_quantity=Sum(
                "products__variants__stock",
                filter=Q(
                    products__is_active=True,
                    products__is_deleted=False,
                    products__variants__is_active=True,
                    products__variants__is_deleted=False,
                ),
            )
        )
        .filter(
            inventory_quantity__gt=0
        )
        .order_by(
            "-inventory_quantity",
            "category_name",
        )
    )

    category_data = list(category_data)

    total_inventory = sum(
        category.inventory_quantity or 0
        for category in category_data
    )

    category_distribution = []

    for category in category_data:
        inventory_quantity = (
            category.inventory_quantity
            or 0
        )

        if total_inventory:
            percentage = (
                inventory_quantity
                / total_inventory
            ) * 100
        else:
            percentage = 0

        category_distribution.append({
            "name": category.category_name,
            "count": inventory_quantity,
            "percentage": round(
                percentage,
                1
            ),
        })

    sales_end = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    sales_start = sales_end - timedelta(days=29)

    daily_sales = (
        delivered_orders
        .filter(
            created_at__gte=sales_start,
            created_at__lt=(
                sales_end
                + timedelta(days=1)
            ),
        )
        .annotate(
            day=TruncDate("created_at")
        )
        .values("day")
        .annotate(
            revenue=Sum("total_amount"),
            orders=Count("id"),
        )
        .order_by("day")
    )

    daily_sales = {
        row["day"]: row
        for row in daily_sales
    }

    sales_trajectory = []

    for day_number in range(30):
        current_day = (
            sales_start.date()
            + timedelta(days=day_number)
        )

        row = daily_sales.get(
            current_day,
            {
                "revenue": 0,
                "orders": 0,
            }
        )

        sales_trajectory.append({
            "date": current_day,
            "label": current_day.strftime("%d %b"),
            "short_label": current_day.strftime("%d"),
            "revenue": row["revenue"] or 0,
            "orders": row["orders"] or 0,
        })

    max_revenue = max(
        (
            float(row["revenue"] or 0)
            for row in sales_trajectory
        ),
        default=0,
    )

    max_orders = max(
        (
            int(row["orders"] or 0)
            for row in sales_trajectory
        ),
        default=0,
    )

    for row in sales_trajectory:
        revenue = float(
            row["revenue"] or 0
        )

        orders = int(
            row["orders"] or 0
        )

        if max_revenue:
            row["revenue_percentage"] = round(
                (revenue / max_revenue) * 100,
                1,
            )
        else:
            row["revenue_percentage"] = 0

        if max_orders:
            row["orders_percentage"] = round(
                (orders / max_orders) * 100,
                1,
            )
        else:
            row["orders_percentage"] = 0

    context = {
        "total_sales": total_sales,
        "sales_growth": round(
            sales_growth,
            1
        ),
        "current_sales": current_sales,
        "active_orders": active_orders,
        "total_customers": total_customers,
        "stock_level": round(
            stock_level,
            1
        ),
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "total_stock": total_stock,
        "recent_orders": recent_orders,
        "hottest_releases": hottest_releases,
        "category_distribution": category_distribution,
        "sales_trajectory": sales_trajectory,
    }

    return render(
        request,
        "Admin_account/admin_dashboard.html",
        context,
    )

@never_cache
@login_required(login_url="admin_login")
@require_POST
def admin_logout(request):
    logout(request)

    messages.success(request, "Logged out successfully.")
    return redirect("admin_login")


def user_management(request):
    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()
    sort_by = request.GET.get("sort", "latest").strip()

    users = User.objects.all()

    if search_query:
        users = users.filter(
            Q(full_name__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    if status_filter == "active":
        users = users.filter(
            is_active=True,
            is_blocked=False,
        )
    elif status_filter == "blocked":
        users = users.filter(
            Q(is_blocked=True)
            | Q(is_active=False)
        )

    if sort_by == "oldest":
        users = users.order_by("date_joined")
    elif sort_by == "name_az":
        users = users.order_by("full_name", "id")
    elif sort_by == "name_za":
        users = users.order_by("-full_name", "-id")
    else:
        sort_by = "latest"
        users = users.order_by("-date_joined", "-id")

    paginator = Paginator(users, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    total_users = User.objects.count()

    active_users = User.objects.filter(
        is_active=True,
        is_blocked=False,
    ).count()

    blocked_users = User.objects.filter(
        Q(is_blocked=True)
        | Q(is_active=False)
    ).count()

    thirty_days_ago = timezone.now() - timedelta(days=30)

    new_users = User.objects.filter(
        date_joined__gte=thirty_days_ago
    ).count()

    return render(
        request,
        "Admin_account/user_management.html",
        {
            "page_obj": page_obj,
            "search_query": search_query,
            "status_filter": status_filter,
            "sort_by": sort_by,
            "total_users": total_users,
            "active_users": active_users,
            "blocked_users": blocked_users,
            "new_users": new_users,
        },
    )
@never_cache
@login_required(login_url="admin_login")
@require_POST
def toggle_user_status(request, user_id):
    if not request.user.is_staff:
        logout(request)

        messages.error(
            request,
            "You are not authorized to perform this action."
        )
        return redirect("admin_login")

    user = get_object_or_404(
        User,
        id=user_id,
        is_staff=False,
        is_superuser=False
    )

    if user.is_blocked:
        user.is_blocked = False
        user.is_active = True

        user.save(
            update_fields=[
                "is_blocked",
                "is_active"
            ]
        )

        messages.success(
            request,
            "User unblocked successfully."
        )

    else:
        user.is_blocked = True
        user.is_active = False

        user.save(
            update_fields=[
                "is_blocked",
                "is_active"
            ]
        )

        messages.success(
            request,
            "User blocked successfully."
        )

    return redirect("user_management")
@never_cache
@login_required(login_url="admin_login")
def admin_forgot_password(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin_dashboard")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()

        if not email:
            messages.error(request, "Email is required.")
            return redirect("admin_forgot_password")

        try:
            admin_user = User.objects.get(
                email__iexact=email,
                is_staff=True
            )

        except User.DoesNotExist:
            messages.error(
                request,
                "No admin account found with this email."
            )
            return redirect("admin_forgot_password")

        if not admin_user.is_active:
            messages.error(
                request,
                "This admin account is inactive."
            )
            return redirect("admin_forgot_password")

        AdminPasswordResetOTP.objects.filter(
            admin=admin_user,
            is_used=False
        ).update(is_used=True)

        otp_code = generate_admin_otp()

        AdminPasswordResetOTP.objects.create(
            admin=admin_user,
            code=otp_code
        )

        send_admin_otp_email(
            admin_user.email,
            otp_code
        )

        request.session["admin_reset_email"] = admin_user.email
        request.session["admin_reset_verified"] = False

        messages.success(request, "OTP sent successfully.")
        return redirect("admin_verify_otp")

    return render(
        request,
        "Admin_account/admin_forgot_password.html"
    )


def admin_verify_otp(request):
    email = request.session.get("admin_reset_email")

    if not email:
        messages.error(
            request,
            "Password reset session expired."
        )
        return redirect("admin_forgot_password")

    try:
        admin_user = User.objects.get(
            email__iexact=email,
            is_staff=True
        )

    except User.DoesNotExist:
        messages.error(
            request,
            "Admin account not found."
        )
        return redirect("admin_forgot_password")

    latest_otp = (
        AdminPasswordResetOTP.objects
        .filter(
            admin=admin_user,
            is_used=False
        )
        .order_by("-created_at")
        .first()
    )

    remaining_seconds = 0

    if latest_otp:
        remaining_seconds = max(
            0,
            int(
                (
                    latest_otp.expired_at
                    - timezone.now()
                ).total_seconds()
            )
        )

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()

        if not entered_otp.isdigit() or len(entered_otp) != 6:
            messages.error(
                request,
                "Enter a valid 6-digit OTP."
            )
            return redirect("admin_verify_otp")

        if not latest_otp:
            messages.error(
                request,
                "OTP not found. Request a new OTP."
            )
            return redirect("admin_verify_otp")

        if latest_otp.is_expired():
            messages.error(request, "OTP has expired.")
            return redirect("admin_verify_otp")

        if latest_otp.code != entered_otp:
            messages.error(request, "Invalid OTP.")
            return redirect("admin_verify_otp")

        latest_otp.is_used = True
        latest_otp.save(update_fields=["is_used"])

        request.session["admin_reset_verified"] = True

        messages.success(
            request,
            "OTP verified successfully."
        )
        return redirect("admin_reset_password")

    context = {
        "email": email,
        "remaining_seconds": remaining_seconds
    }

    return render(
        request,
        "Admin_account/admin_verify_otp.html",
        context
    )


def admin_resend_otp(request):
    email = request.session.get("admin_reset_email")

    if not email:
        messages.error(
            request,
            "Password reset session expired."
        )
        return redirect("admin_forgot_password")

    try:
        admin_user = User.objects.get(
            email__iexact=email,
            is_staff=True
        )

    except User.DoesNotExist:
        messages.error(
            request,
            "Admin account not found."
        )
        return redirect("admin_forgot_password")

    current_otp = (
        AdminPasswordResetOTP.objects
        .filter(
            admin=admin_user,
            is_used=False
        )
        .order_by("-created_at")
        .first()
    )

    if current_otp and not current_otp.is_expired():
        messages.warning(
            request,
            "Current OTP is still active."
        )
        return redirect("admin_verify_otp")

    AdminPasswordResetOTP.objects.filter(
        admin=admin_user,
        is_used=False
    ).update(is_used=True)

    otp_code = generate_admin_otp()

    AdminPasswordResetOTP.objects.create(
        admin=admin_user,
        code=otp_code
    )

    send_admin_otp_email(
        admin_user.email,
        otp_code
    )

    messages.success(
        request,
        "New OTP sent successfully."
    )
    return redirect("admin_verify_otp")

@never_cache
@login_required(login_url="admin_login")
def admin_reset_password(request):
    email = request.session.get("admin_reset_email")
    verified = request.session.get(
        "admin_reset_verified",
        False
    )

    if not email or not verified:
        messages.error(
            request,
            "Verify your OTP first."
        )
        return redirect("admin_forgot_password")

    try:
        admin_user = User.objects.get(
            email__iexact=email,
            is_staff=True
        )

    except User.DoesNotExist:
        messages.error(
            request,
            "Admin account not found."
        )
        return redirect("admin_forgot_password")

    if request.method == "POST":
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )

        if not new_password or not confirm_password:
            messages.error(
                request,
                "Both password fields are required."
            )
            return redirect("admin_reset_password")

        if new_password != confirm_password:
            messages.error(
                request,
                "Passwords do not match."
            )
            return redirect("admin_reset_password")

        if admin_user.check_password(new_password):
            messages.error(
                request,
                "New password cannot be the same as the current password."
            )
            return redirect("admin_reset_password")

        try:
            validate_password(
                new_password,
                user=admin_user
            )

        except ValidationError as errors:
            for error in errors.messages:
                messages.error(request, error)

            return redirect("admin_reset_password")

        admin_user.set_password(new_password)
        admin_user.save(update_fields=["password"])

        request.session.pop("admin_reset_email", None)
        request.session.pop("admin_reset_verified", None)

        messages.success(
            request,
            "Password reset successfully. Please sign in."
        )
        return redirect("admin_login")

    return render(
        request,
        "Admin_account/admin_reset_password.html"
    )