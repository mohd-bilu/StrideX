from django.db import models
from Admin_panel.category.models import Category


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    product_name = models.CharField(
        max_length=200,
    )
    description = models.TextField(
        blank=True,
    )
    is_active = models.BooleanField(
        default=True,
    )
    is_deleted = models.BooleanField(
        default=False,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "products"
        ordering = [
            "-created_at",
        ]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.product_name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(
        upload_to="product_images/",
    )
    is_primary = models.BooleanField(
        default=False,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "product_images"
        ordering = [
            "-is_primary",
            "created_at",
        ]
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"

    def __str__(self):
        return (
            f"{self.product.product_name} "
            f"Image {self.id}"
        )


class Variant(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )

    sku = models.CharField(
        max_length=100,
        unique=True,
    )

    size = models.CharField(
        max_length=20,
    )

    color = models.CharField(
        max_length=50,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    stock = models.PositiveIntegerField()

    is_active = models.BooleanField(
        default=True,
    )

    is_default = models.BooleanField(
        default=False,
    )

    is_deleted = models.BooleanField(
        default=False,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        db_table = "variants"

        ordering = [
            "-updated_at",
        ]
class VariantImage(models.Model):
    variant = models.ForeignKey(
        Variant,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(
        upload_to="variant_images/",
    )
    is_primary = models.BooleanField(
        default=False,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "variant_images"
        ordering = [
            "-is_primary",
            "created_at",
        ]

    def __str__(self):
        return (
            f"{self.variant.sku}"
            f" Image "
            f"{self.id}"
        )