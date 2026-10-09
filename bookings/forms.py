from django import forms
from django.forms import modelformset_factory
from bookings.models import BookingPassenger
from flights.models import FareClass


class BookingCreateForm(forms.Form):
    fare_class = forms.ModelChoiceField(
        queryset=FareClass.objects.filter(is_active=True).order_by("code"),
        widget=forms.Select(attrs={"class": "form-select"}),
        required=True,
    )
    passengers_count = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        required=True,
    )


class BookingPassengerForm(forms.ModelForm):
    class Meta:
        model = BookingPassenger
        fields = [
            "first_name",
            "last_name",
            "date_of_birth",
            "nationality",
            "document_type",
            "document_no",
            "special_requests",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "nationality": forms.TextInput(attrs={"class": "form-control"}),
            "document_type": forms.Select(attrs={"class": "form-select"}),
            "document_no": forms.TextInput(attrs={"class": "form-control"}),
            "special_requests": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


PassengerFormSet = modelformset_factory(
    BookingPassenger,
    form=BookingPassengerForm,
    extra=0,
    can_delete=False,
)

class RefundRequestForm(forms.Form):
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        help_text="Optional: describe the reason for the refund request.",
    )

class DemoPaymentForm(forms.Form):
    card_holder = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"class": "form-control"}))
    card_number = forms.CharField(max_length=19, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "4111 1111 1111 1111"}))
    exp_month = forms.IntegerField(min_value=1, max_value=12, widget=forms.NumberInput(attrs={"class": "form-control"}))
    exp_year = forms.IntegerField(min_value=2025, max_value=2100, widget=forms.NumberInput(attrs={"class": "form-control"}))
    cvc = forms.CharField(max_length=4, widget=forms.PasswordInput(attrs={"class": "form-control"}))

    def clean_card_number(self):
        raw = self.cleaned_data["card_number"]
        digits = "".join(ch for ch in raw if ch.isdigit())
        if len(digits) < 13 or len(digits) > 19:
            raise forms.ValidationError("Invalid card number length.")
        return digits