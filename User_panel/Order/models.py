from django.db import models
from django.conf import settings
from django.utils import timezone
from Admin_panel.product.models import Variant
from User_panel.Authentication.models import Address


class Order(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("SHIPPED", "Shipped"),
        ("OUT_FOR_DELIVERY", "Out For Delivery"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
        ("RETURN_REQUESTED", "Return Requested"),
        ("RETURNED", "Returned"),
    )

    PAYMENT_METHOD_CHOICES = (
        ("COD", "Cash On Delivery"),
    )

    PAYMENT_STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    order_id = models.CharField(
        max_length=25,
        unique=True,
        blank=True
    )

    address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        related_name="orders"
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="COD"
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="PENDING"
    )

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    shipping_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    order_status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.order_id:
            super().save(*args, **kwargs)

            self.order_id = f"ORD{self.id:05d}"

            super().save(
                update_fields=["order_id"]
            )

            return

        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_id


class OrderItem(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("SHIPPED", "Shipped"),
        ("OUT_FOR_DELIVERY", "Out For Delivery"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
        ("RETURN_REQUESTED", "Return Requested"),
        ("RETURNED", "Returned"),
        ("REJECTED", "Rejected"),
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    variant = models.ForeignKey(
        Variant,
        on_delete=models.PROTECT,
        related_name="order_items"
    )

    quantity = models.PositiveIntegerField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    cancel_reason = models.TextField(
        blank=True,
        null=True
    )

    return_reason = models.TextField(
        blank=True,
        null=True
    )

    rejection_reason = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.total_price = self.price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order.order_id} - {self.variant}"