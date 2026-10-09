from django.db import models
import secrets
import string
from django.conf import settings
from django.core.exceptions import ValidationError

# Create your models here.

def generate_booking_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_ticket_number(length: int = 13) -> str:
    # Simple unique-ish number; will still be enforced by unique constraint
    alphabet = string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Booking(models.Model):
    class Status(models.TextChoices):
        RESERVED = "RESERVED", "Reserved"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"
        REFUNDED = "REFUNDED", "Refunded"

    booking_code = models.CharField(max_length=10, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    flight = models.ForeignKey(
        "flights.Flight",
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    fare_class = models.ForeignKey(
        "flights.FareClass",
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    flight_fare = models.ForeignKey(
        "flights.FlightFare",
        on_delete=models.PROTECT,
        related_name="bookings",
        blank=True,
        null=True,
    )

    passengers_count = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RESERVED)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="EUR")

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    reserved_email_sent = models.BooleanField(default=False)
    paid_email_sent = models.BooleanField(default=False)

    base_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["booking_code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def clean(self):
        if self.passengers_count <= 0:
            raise ValidationError("passengers_count must be >= 1.")

    def save(self, *args, **kwargs):
        if not self.booking_code:
            for _ in range(10):
                code = generate_booking_code()
                if not Booking.objects.filter(booking_code=code).exists():
                    self.booking_code = code
                    break
            if not self.booking_code:
                raise RuntimeError("Could not generate unique booking_code.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.booking_code} - {self.flight.flight_number} ({self.status})"


class BookingPassenger(models.Model):
    class DocumentType(models.TextChoices):
        PASSPORT = "PASSPORT", "Passport"
        ID = "ID", "ID Card"

    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="passengers",
    )

    aircraft_seat = models.ForeignKey(
        "core.AircraftSeat",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking_passengers",
    )

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    date_of_birth = models.DateField()
    nationality = models.CharField(max_length=80, blank=True, null=True)

    document_type = models.CharField(max_length=10, choices=DocumentType.choices, default=DocumentType.PASSPORT)
    document_no = models.CharField(max_length=50)

    seat_no = models.CharField(max_length=8, blank=True, null=True)
    special_requests = models.TextField(blank=True, null=True)

    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["document_no"]),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.booking.booking_code})"


class Payment(models.Model):
    class Method(models.TextChoices):
        CARD = "CARD", "Card"
        CASH = "CASH", "Cash"
        ONLINE = "ONLINE", "Online"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.CARD)
    provider_ref = models.CharField(max_length=120, blank=True, null=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"Payment {self.id} - {self.booking.booking_code} ({self.status})"


class Refund(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        COMPLETED = "COMPLETED", "Completed"

    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="refunds",
    )
    payment = models.ForeignKey(
        "bookings.Payment",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="refunds",
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.REQUESTED)
    refunded_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"Refund {self.id} - {self.booking.booking_code} ({self.status})"


class Ticket(models.Model):
    class Status(models.TextChoices):
        ISSUED = "ISSUED", "Issued"
        VOID = "VOID", "Void"
        REFUNDED = "REFUNDED", "Refunded"

    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="ticket",
    )
    ticket_number = models.CharField(max_length=20, unique=True, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ISSUED)

    class Meta:
        ordering = ["-issued_at"]

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            for _ in range(10):
                tn = generate_ticket_number()
                if not Ticket.objects.filter(ticket_number=tn).exists():
                    self.ticket_number = tn
                    break
            if not self.ticket_number:
                raise RuntimeError("Could not generate unique ticket_number.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.ticket_number} ({self.booking.booking_code})"
