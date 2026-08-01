import re

from django import forms
from django.utils.text import slugify

from .models import Category


class CategoryForm(forms.ModelForm):

    class Meta:
        model = Category
        fields = [
            "category_name",
            "description",
            "image",
            "is_active",
        ]

    def clean_category_name(self):
        category_name = self.cleaned_data.get(
            "category_name",
            ""
        ).strip()

        if not category_name:
            raise forms.ValidationError(
                "Category name cannot be empty."
            )

        if category_name.isdigit():
            raise forms.ValidationError(
                "Category name cannot contain only numbers."
            )

        if not re.fullmatch(
            r"[A-Za-z0-9 _-]+",
            category_name,
        ):
            raise forms.ValidationError(
                "Only letters, numbers, spaces, hyphens (-) and underscores (_) are allowed."
            )

        if not re.search(
            r"[A-Za-z]",
            category_name,
        ):
            raise forms.ValidationError(
                "Category name must contain at least one letter."
            )

        duplicate = Category.objects.filter(
            category_name__iexact=category_name,
            is_deleted=False,
        ).exclude(
            pk=self.instance.pk,
        )

        if duplicate.exists():
            raise forms.ValidationError(
                "Category name already exists."
            )

        return category_name

    def clean_image(self):
        image = self.cleaned_data.get("image")

        if image:

            allowed_extensions = (
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
            )

            if not image.name.lower().endswith(
                allowed_extensions,
            ):
                raise forms.ValidationError(
                    "Only JPG, JPEG, PNG and WEBP images are allowed."
                )

            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    "Image size should not exceed 5 MB."
                )

        return image

    def save(self, commit=True):
        category = super().save(commit=False)

        category.category_name = (
            category.category_name.strip()
        )

        category.slug = slugify(
            category.category_name
        )

        if commit:
            category.save()

        return category