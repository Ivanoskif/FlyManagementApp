from django import forms
from core.models import Airport, Airline, AircraftModel, Aircraft, CrewMember, Route

class AirportForm(forms.ModelForm):
    class Meta:
        model = Airport
        fields = [
            "name",
            "city",
            "country",
            "iata_code",
            "icao_code",
            "timezone",
            "latitude",
            "longitude",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "iata_code": forms.TextInput(attrs={"class": "form-control", "style": "text-transform:uppercase"}),
            "icao_code": forms.TextInput(attrs={"class": "form-control", "style": "text-transform:uppercase"}),
            "timezone": forms.TextInput(attrs={"class": "form-control"}),
            "latitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_iata_code(self):
        code = (self.cleaned_data.get("iata_code") or "").strip().upper()
        if len(code) != 3:
            raise forms.ValidationError("IATA code must be exactly 3 characters.")
        return code

    def clean_icao_code(self):
        code = (self.cleaned_data.get("icao_code") or "").strip().upper()
        if code and len(code) != 4:
            raise forms.ValidationError("ICAO code must be exactly 4 characters.")
        return code

class AirlineForm(forms.ModelForm):
    class Meta:
        model = Airline
        fields = [
            "name",
            "iata_code",
            "icao_code",
            "callsign",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "iata_code": forms.TextInput(attrs={"class": "form-control", "style": "text-transform:uppercase"}),
            "icao_code": forms.TextInput(attrs={"class": "form-control", "style": "text-transform:uppercase"}),
            "callsign": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_iata_code(self):
        code = (self.cleaned_data.get("iata_code") or "").strip().upper()
        if code and len(code) != 2:
            raise forms.ValidationError("IATA code must be exactly 2 characters.")
        return code or None

    def clean_icao_code(self):
        code = (self.cleaned_data.get("icao_code") or "").strip().upper()
        if code and len(code) != 3:
            raise forms.ValidationError("ICAO code must be exactly 3 characters.")
        return code or None

class AircraftModelForm(forms.ModelForm):
    class Meta:
        model = AircraftModel
        fields = [
            "manufacturer",
            "model_name",
            "default_total_seats",
            "economy_seats",
            "premium_seats",
            "business_seats",
            "is_active",
        ]
        widgets = {
            "manufacturer": forms.TextInput(attrs={"class": "form-control"}),
            "model_name": forms.TextInput(attrs={"class": "form-control"}),
            "default_total_seats": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "economy_seats": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "premium_seats": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "business_seats": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned = super().clean()

        total = cleaned.get("default_total_seats")
        econ = cleaned.get("economy_seats")
        prem = cleaned.get("premium_seats")
        bus = cleaned.get("business_seats")

        split_vals = [v for v in [econ, prem, bus] if v is not None]
        if split_vals:
            split_sum = (econ or 0) + (prem or 0) + (bus or 0)
            if total and split_sum > total:
                raise forms.ValidationError(
                    "Sum of economy/premium/business seats cannot exceed default_total_seats."
                )

        manu = (cleaned.get("manufacturer") or "").strip()
        name = (cleaned.get("model_name") or "").strip()
        cleaned["manufacturer"] = manu
        cleaned["model_name"] = name
        return cleaned

class AircraftForm(forms.ModelForm):
    class Meta:
        model = Aircraft
        fields = [
            "airline",
            "model",
            "registration_code",
            "status",
            "in_service_since",
            "notes",
        ]
        widgets = {
            "airline": forms.Select(attrs={"class": "form-select"}),
            "model": forms.Select(attrs={"class": "form-select"}),
            "registration_code": forms.TextInput(attrs={"class": "form-control", "style": "text-transform:uppercase"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "in_service_since": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["airline"].queryset = self.fields["airline"].queryset.filter(is_active=True).order_by("name")
        self.fields["model"].queryset = self.fields["model"].queryset.filter(is_active=True).order_by("manufacturer", "model_name")

    def clean_registration_code(self):
        code = (self.cleaned_data.get("registration_code") or "").strip().upper()
        if not code:
            raise forms.ValidationError("Registration code is required.")
        return code


class CrewMemberForm(forms.ModelForm):
    class Meta:
        model = CrewMember
        fields = [
            "airline",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "license_no",
            "status",
        ]
        widgets = {
            "airline": forms.Select(attrs={"class": "form-select"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-select"}),
            "license_no": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["airline"].queryset = self.fields["airline"].queryset.filter(is_active=True).order_by("name")
        self.fields["airline"].required = False

    def clean_first_name(self):
        v = (self.cleaned_data.get("first_name") or "").strip()
        if not v:
            raise forms.ValidationError("First name is required.")
        return v

    def clean_last_name(self):
        v = (self.cleaned_data.get("last_name") or "").strip()
        if not v:
            raise forms.ValidationError("Last name is required.")
        return v

    def clean_license_no(self):
        role = self.cleaned_data.get("role")
        lic = (self.cleaned_data.get("license_no") or "").strip()

        is_pilot = role in [CrewMember.Role.PILOT_CAPTAIN, CrewMember.Role.PILOT_FIRST_OFFICER]
        if is_pilot and not lic:
            raise forms.ValidationError("license_no is required for pilots.")
        return lic or None

class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ["airline", "origin", "destination", "is_active"]
        widgets = {
            "airline": forms.Select(attrs={"class": "form-select"}),
            "origin": forms.Select(attrs={"class": "form-select"}),
            "destination": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["airline"].queryset = self.fields["airline"].queryset.filter(is_active=True).order_by("name")
        self.fields["origin"].queryset = self.fields["origin"].queryset.filter(is_active=True).order_by("city", "iata_code")
        self.fields["destination"].queryset = self.fields["destination"].queryset.filter(is_active=True).order_by("city", "iata_code")

    def clean(self):
        cleaned = super().clean()
        origin = cleaned.get("origin")
        destination = cleaned.get("destination")
        if origin and destination and origin == destination:
            raise forms.ValidationError("Origin and destination cannot be the same airport.")
        return cleaned
