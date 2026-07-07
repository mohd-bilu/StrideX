from django.core.mail import send_mail
from django.conf import settings


def send_otp_email(email, otp):
    subject = "StrideX Email Verification"

    message = f"""
Welcome to StrideX.

Your OTP is

{otp}

This OTP expires in 2 minutes.
"""

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False
    )