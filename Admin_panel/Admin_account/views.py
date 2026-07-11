from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from User_panel.Authentication.models import User
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

    return render(
        request,
        "Admin_account/admin_dashboard.html"
    )


@never_cache
@login_required(login_url="admin_login")
@require_POST
def admin_logout(request):
    logout(request)

    messages.success(request, "Logged out successfully.")
    return redirect("admin_login")


@never_cache
@login_required(login_url="admin_login")
def user_management(request):
    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    base_users = User.objects.filter(
        is_staff=False,
        is_superuser=False
    )

    total_users = base_users.count()

    active_users = base_users.filter(
        is_active=True,
        is_blocked=False
    ).count()

    blocked_users = base_users.filter(
        is_blocked=True
    ).count()

    seven_days_ago = timezone.now() - timedelta(days=7)

    new_users = base_users.filter(
        date_joined__gte=seven_days_ago
    ).count()

    users = base_users.order_by("-date_joined")

    if search_query:
        users = users.filter(
            Q(full_name__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    if status_filter == "active":
        users = users.filter(
            is_active=True,
            is_blocked=False
        )

    elif status_filter == "blocked":
        users = users.filter(is_blocked=True)

    paginator = Paginator(users, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "status_filter": status_filter,
        "total_users": total_users,
        "active_users": active_users,
        "new_users": new_users,
        "blocked_users": blocked_users,
    }

    return render(
        request,
        "Admin_account/user_management.html",
        context
    )

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