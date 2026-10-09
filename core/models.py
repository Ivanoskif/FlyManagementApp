from django.db import models
from django.core.exceptions import ValidationError

# Create your models here.
class Airline(models.Model):
    name = models.CharField(max_length=200, unique=True)
    iata_code = models.CharField(max_length=2, blank=True, null=True, unique=True)
    icao_code = models.CharField(max_length=3, blank=True, null=True, unique=True)
    callsign = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        code = self.iata_code or self.icao_code
        return f"{self.name} ({code})" if code else self.name


class Airport(models.Model):
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=120)
    country = models.CharField(max_length=120)

    iata_code = models.CharField(max_length=3, unique=True)
    icao_code = models.CharField(max_length=4, blank=True, null=True)

    timezone = models.CharField(max_length=64, default="UTC")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    is_active = models.BooleanField(default=True)

    # image = models.ImageField(upload_to="airports/", blank=True, null=True)

    class Meta:
        ordering = ["country", "city", "iata_code"]
        indexes = [
            models.Index(fields=["city"]),
            models.Index(fields=["country"]),
        ]

    def __str__(self) -> str:
        return f"{self.iata_code} - {self.city}, {self.country}"




class AircraftModel(models.Model):
    manufacturer = models.CharField(max_length=120)
    model_name = models.CharField(max_length=120)
    default_total_seats = models.PositiveIntegerField()

    economy_seats = models.PositiveIntegerField(blank=True, null=True)
    premium_seats = models.PositiveIntegerField(blank=True, null=True)
    business_seats = models.PositiveIntegerField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("manufacturer", "model_name")]
        ordering = ["manufacturer", "model_name"]

    def __str__(self) -> str:
        return f"{self.manufacturer} {self.model_name}"

class AircraftSeat(models.Model):
    class SeatType(models.TextChoices):
        WINDOW = "WINDOW", "Window"
        AISLE = "AISLE", "Aisle"
        MIDDLE = "MIDDLE", "Middle"

    aircraft_model = models.ForeignKey(
        "core.AircraftModel",
        on_delete=models.CASCADE,
        related_name="seats",
    )

    seat_code = models.CharField(max_length=5)
    row_number = models.PositiveIntegerField()
    seat_letter = models.CharField(max_length=1)

    seat_type = models.CharField(max_length=10, choices=SeatType.choices)
    is_extra_legroom = models.BooleanField(default=False)

    class Meta:
        unique_together = [("aircraft_model", "seat_code")]
        ordering = ["aircraft_model_id", "row_number", "seat_letter"]
        indexes = [
            models.Index(fields=["aircraft_model"]),
            models.Index(fields=["row_number"]),
            models.Index(fields=["seat_letter"]),
            models.Index(fields=["is_extra_legroom"]),
        ]

    def clean(self):
        if len(self.seat_letter or "") != 1:
            raise ValidationError("seat_letter must be 1 character (e.g., A).")
        if self.row_number <= 0:
            raise ValidationError("row_number must be >= 1.")

        code = f"{self.row_number}{self.seat_letter}"
        if self.seat_code != code:
            self.seat_code = code

    def save(self, *args, **kwargs):
        # normalize seat_code
        self.seat_code = f"{self.row_number}{self.seat_letter}"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        extra = " (XL)" if self.is_extra_legroom else ""
        return f"{self.aircraft_model} - {self.seat_code}{extra}"

class Aircraft(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        OUT_OF_SERVICE = "OUT_OF_SERVICE", "Out of service"

    airline = models.ForeignKey("core.Airline", on_delete=models.PROTECT, related_name="aircraft")
    model = models.ForeignKey("core.AircraftModel", on_delete=models.PROTECT, related_name="aircraft")

    registration_code = models.CharField(max_length=16, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    in_service_since = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["registration_code"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["airline"]),
        ]

    def __str__(self) -> str:
        return f"{self.registration_code} ({self.model})"

class CrewMember(models.Model):
    class Role(models.TextChoices):
        PILOT_CAPTAIN = "PILOT_CAPTAIN", "Pilot - Captain"
        PILOT_FIRST_OFFICER = "PILOT_FIRST_OFFICER", "Pilot - First Officer"
        CABIN_CREW = "CABIN_CREW", "Cabin Crew"
        ENGINEER = "ENGINEER", "Engineer"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    airline = models.ForeignKey("core.Airline", on_delete=models.PROTECT, related_name="crew_members", blank=True,
                                null=True)

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)

    role = models.CharField(max_length=25, choices=Role.choices)
    license_no = models.CharField(max_length=60, blank=True, null=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} - {self.role}"


class Route(models.Model):
    airline = models.ForeignKey("core.Airline", on_delete=models.PROTECT, related_name="routes")
    origin = models.ForeignKey("core.Airport", on_delete=models.PROTECT, related_name="routes_from")
    destination = models.ForeignKey("core.Airport", on_delete=models.PROTECT, related_name="routes_to")

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("airline", "origin", "destination")]
        indexes = [
            models.Index(fields=["origin", "destination"]),
            models.Index(fields=["airline"]),
        ]

    def __str__(self) -> str:
        return f"{self.airline} {self.origin.iata_code}->{self.destination.iata_code}"

class CityImage(models.Model):
    city = models.CharField(max_length=120)
    country = models.CharField(max_length=120, blank=True, null=True)

    image = models.ImageField(upload_to="cities/", blank=True, null=True)

    no_image_found = models.BooleanField(default=False)

    class Meta:
        unique_together = [("city", "country")]
        indexes = [
            models.Index(fields=["city"]),
            models.Index(fields=["country"]),
        ]

    def __str__(self):
        return f"{self.city}, {self.country}" if self.country else self.city