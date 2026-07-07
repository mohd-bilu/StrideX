import random

from django.core.mail import send_mail
from django.conf import settings


def generate_admin_otp():
    return str(random.randint(100000, 999999))


def send_admin_otp_email(email, otp):
    subject = "StrideX Admin Password Reset OTP"

    message = f"""
Your StrideX Admin password reset OTP is:

{otp}

This OTP will expire in 2 minutes.

If you did not request a password reset,
please ignore this email.
"""

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False
    )