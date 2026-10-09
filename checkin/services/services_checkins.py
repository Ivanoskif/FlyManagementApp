from __future__ import annotations
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from bookings.models import Booking, BookingPassenger
from bookings.services.services_seats import auto_assign_missing_seats_for_booking


@transaction.atomic
def check_in_passengers(*, booking_id: int, user_id: int, passenger_ids: list[int]) -> None:
    booking = (
        Booking.objects.select_for_update()
        .select_related("flight", "user")
        .prefetch_related("passengers")
        .get(id=booking_id, user_id=user_id)
    )

    if booking.status != Booking.Status.PAID:
        raise ValidationError("Check-in is allowed only for PAID bookings.")

    if booking.flight.status == booking.flight.Status.CANCELLED:
        raise ValidationError("Cannot check-in for a cancelled flight.")

    if not passenger_ids:
        raise ValidationError("Select at least one passenger to check-in.")

    passengers = list(
        BookingPassenger.objects.select_for_update()
        .filter(booking_id=booking.id, id__in=passenger_ids)
        .order_by("id")
    )
    if len(passengers) != len(set(passenger_ids)):
        raise ValidationError("Some selected passengers are invalid for this booking.")

    if any(p.aircraft_seat_id is None for p in passengers):
        auto_assign_missing_seats_for_booking(booking_id=booking.id)

        passengers = list(
            BookingPassenger.objects.select_for_update()
            .filter(booking_id=booking.id, id__in=passenger_ids)
            .order_by("id")
        )

    if any(p.aircraft_seat_id is None for p in passengers):
        raise ValidationError("Aircraft missing or no free seats")

    now = timezone.now()
    for p in passengers:
        if p.checked_in:
            continue
        p.checked_in = True
        p.checked_in_at = now
        p.save(update_fields=["checked_in", "checked_in_at"])
