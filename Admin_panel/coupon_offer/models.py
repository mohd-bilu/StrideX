from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ("PERCENTAGE", "Percentage"),
        ("FIXED", "Fixed Amount"),
    )

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default="PERCENTAGE",
    )

    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
        ],
    )

    minimum_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
        ],
    )

    maximum_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
        ],
    )

    start_date = models.DateTimeField()

    expiry_date = models.DateTimeField()

    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    used_count = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "coupons"
        ordering = [
            "-created_at",
        ]
        verbose_name = "Coupon"
        verbose_name_plural = "Coupons"

    def __str__(self):
        return self.code


class CouponUsage(models.Model):
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name="usages",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="coupon_usages",
    )

    order = models.ForeignKey(
        "Order.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coupon_usage",
    )

    used_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "coupon_usages"
        ordering = [
            "-used_at",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "coupon",
                    "user",
                ],
                name="unique_coupon_user_usage",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.coupon.code}"