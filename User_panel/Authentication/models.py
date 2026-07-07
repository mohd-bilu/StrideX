from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    username = models.CharField(
        max_length=150,
        unique=True,
        null=True,
        blank=True
    )
    full_name = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )
    email = models.EmailField(unique=True)
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )
    profile_photo = models.ImageField(
        upload_to="profile_photos/",
        blank=True,
        null=True
    )
    date_of_birth = models.DateField(
        blank=True,
        null=True
    )
    is_blocked = models.BooleanField(default=False)

    REQUIRED_FIELDS = [
        "email",
        "full_name"
    ]

    def __str__(self):
        return self.email


class OTP(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="otps"
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):
        if not self.expired_at:
            self.expired_at = timezone.now() + timedelta(minutes=2)

        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expired_at

    def __str__(self):
        return f"{self.user.email} - {self.code}"


class Address(models.Model):
    ADDRESS_TYPES = [
        ("Home", "Home"),
        ("Office", "Office"),
        ("Other", "Other"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses"
    )
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(
        max_length=255,
        blank=True
    )
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=100)
    type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPES
    )
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} - {self.city}"