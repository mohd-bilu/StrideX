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

        category_name = (
            self.cleaned_data["category_name"]
            .strip()
        )

        exists = Category.objects.filter(
            category_name__iexact=category_name,
            is_deleted=False,
        ).exclude(
            pk=self.instance.pk
        ).exists()

        if exists:

            raise forms.ValidationError(
                "Category already exists."
            )

        return category_name

    def clean_image(self):

        image = self.cleaned_data.get(
            "image"
        )

        if image:

            allowed_extensions = [
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
            ]

            extension = (
                image.name.lower()
            )

            if not extension.endswith(
                tuple(allowed_extensions)
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

        category = super().save(
            commit=False
        )

        category.slug = slugify(
            category.category_name
        )

        if commit:

            category.save()

        return category