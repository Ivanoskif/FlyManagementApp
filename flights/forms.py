from django import forms
from django.utils import timezone
from core.models import Airport
from flights.models import FareClass, Flight


class FlightSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "City / Country / IATA (e.g. Skopje, MK, SKP, London, LHR)"
        }),
    )
    origin = forms.ModelChoiceField(
        queryset=Airport.objects.filter(is_active=True).order_by("city", "iata_code"),
        required=False,
        empty_label="From (origin airport)",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    destination = forms.ModelChoiceField(
        queryset=Airport.objects.filter(is_active=True).order_by("city", "iata_code"),
        required=False,
        empty_label="To (destination airport)",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    passengers = forms.IntegerField(
        required=False,
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    fare_class = forms.ModelChoiceField(
        queryset=FareClass.objects.filter(is_active=True).order_by("code"),
        required=False,
        empty_label="Any class",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

class FlightDelayForm(forms.Form):
    delay_minutes = forms.IntegerField(min_value=1, max_value=24*60, help_text="Delay in minutes (1 - 1440).")


class FlightRescheduleForm(forms.Form):
    new_departure = forms.DateTimeField(
        help_text="New departure datetime (UTC).",
        initial=timezone.now
    )


class FlightCancelForm(forms.Form):
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

class FlightStatusForm(forms.Form):
    new_status = forms.ChoiceField(choices=Flight.Status.choices)
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

