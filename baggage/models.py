from django.db import models
from decimal import Decimal
from accounts.models import PassengerProfile

# Create your models here.

class BaggageType(models.TextChoices):
    PERSONAL = "PERSONAL", "Personal item"
    CABIN = "CABIN", "Cabin / carry-on"
    CHECKED = "CHECKED", "Checked baggage"


class BaggageRule(models.Model):
    membership_level = models.CharField(
        max_length=10,
        choices=PassengerProfile.MembershipLevel.choices,
        db_index=True,
    )

    baggage_type = models.CharField(max_length=10, choices=BaggageType.choices, db_index=True)

    included_pieces = models.PositiveIntegerField(default=0)

    max_weight_kg_per_piece = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    max_linear_cm = models.PositiveIntegerField(default=0)

    price_eur = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    max_additional_pieces = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("membership_level", "baggage_type")]
        ordering = ["membership_level", "baggage_type"]

    def __str__(self) -> str:
        return f"{self.membership_level} - {self.baggage_type}"


class BookingPassengerBaggage(models.Model):
    booking_passenger = models.ForeignKey(
        "bookings.BookingPassenger",
        on_delete=models.CASCADE,
        related_name="baggage_items",
    )

    baggage_type = models.CharField(max_length=10, choices=BaggageType.choices)
    pieces = models.PositiveIntegerField(default=1)

    max_weight_kg_per_piece = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    max_linear_cm = models.PositiveIntegerField(default=0)

    is_included = models.BooleanField(default=False)
    price_eur = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["baggage_type"]),
            models.Index(fields=["is_included"]),
        ]

    def __str__(self) -> str:
        flag = "included" if self.is_included else "addon"
        return f"{self.booking_passenger_id} {self.baggage_type} x{self.pieces} ({flag})"
