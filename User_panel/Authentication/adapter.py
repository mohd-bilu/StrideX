from django.contrib import messages
from django.shortcuts import redirect

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import User


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(
            request,
            sociallogin,
            data
        )

        full_name = (data.get("name") or "").strip()

        if not full_name:
            first_name = (data.get("first_name") or "").strip()
            last_name = (data.get("last_name") or "").strip()
            full_name = f"{first_name} {last_name}".strip()

        if not full_name:
            extra_data = sociallogin.account.extra_data or {}
            full_name = (extra_data.get("name") or "").strip()

        user.full_name = full_name

        return user

    def pre_social_login(self, request, sociallogin):
        super().pre_social_login(
            request,
            sociallogin
        )

        email = (sociallogin.user.email or "").strip()

        if not email:
            email = sociallogin.account.extra_data.get(
                "email",
                ""
            ).strip()

        if not email:
            return

        existing_user = User.objects.filter(
            email__iexact=email
        ).first()

        if existing_user and (
            existing_user.is_staff
            or existing_user.is_superuser
        ):
            messages.error(
                request,
                "Admin accounts cannot log in through the user portal."
            )

            raise ImmediateHttpResponse(
                redirect("login")
            )

        if existing_user and (
            existing_user.is_blocked
            or not existing_user.is_active
        ):
            messages.error(
                request,
                "Your account has been blocked. Please contact support."
            )

            raise ImmediateHttpResponse(
                redirect("login")
            )