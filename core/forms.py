from django import forms
from core.models import Airport


class RouteSearchForm(forms.Form):
    airline_q = forms.CharField(
        required=False,
        label="Airline search",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Airline (e.g. Air France, AF, AFR)"
        }),
    )

    from_q = forms.CharField(
        required=False,
        label="From search",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "From: city / country / IATA (e.g. Skopje, MK, SKP)"
        }),
    )
    to_q = forms.CharField(
        required=False,
        label="To search",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "To: city / country / IATA (e.g. London, UK, LHR)"
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
