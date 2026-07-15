from django import forms

from .models import Product


class ProductForm(forms.ModelForm):

    class Meta:

        model = Product

        fields = [
            "category",
            "product_name",
            "description",
            "is_active",
        ]

    def clean_product_name(self):

        product_name = (
            self.cleaned_data["product_name"]
            .strip()
        )

        exists = Product.objects.filter(
            product_name__iexact=product_name,
            is_deleted=False,
        ).exclude(
            pk=self.instance.pk
        ).exists()

        if exists:

            raise forms.ValidationError(
                "Product already exists."
            )

        return product_name