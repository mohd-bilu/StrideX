from django import forms

from Admin_panel.category.models import Category

from .models import Product, Variant


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = [
            "category",
            "product_name",
            "description",
            "is_active",
        ]

        widgets = {
            "product_name": forms.TextInput(
                attrs={
                    "placeholder": "Enter product name",
                    "class": "form-control",
                },
            ),
            "category": forms.Select(
                attrs={
                    "class": "form-select",
                },
            ),
            "description": forms.Textarea(
                attrs={
                    "placeholder": "Write product description...",
                    "rows": 6,
                    "class": "form-control",
                },
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "status-switch",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["category"].queryset = Category.objects.filter(
            is_deleted=False,
            is_active=True,
        ).order_by("category_name")

    def clean_product_name(self):
        product_name = self.cleaned_data["product_name"].strip()

        if Product.objects.filter(
            product_name__iexact=product_name,
            is_deleted=False,
        ).exclude(
            pk=self.instance.pk,
        ).exists():

            raise forms.ValidationError(
                "Product already exists."
            )

        return product_name


class VariantForm(forms.ModelForm):

    class Meta:
        model = Variant
        fields = [
            "sku",
            "size",
            "color",
            "price",
            "stock",
            "is_active",
            "is_default",
        ]

        widgets = {
            "sku": forms.TextInput(
                attrs={
                    "placeholder": "Enter SKU",
                    "class": "form-control",
                },
            ),
            "size": forms.TextInput(
                attrs={
                    "placeholder": "Enter size",
                    "class": "form-control",
                },
            ),
            "color": forms.TextInput(
                attrs={
                    "placeholder": "Enter color",
                    "class": "form-control",
                },
            ),
            "price": forms.NumberInput(
                attrs={
                    "placeholder": "Enter price",
                    "class": "form-control",
                    "step": "0.01",
                },
            ),
            "stock": forms.NumberInput(
                attrs={
                    "placeholder": "Enter stock",
                    "class": "form-control",
                },
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "status-switch",
                },
            ),
            "is_default": forms.CheckboxInput(
                attrs={
                    "class": "status-switch",
                },
            ),
        }

    def clean_sku(self):
        sku = self.cleaned_data["sku"].strip().upper()

        if Variant.objects.filter(
            sku__iexact=sku,
        ).exclude(
            pk=self.instance.pk,
        ).exists():

            raise forms.ValidationError(
                "SKU already exists."
            )

        return sku

    def clean_price(self):
        price = self.cleaned_data["price"]

        if price <= 0:
            raise forms.ValidationError(
                "Price must be greater than zero."
            )

        return price

    def clean_stock(self):
        stock = self.cleaned_data["stock"]

        if stock < 0:
            raise forms.ValidationError(
                "Stock cannot be negative."
            )

        return stock