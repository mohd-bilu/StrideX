import random

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone

from .models import User, Address
from .validators import validate_signup
from .utils import send_otp_email


def generate_otp():
    otp = ""

    for i in range(6):
        otp += str(random.randint(0, 9))

    return otp


@never_cache
def signup(request):
    if request.user.is_authenticated:
        return redirect("user_home")

    if request.method == "POST":
        fullname = request.POST.get("fullname", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        agree = request.POST.get("agree")

        error = validate_signup(
            fullname,
            email,
            password,
            confirm_password
        )

        if error:
            messages.error(request, error)
            return redirect("signup")

        if not agree:
            messages.error(request, "Accept Terms & Conditions")
            return redirect("signup")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect("signup")

        otp = generate_otp()

        request.session["signup_data"] = {
            "fullname": fullname,
            "email": email,
            "password": password
        }
        request.session["otp"] = otp
        request.session["otp_created_at"] = timezone.now().timestamp()

        send_otp_email(email, otp)

        messages.success(request, "OTP sent successfully.")
        return redirect("verify_otp")

    return render(request, "Authentication/signup_page.html")

@never_cache
def verify_otp(request):
    if "signup_data" not in request.session:
        messages.error(request, "Session expired.")
        return redirect("signup")

    if "otp" not in request.session:
        messages.error(request, "OTP expired.")
        return redirect("signup")

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        session_otp = request.session.get("otp")
        otp_created_at = request.session.get("otp_created_at")

        if not otp_created_at:
            messages.error(
                request,
                "OTP expired. Please request a new OTP."
            )
            return redirect("signup")

        current_time = timezone.now().timestamp()

        if current_time - otp_created_at > 120:
            request.session.pop("otp", None)
            request.session.pop("otp_created_at", None)

            messages.error(
                request,
                "OTP expired. Please request a new OTP."
            )
            return redirect("signup")

        if entered_otp != session_otp:
            messages.error(request, "Invalid OTP")
            return redirect("verify_otp")

        signup_data = request.session["signup_data"]

        User.objects.create_user(
            username=signup_data["email"],
            email=signup_data["email"],
            password=signup_data["password"],
            full_name=signup_data["fullname"],
            is_active=True
        )

        request.session.pop("signup_data", None)
        request.session.pop("otp", None)
        request.session.pop("otp_created_at", None)

        messages.success(request, "Account created successfully.")
        return redirect("login")

    return render(
        request,
        "Authentication/otp_verification.html",
        {"email": request.session["signup_data"]["email"]}
    )

@never_cache
def resend_otp(request):
    if "signup_data" not in request.session:
        messages.error(request, "Signup session expired.")
        return redirect("signup")

    otp = generate_otp()

    request.session["otp"] = otp
    request.session["otp_created_at"] = timezone.now().timestamp()

    email = request.session["signup_data"]["email"]

    send_otp_email(email, otp)

    messages.success(request, "New OTP sent successfully.")
    return redirect("verify_otp")


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect("user_home")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        try:
            existing_user = User.objects.get(email__iexact=email)

        except User.DoesNotExist:
            existing_user = None

        if existing_user and (
            existing_user.is_blocked
            or not existing_user.is_active
        ):
            messages.error(
                request,
                "Your account has been blocked. Please contact support."
            )
            return redirect("login")

        user = authenticate(
            request,
            username=existing_user.username if existing_user else email,
            password=password
        )

        if user is not None:
            login(request, user)

            messages.success(request, "Login successful.")
            return redirect("user_home")

        messages.error(request, "Invalid email or password.")
        return redirect("login")

    return render(request, "Authentication/login.html")


@never_cache
@login_required(login_url="login")
def logout_view(request):
    if request.method == "POST":
        logout(request)

        messages.success(request, "Logged out successfully.")
        return redirect("login")

    return redirect("profile")


@never_cache
@login_required(login_url="login")
def user_home(request):
    return render(request, "Authentication/home.html")


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            messages.error(request, "Enter your email.")
            return redirect("forgot_password")

        try:
            User.objects.get(email=email)

        except User.DoesNotExist:
            messages.error(request, "Email not registered.")
            return redirect("forgot_password")

        otp = generate_otp()

        request.session["reset_email"] = email
        request.session["reset_otp"] = otp
        request.session["reset_otp_created_at"] = (
            timezone.now().timestamp()
        )

        send_otp_email(email, otp)

        messages.success(request, "OTP sent to your email.")
        return redirect("forgot_password_verify_otp")

    return render(
        request,
        "Authentication/forgot_password.html"
    )

@never_cache
def forgot_password_verify_otp(request):
    if "reset_email" not in request.session:
        messages.error(request, "Session expired.")
        return redirect("forgot_password")

    if "reset_otp" not in request.session:
        messages.error(request, "OTP expired.")
        return redirect("forgot_password")

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        session_otp = request.session.get("reset_otp")
        otp_created_at = request.session.get(
            "reset_otp_created_at"
        )

        if not otp_created_at:
            messages.error(request, "OTP expired.")
            return redirect("forgot_password")

        current_time = timezone.now().timestamp()

        if current_time - otp_created_at > 120:
            request.session.pop("reset_otp", None)
            request.session.pop("reset_otp_created_at",None)

            messages.error(request, "OTP expired.")
            return redirect("forgot_password")

        if entered_otp != session_otp:
            messages.error(request, "Invalid OTP")
            return redirect("forgot_password_verify_otp")

        request.session["reset_otp_verified"] = True

        request.session.pop("reset_otp", None)
        request.session.pop("reset_otp_created_at",None)

        messages.success(request,"OTP verified successfully.")
        return redirect("reset_password")

    return render(
        request,
        "Authentication/forgot_password_otp.html",
        {"email": request.session["reset_email"]}
    )

@never_cache
def resend_forgot_password_otp(request):
    if "reset_email" not in request.session:
        messages.error(request, "Session expired.")
        return redirect("forgot_password")

    otp = generate_otp()

    request.session["reset_otp"] = otp
    request.session["reset_otp_created_at"] = (
        timezone.now().timestamp()
    )

    email = request.session["reset_email"]

    send_otp_email(email, otp)

    messages.success(request, "New OTP sent successfully.")
    return redirect("forgot_password_verify_otp")

def reset_password(request):
    if "reset_email" not in request.session:
        messages.error(request, "Session expired.")
        return redirect("forgot_password")

    if not request.session.get("reset_otp_verified"):
        messages.error(request, "Please verify OTP first.")
        return redirect("forgot_password")

    if request.method == "POST":
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not new_password or not confirm_password:
            messages.error(request, "All fields are required.")
            return redirect("reset_password")

        if len(new_password) < 8:
            messages.error(
                request,
                "Password must contain at least 8 characters."
            )
            return redirect("reset_password")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("reset_password")

        email = request.session["reset_email"]

        try:
            user = User.objects.get(email=email)

        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect("forgot_password")

        if user.check_password(new_password):
            messages.error(
                request,
                "New password cannot be the same as your old password."
            )
            return redirect("reset_password")

        user.set_password(new_password)
        user.save()

        request.session.pop("reset_email", None)
        request.session.pop("reset_otp", None)
        request.session.pop("reset_otp_created_at", None)
        request.session.pop("reset_otp_verified", None)

        messages.success(
            request,
            "Password reset successfully. Please login."
        )
        return redirect("login")

    return render(
        request,
        "Authentication/reset_password.html"
    )

@never_cache
@login_required(login_url="login")
def profile(request):
    return render(
        request,
        "Authentication/profile.html",
        {"user": request.user}
    )


@login_required(login_url="login")
def edit_profile(request):
    user = request.user

    if request.method == "POST":
        full_name = request.POST.get(
            "full_name","").strip()

        phone_number = request.POST.get(
            "phone_number","").strip()
        if len(phone_number)<10:
            messages.error(request,'Phone number should be 10 digits')
            return redirect("edit_profile") 

        date_of_birth = request.POST.get(
            "date_of_birth","").strip()

        profile_photo = request.FILES.get("profile_photo")
        remove_photo = request.POST.get("remove_photo")

        if not full_name:
            messages.error(request,"Full name is required.")
            return redirect("edit_profile")

        user.full_name = full_name
        user.phone_number = phone_number

        if date_of_birth:
            user.date_of_birth = date_of_birth

        else:
            user.date_of_birth = None

        if remove_photo:
            if user.profile_photo:
                user.profile_photo.delete(
                    save=False
                )

            user.profile_photo = None

        elif profile_photo:
            allowed_types = [
                "image/jpeg",
                "image/png",
                "image/gif"
            ]

            if profile_photo.content_type not in allowed_types:
                messages.error(
                    request,
                    "Only JPG, PNG or GIF images are allowed."
                )
                return redirect("edit_profile")

            if profile_photo.size > 1024 * 1024:
                messages.error(
                    request,
                    "Maximum image size is 1MB."
                )
                return redirect("edit_profile")

            if user.profile_photo:
                user.profile_photo.delete(
                    save=False
                )

            user.profile_photo = profile_photo

        user.save()

        messages.success(request,"Profile updated successfully.")
        return redirect("profile")

    return render(
        request,
        "Authentication/edit_profile.html",
        {"user": user}
    )

@login_required(login_url="login")
def change_email(request):
    user = request.user

    if request.method == "POST":
        new_email = request.POST.get(
            "email",
            ""
        ).strip().lower()

        if not new_email:
            messages.error(request, "Please enter an email.")
            return redirect("change_email")

        if new_email == user.email:
            messages.error(
                request,
                "New email cannot be same as current email."
            )
            return redirect("change_email")

        if User.objects.filter(email=new_email).exists():
            messages.error(
                request,
                "Email already registered."
            )
            return redirect("change_email")

        otp = generate_otp()

        request.session["new_email"] = new_email
        request.session["email_change_otp"] = otp
        request.session["email_change_otp_created_at"] = (
            timezone.now().timestamp()
        )

        send_otp_email(new_email, otp)

        messages.success(
            request,
            "OTP sent to your new email."
        )
        return redirect("verify_email_otp")

    return render(
        request,
        "Authentication/change_email.html",
        {"user": user}
    )

@never_cache
@login_required(login_url="login")
def verify_email_otp(request):
    if (
        "new_email" not in request.session
        or "email_change_otp" not in request.session
    ):
        messages.error(
            request,
            "Email verification session expired."
        )
        return redirect("change_email")

    user = request.user

    if request.method == "POST":
        entered_otp = request.POST.get("otp", "").strip()
        session_otp = request.session.get(
            "email_change_otp"
        )
        otp_created_at = request.session.get(
            "email_change_otp_created_at"
        )

        if not otp_created_at:
            messages.error(request, "OTP expired.")
            return redirect("change_email")

        current_time = timezone.now().timestamp()

        if current_time - otp_created_at > 120:
            request.session.pop(
                "email_change_otp",
                None
            )
            request.session.pop(
                "email_change_otp_created_at",
                None
            )

            messages.error(request, "OTP expired.")
            return redirect("change_email")

        if entered_otp != session_otp:
            messages.error(request, "Invalid OTP.")
            return redirect("verify_email_otp")

        new_email = request.session["new_email"]

        if User.objects.filter(
            email=new_email
        ).exclude(
            id=user.id
        ).exists():
            messages.error(
                request,
                "This email is already registered."
            )

            request.session.pop("new_email", None)
            request.session.pop(
                "email_change_otp",
                None
            )
            request.session.pop(
                "email_change_otp_created_at",
                None
            )

            return redirect("change_email")

        user.email = new_email
        user.username = new_email

        user.save(
            update_fields=[
                "email",
                "username"
            ]
        )

        request.session.pop("new_email", None)
        request.session.pop(
            "email_change_otp",
            None
        )
        request.session.pop(
            "email_change_otp_created_at",
            None
        )

        messages.success(
            request,
            "Email updated successfully."
        )
        return redirect("profile")

    return render(
        request,
        "Authentication/verify_email_otp.html",
        {"email": request.session["new_email"]}
    )


@never_cache
@login_required(login_url="login")
def resend_email_change_otp(request):
    if "new_email" not in request.session:
        messages.error(
            request,
            "Email change session expired."
        )
        return redirect("change_email")

    otp = generate_otp()

    request.session["email_change_otp"] = otp
    request.session["email_change_otp_created_at"] = (
        timezone.now().timestamp()
    )

    email = request.session["new_email"]

    send_otp_email(email, otp)

    messages.success(
        request,
        "New OTP sent successfully."
    )
    return redirect("verify_email_otp")

@never_cache
@login_required(login_url="login")
def change_password(request):
    user = request.user

    if request.method == "POST":
        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if (
            not current_password or not new_password or not confirm_password
        ):
            messages.error(request, "All fields are required.")
            return redirect("change_password")

        if not user.check_password(current_password):
            messages.error(
                request,
                "Current password is incorrect."
            )
            return redirect("change_password")

        if new_password != confirm_password:
            messages.error(
                request,
                "New passwords do not match."
            )
            return redirect("change_password")

        if len(new_password) < 8:
            messages.error(
                request,
                "Password must be at least 8 characters."
            )
            return redirect("change_password")

        if user.check_password(new_password):
            messages.error(
                request,
                "New password cannot be the same as current password."
            )
            return redirect("change_password")

        user.set_password(new_password)
        user.save()

        update_session_auth_hash(request, user)

        messages.success(
            request,
            "Password changed successfully."
        )
        return redirect("profile")

    return render(
        request,
        "Authentication/change_password.html",
        {"user": user}
    )


@login_required(login_url="login")
def address_list(request):
    addresses = Address.objects.filter(user=request.user)

    return render(
        request,
        "Authentication/address_list.html",
        {"addresses": addresses}
    )


@login_required(login_url="login")
def add_address(request):
    user = request.user

    if request.method == "POST":
        pincode = request.POST.get("pincode", "").strip()

        if not pincode.isdigit() or len(pincode) != 6:
            messages.error(
                request,
                "Pincode must contain exactly 6 digits."
            )
            return redirect("add_address")

        is_default = request.POST.get("is_default")

        if is_default:
            Address.objects.filter(
                user=user
            ).update(
                is_default=False
            )

        Address.objects.create(
            user=user,
            full_name=request.POST.get("full_name"),
            phone_number=request.POST.get("phone_number"),
            address_line1=request.POST.get("address_line1"),
            address_line2=request.POST.get("address_line2"),
            city=request.POST.get("city"),
            state=request.POST.get("state"),
            pincode=pincode,
            country=request.POST.get("country"),
            type=request.POST.get("type"),
            is_default=bool(is_default)
        )

        messages.success(
            request,
            "Address Added Successfully."
        )
        return redirect("address_list")

    return render(
        request,
        "Authentication/add_address.html"
    )


@login_required(login_url="login")
def edit_address(request, id):
    address = get_object_or_404(
        Address,
        id=id,
        user=request.user
    )

    if request.method == "POST":
        pincode = request.POST.get("pincode", "").strip()

        if not pincode.isdigit():
            messages.error(
                request,
                "Pincode must contain only numbers."
            )
            return redirect("edit_address", id=id)

        if len(pincode) < 6:
            messages.error(
                request,
                "Pincode cannot be less than 6 digits."
            )
            return redirect("edit_address", id=id)

        if len(pincode) > 6:
            messages.error(
                request,
                "Pincode cannot be more than 6 digits."
            )
            return redirect("edit_address", id=id)

        address.full_name = request.POST.get("full_name")
        address.phone_number = request.POST.get("phone_number")
        address.address_line1 = request.POST.get("address_line1")
        address.address_line2 = request.POST.get("address_line2")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.pincode = pincode
        address.country = request.POST.get("country")
        address.type = request.POST.get("type")

        if request.POST.get("is_default"):
            Address.objects.filter(
                user=request.user
            ).exclude(
                id=address.id
            ).update(
                is_default=False
            )

            address.is_default = True

        address.save()

        messages.success(
            request,
            "Address Updated Successfully."
        )
        return redirect("address_list")

    return render(
        request,
        "Authentication/edit_address.html",
        {"address": address}
    )


@login_required(login_url="login")
def delete_address(request, id):
    address = get_object_or_404(
        Address,
        id=id,
        user=request.user
    )

    if request.method == "POST":
        address.delete()

        messages.success(
            request,
            "Address deleted successfully."
        )

    return redirect("address_list")


@login_required(login_url="login")
def make_default_address(request, id):
    address = get_object_or_404(
        Address,
        id=id,
        user=request.user
    )

    Address.objects.filter(
        user=request.user
    ).update(
        is_default=False
    )

    address.is_default = True
    address.save(update_fields=["is_default"])

    messages.success(
        request,
        "Default Address Updated."
    )
    return redirect("address_list")