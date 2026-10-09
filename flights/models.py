from django.db import models
from django.core.exceptions import ValidationError

# Create your models here.



class FareClass(models.Model):
    class RefundPolicy(models.TextChoices):
        FLEX = "FLEX", "Flexible"
        PARTIAL = "PARTIAL", "Partial"
        NON_REFUNDABLE = "NON_REFUNDABLE", "Non-refundable"

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=80)
    refund_policy = models.CharField(
        max_length=20, choices=RefundPolicy.choices, default=RefundPolicy.PARTIAL
    )
    baggage_info = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Flight(models.Model):
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        BOARDING = "BOARDING", "Boarding"
        IN_FLIGHT = "IN_FLIGHT", "In flight"
        LANDED = "LANDED", "Landed"
        DELAYED = "DELAYED", "Delayed"
        CANCELLED = "CANCELLED", "Cancelled"

    flight_number = models.CharField(max_length=12)

    airline = models.ForeignKey("core.Airline", on_delete=models.PROTECT, related_name="flights")
    origin = models.ForeignKey("core.Airport", on_delete=models.PROTECT, related_name="departing_flights")
    destination = models.ForeignKey("core.Airport", on_delete=models.PROTECT, related_name="arriving_flights")

    scheduled_departure = models.DateTimeField()
    scheduled_arrival = models.DateTimeField()
    actual_departure = models.DateTimeField(blank=True, null=True)
    actual_arrival = models.DateTimeField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)

    aircraft = models.ForeignKey(
        "core.Aircraft",
        on_delete=models.PROTECT,
        related_name="flights",
        blank=True,
        null=True,
    )

    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-scheduled_departure"]
        indexes = [
            models.Index(fields=["flight_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["scheduled_departure"]),
            models.Index(fields=["airline"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(origin=models.F("destination")),
                name="flight_origin_not_destination",
            ),
        ]

    def clean(self):
        if self.scheduled_departure and self.scheduled_arrival:
            if self.scheduled_departure >= self.scheduled_arrival:
                raise ValidationError("Scheduled departure must be before scheduled arrival.")

    def __str__(self) -> str:
        return f"{self.flight_number} {self.origin.iata_code}->{self.destination.iata_code}"


class FlightFare(models.Model):
    flight = models.ForeignKey("flights.Flight", on_delete=models.CASCADE, related_name="fares")
    fare_class = models.ForeignKey("flights.FareClass", on_delete=models.PROTECT, related_name="flight_fares")

    price = models.DecimalField(max_digits=10, decimal_places=2)
    seats_allocated = models.PositiveIntegerField()
    seats_sold = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("flight", "fare_class")]
        indexes = [
            models.Index(fields=["flight"]),
            models.Index(fields=["fare_class"]),
        ]

    def clean(self):
        if self.seats_sold > self.seats_allocated:
            raise ValidationError("seats_sold cannot exceed seats_allocated.")

    def __str__(self) -> str:
        return f"{self.flight.flight_number} - {self.fare_class.code} ({self.price})"


class FlightCrewAssignment(models.Model):
    class Duty(models.TextChoices):
        CAPTAIN = "CAPTAIN", "Captain"
        FIRST_OFFICER = "FIRST_OFFICER", "First Officer"
        CABIN = "CABIN", "Cabin Crew"
        ENGINEER = "ENGINEER", "Engineer"
        OTHER = "OTHER", "Other"

    flight = models.ForeignKey("flights.Flight", on_delete=models.CASCADE, related_name="crew_assignments")
    crew_member = models.ForeignKey("core.CrewMember", on_delete=models.PROTECT, related_name="flight_assignments")

    duty = models.CharField(max_length=20, choices=Duty.choices)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("flight", "crew_member")]
        indexes = [
            models.Index(fields=["flight"]),
            models.Index(fields=["crew_member"]),
        ]

    def __str__(self) -> str:
        return f"{self.flight.flight_number} - {self.crew_member} ({self.duty})"
