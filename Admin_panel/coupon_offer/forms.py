from django import forms
from django.utils import timezone

from .models import Coupon, Offer


class CouponForm(forms.ModelForm):

    class Meta:
        model = Coupon
        fields = [
            "code",
            "discount_type",
            "discount_value",
            "minimum_purchase",
            "maximum_discount",
            "start_date",
            "expiry_date",
            "usage_limit",
            "is_active",
        ]

        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter coupon code",
                }
            ),
            "discount_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "discount_value": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter discount value",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "minimum_purchase": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter minimum purchase",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "maximum_discount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter maximum discount",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "start_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
            "expiry_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
            "usage_limit": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Leave empty for unlimited",
                    "min": "1",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["maximum_discount"].required = False
        self.fields["usage_limit"].required = False

        if self.instance and self.instance.pk:

            if self.instance.start_date:
                self.initial["start_date"] = (
                    self.instance.start_date.strftime(
                        "%Y-%m-%dT%H:%M"
                    )
                )

            if self.instance.expiry_date:
                self.initial["expiry_date"] = (
                    self.instance.expiry_date.strftime(
                        "%Y-%m-%dT%H:%M"
                    )
                )

    def clean_code(self):
        code = self.cleaned_data.get(
            "code"
        )

        if not code:
            raise forms.ValidationError(
                "Coupon code is required."
            )

        code = code.strip().upper()

        if not code:
            raise forms.ValidationError(
                "Coupon code cannot be empty."
            )

        return code

    def clean_discount_value(self):
        discount_type = self.cleaned_data.get(
            "discount_type"
        )

        discount_value = self.cleaned_data.get(
            "discount_value"
        )

        if discount_value is None:
            raise forms.ValidationError(
                "Discount value is required."
            )

        if discount_value <= 0:
            raise forms.ValidationError(
                "Discount value must be greater than 0."
            )

        if (
            discount_type == "PERCENTAGE"
            and discount_value > 100
        ):
            raise forms.ValidationError(
                "Percentage discount cannot exceed 100%."
            )

        return discount_value

    def clean_maximum_discount(self):
        maximum_discount = self.cleaned_data.get(
            "maximum_discount"
        )

        if (
            maximum_discount is not None
            and maximum_discount <= 0
        ):
            raise forms.ValidationError(
                "Maximum discount must be greater than 0."
            )

        return maximum_discount

    def clean_usage_limit(self):
        usage_limit = self.cleaned_data.get(
            "usage_limit"
        )

        if (
            usage_limit is not None
            and usage_limit <= 0
        ):
            raise forms.ValidationError(
                "Usage limit must be greater than 0."
            )

        return usage_limit

    def clean(self):
        cleaned_data = super().clean()

        discount_type = cleaned_data.get(
            "discount_type"
        )

        discount_value = cleaned_data.get(
            "discount_value"
        )

        maximum_discount = cleaned_data.get(
            "maximum_discount"
        )

        start_date = cleaned_data.get(
            "start_date"
        )

        expiry_date = cleaned_data.get(
            "expiry_date"
        )

        if (
            discount_type == "FIXED"
            and maximum_discount is not None
        ):
            self.add_error(
                "maximum_discount",
                "Maximum discount is only applicable to percentage coupons."
            )

        if (
            discount_type == "PERCENTAGE"
            and discount_value is not None
            and discount_value > 100
        ):
            self.add_error(
                "discount_value",
                "Percentage discount cannot exceed 100%."
            )

        if (
            start_date
            and expiry_date
            and expiry_date <= start_date
        ):
            self.add_error(
                "expiry_date",
                "Expiry date must be after the start date."
            )

        if (
            start_date
            and not self.instance.pk
            and start_date < timezone.now()
        ):
            self.add_error(
                "start_date",
                "Start date cannot be in the past."
            )

        return cleaned_data


class OfferForm(forms.ModelForm):

    class Meta:
        model = Offer
        fields = [
            "name",
            "offer_type",
            "product",
            "category",
            "discount_type",
            "discount_value",
            "start_date",
            "expiry_date",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter offer name",
                }
            ),
            "offer_type": forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "id_offer_type",
                }
            ),
            "product": forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "id_product",
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "id_category",
                }
            ),
            "discount_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "discount_value": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter discount value",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "start_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
            "expiry_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["product"].required = False
        self.fields["category"].required = False

        self.fields["product"].empty_label = (
            "Select Product"
        )

        self.fields["category"].empty_label = (
            "Select Category"
        )

        if self.instance and self.instance.pk:

            if self.instance.start_date:
                self.initial["start_date"] = (
                    self.instance.start_date.strftime(
                        "%Y-%m-%dT%H:%M"
                    )
                )

            if self.instance.expiry_date:
                self.initial["expiry_date"] = (
                    self.instance.expiry_date.strftime(
                        "%Y-%m-%dT%H:%M"
                    )
                )

    def clean_name(self):
        name = self.cleaned_data.get(
            "name"
        )

        if not name:
            raise forms.ValidationError(
                "Offer name is required."
            )

        name = name.strip()

        if not name:
            raise forms.ValidationError(
                "Offer name cannot be empty."
            )

        return name

    def clean_discount_value(self):
        discount_type = self.cleaned_data.get(
            "discount_type"
        )

        discount_value = self.cleaned_data.get(
            "discount_value"
        )

        if discount_value is None:
            raise forms.ValidationError(
                "Discount value is required."
            )

        if discount_value <= 0:
            raise forms.ValidationError(
                "Discount value must be greater than 0."
            )

        if (
            discount_type == "PERCENTAGE"
            and discount_value > 100
        ):
            raise forms.ValidationError(
                "Percentage discount cannot exceed 100%."
            )

        return discount_value

    def clean(self):
        cleaned_data = super().clean()

        offer_type = cleaned_data.get(
            "offer_type"
        )

        product = cleaned_data.get(
            "product"
        )

        category = cleaned_data.get(
            "category"
        )

        start_date = cleaned_data.get(
            "start_date"
        )

        expiry_date = cleaned_data.get(
            "expiry_date"
        )

        if offer_type == "PRODUCT":

            if not product:
                self.add_error(
                    "product",
                    "Please select a product."
                )

            cleaned_data["category"] = None

        elif offer_type == "CATEGORY":

            if not category:
                self.add_error(
                    "category",
                    "Please select a category."
                )

            cleaned_data["product"] = None

        if (
            start_date
            and expiry_date
            and expiry_date <= start_date
        ):
            self.add_error(
                "expiry_date",
                "Expiry date must be after the start date."
            )

        if (
            start_date
            and not self.instance.pk
            and start_date < timezone.now()
        ):
            self.add_error(
                "start_date",
                "Start date cannot be in the past."
            )

        return cleaned_data