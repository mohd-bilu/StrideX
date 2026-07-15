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