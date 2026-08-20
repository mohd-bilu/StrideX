from django import forms
from django.utils import timezone

from .models import Coupon


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
                    "placeholder": "E.G. SAVE20",
                    "autocomplete": "off",
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
                    "placeholder": "e.g. 20",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "minimum_purchase": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "maximum_discount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.00",
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
                    "placeholder": "e.g. 100",
                    "min": "1",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-switch-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["code"].label = "Coupon Code"
        self.fields["discount_type"].label = "Discount Type"
        self.fields["discount_value"].label = "Discount Value"
        self.fields["minimum_purchase"].label = "Minimum Order Amount"
        self.fields["maximum_discount"].label = "Maximum Discount Amount"
        self.fields["start_date"].label = "Valid From"
        self.fields["expiry_date"].label = "Valid To"
        self.fields["usage_limit"].label = "Usage Limit"
        self.fields["is_active"].label = "Active"

        self.fields["usage_limit"].required = True
        self.fields["minimum_purchase"].required = False
        self.fields["maximum_discount"].required = False

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
        code = self.cleaned_data.get("code")

        if not code:
            raise forms.ValidationError(
                "Coupon code is required."
            )

        code = code.strip().upper()

        queryset = Coupon.objects.filter(
            code__iexact=code
        )

        if self.instance and self.instance.pk:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():
            raise forms.ValidationError(
                "A coupon with this code already exists."
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
                "Discount value must be greater than zero."
            )

        if discount_type == "PERCENTAGE":
            if discount_value > 100:
                raise forms.ValidationError(
                    "Percentage discount cannot exceed 100%."
                )

        return discount_value

    def clean_minimum_purchase(self):
        minimum_purchase = self.cleaned_data.get(
            "minimum_purchase"
        )

        if minimum_purchase is None:
            return 0

        if minimum_purchase < 0:
            raise forms.ValidationError(
                "Minimum order amount cannot be negative."
            )

        return minimum_purchase

    def clean_maximum_discount(self):
        maximum_discount = self.cleaned_data.get(
            "maximum_discount"
        )

        if maximum_discount is None:
            return None

        if maximum_discount <= 0:
            raise forms.ValidationError(
                "Maximum discount must be greater than zero."
            )

        return maximum_discount

    def clean_usage_limit(self):
        usage_limit = self.cleaned_data.get(
            "usage_limit"
        )

        if usage_limit is None:
            raise forms.ValidationError(
                "Usage limit is required."
            )

        if usage_limit <= 0:
            raise forms.ValidationError(
                "Usage limit must be greater than zero."
            )

        if (
            self.instance
            and self.instance.pk
            and usage_limit < self.instance.used_count
        ):
            raise forms.ValidationError(
                f"Usage limit cannot be less than "
                f"the number of times this coupon "
                f"has already been used ({self.instance.used_count})."
            )

        return usage_limit

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        expiry_date = cleaned_data.get("expiry_date")
        discount_type = cleaned_data.get("discount_type")
        maximum_discount = cleaned_data.get(
            "maximum_discount"
        )

        if start_date and expiry_date:
            if expiry_date <= start_date:
                self.add_error(
                    "expiry_date",
                    "Valid To must be later than Valid From."
                )

        if start_date and not timezone.is_naive(start_date):
            pass

        if (
            discount_type == "PERCENTAGE"
            and maximum_discount is not None
            and maximum_discount <= 0
        ):
            self.add_error(
                "maximum_discount",
                "Maximum discount must be greater than zero."
            )

        return cleaned_data