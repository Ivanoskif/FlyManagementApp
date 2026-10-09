from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.core.exceptions import ValidationError
from django.utils import timezone

from flights.models import Flight, FlightFare, FlightCrewAssignment
from core.models import Airline, Airport, Aircraft, CrewMember



class FlightForm(forms.ModelForm):
    class Meta:
        model = Flight
        fields = [
            "flight_number",
            "airline",
            "origin",
            "destination",
            "scheduled_departure",
            "scheduled_arrival",
            # "status",
            "aircraft",
            "base_price",
            "notes",
        ]
        widgets = {
            "flight_number": forms.TextInput(attrs={"class": "form-control", "style": "text-transform:uppercase"}),
            "airline": forms.Select(attrs={"class": "form-select"}),
            "origin": forms.Select(attrs={"class": "form-select"}),
            "destination": forms.Select(attrs={"class": "form-select"}),
            "scheduled_departure": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "scheduled_arrival": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            # "status": forms.Select(attrs={"class": "form-select"}),
            "aircraft": forms.Select(attrs={"class": "form-select"}),
            "base_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["airline"].queryset = Airline.objects.filter(is_active=True).order_by("name")
        self.fields["origin"].queryset = Airport.objects.filter(is_active=True).order_by("city", "iata_code")
        self.fields["destination"].queryset = Airport.objects.filter(is_active=True).order_by("city", "iata_code")
        self.fields["aircraft"].queryset = Aircraft.objects.exclude(status=Aircraft.Status.OUT_OF_SERVICE).order_by("registration_code")

        for f in ["scheduled_departure", "scheduled_arrival"]:
            if self.instance and getattr(self.instance, f, None):
                dt = timezone.localtime(getattr(self.instance, f))
                self.initial[f] = dt.strftime("%Y-%m-%dT%H:%M")

        if not self.instance or not self.instance.pk:
            self.initial.setdefault("scheduled_departure", timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M"))
            self.initial.setdefault("scheduled_arrival", timezone.localtime(timezone.now() + timezone.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"))

    def clean_flight_number(self):
        v = (self.cleaned_data.get("flight_number") or "").strip().upper()
        if not v:
            raise forms.ValidationError("Flight number is required.")
        return v

    def clean(self):
        cleaned = super().clean()
        origin = cleaned.get("origin")
        destination = cleaned.get("destination")
        dep = cleaned.get("scheduled_departure")
        arr = cleaned.get("scheduled_arrival")

        if origin and destination and origin == destination:
            raise forms.ValidationError("Origin and destination cannot be the same.")

        if dep and arr and dep >= arr:
            raise forms.ValidationError("Scheduled departure must be before scheduled arrival.")

        return cleaned


class BaseFlightFareInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        seen = set()
        total_alloc = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue

            fare_class = form.cleaned_data.get("fare_class")
            price = form.cleaned_data.get("price")
            seats_alloc = form.cleaned_data.get("seats_allocated")
            seats_sold = form.cleaned_data.get("seats_sold")

            if not fare_class and not price and not seats_alloc and not seats_sold:
                continue

            if not fare_class:
                raise ValidationError("Each fare row must have a fare class.")

            if fare_class.id in seen:
                raise ValidationError("Duplicate fare class rows are not allowed.")
            seen.add(fare_class.id)

            if price is None or price < 0:
                raise ValidationError("Fare price must be >= 0.")

            if seats_alloc is None or seats_alloc <= 0:
                raise ValidationError("Seats allocated must be > 0.")

            if seats_sold is None or seats_sold < 0:
                raise ValidationError("Seats sold must be >= 0.")

            if seats_sold > seats_alloc:
                raise ValidationError("Seats sold cannot exceed seats allocated.")

            total_alloc += seats_alloc

        flight = getattr(self, "instance", None)
        if flight and getattr(flight, "aircraft_id", None):
            cap = flight.aircraft.model.default_total_seats
            if total_alloc > cap:
                raise ValidationError(
                    f"Total seats allocated ({total_alloc}) exceeds aircraft capacity ({cap})."
                )


FlightFareFormSet = inlineformset_factory(
    parent_model=Flight,
    model=FlightFare,
    fields=["fare_class", "price", "seats_allocated", "seats_sold"],
    extra=0,
    can_delete=True,
    formset=BaseFlightFareInlineFormSet,
    widgets={
        "fare_class": forms.Select(attrs={"class": "form-select"}),
        "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
        "seats_allocated": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        "seats_sold": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
    },
)


class AssignCrewForm(forms.Form):
    crew_member = forms.ModelChoiceField(
        queryset=CrewMember.objects.filter(status=CrewMember.Status.ACTIVE).order_by("last_name", "first_name"),
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Select crew member...",
        required=True,
    )
    duty = forms.ChoiceField(
        choices=FlightCrewAssignment.Duty.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        required=True,
    )