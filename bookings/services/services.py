from __future__ import annotations
from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from bookings.models import Booking, BookingPassenger
from flights.models import FlightFare
from bookings.services.services_emails import send_booking_reserved_email


DEFAULT_HOLD_MINUTES = 30

@transaction.atomic
def create_booking_reserved(*, user, flight_id: int, fare_class_id: int, passengers_count: int) -> Booking:

    if passengers_count <= 0:
        raise ValidationError("Passengers count must be at least 1.")

    flight_fare = (
        FlightFare.objects.select_for_update()
        .select_related("flight", "fare_class")
        .get(flight_id=flight_id, fare_class_id=fare_class_id)
    )

    available = flight_fare.seats_allocated - flight_fare.seats_sold
    if passengers_count > available:
        raise ValidationError(f"Not enough seats. Available: {available}.")

    flight_fare.seats_sold += passengers_count
    flight_fare.full_clean()
    flight_fare.save(update_fields=["seats_sold"])

    total_amount = (Decimal(passengers_count) * flight_fare.price).quantize(Decimal("0.01"))


    booking = Booking.objects.create(
        user=user,
        flight=flight_fare.flight,
        fare_class=flight_fare.fare_class,
        flight_fare=flight_fare,
        passengers_count=passengers_count,
        status=Booking.Status.RESERVED,
        total_amount=total_amount,
        base_amount = total_amount,
        currency="EUR",
        expires_at=timezone.now() + timedelta(minutes=DEFAULT_HOLD_MINUTES),
    )
    return booking

@transaction.atomic
def create_booking_with_passengers_reserved(
    *,
    user,
    flight_id: int,
    fare_class_id: int,
    passengers: list[dict],
) -> Booking:

    if not passengers:
        raise ValidationError("At least 1 passenger is required.")

    booking = create_booking_reserved(
        user=user,
        flight_id=flight_id,
        fare_class_id=fare_class_id,
        passengers_count=len(passengers),
    )

    objs: list[BookingPassenger] = []
    for p in passengers:
        if not p.get("first_name") or not p.get("last_name") or not p.get("date_of_birth") or not p.get("document_no"):
            raise ValidationError("Passenger data is incomplete.")

        objs.append(
            BookingPassenger(
                booking=booking,
                first_name=p["first_name"],
                last_name=p["last_name"],
                date_of_birth=p["date_of_birth"],
                nationality=p.get("nationality"),
                document_type=p.get("document_type") or BookingPassenger.DocumentType.PASSPORT,
                document_no=p["document_no"],
            )
        )

    BookingPassenger.objects.bulk_create(objs)

    if hasattr(booking, "_prefetched_objects_cache"):
        booking._prefetched_objects_cache = {}

    send_booking_reserved_email(booking)

    return booking



@transaction.atomic
def cancel_booking(*, booking_id: int, by_user=None) -> Booking:
    booking = (
        Booking.objects.select_for_update()
        .select_related("flight_fare", "flight_fare__flight")
        .get(id=booking_id)
    )

    if booking.status == Booking.Status.CANCELLED:
        return booking

    if booking.status == Booking.Status.PAID:
        raise ValidationError("Paid booking cannot be cancelled directly. Use refund process.")

    if booking.status == Booking.Status.REFUNDED:
        raise ValidationError("Booking already refunded.")

    if booking.status == Booking.Status.RESERVED and booking.flight_fare_id:
        flight_fare = FlightFare.objects.select_for_update().get(id=booking.flight_fare_id)
        flight_fare.seats_sold = max(0, flight_fare.seats_sold - booking.passengers_count)
        flight_fare.save(update_fields=["seats_sold"])

    BookingPassenger.objects.filter(booking_id=booking.id).update(
        aircraft_seat=None,
        seat_no=None,
    )

    booking.status = Booking.Status.CANCELLED
    booking.save(update_fields=["status"])
    return booking


@transaction.atomic
def expire_booking_if_needed(*, booking_id: int) -> Booking:

    booking = Booking.objects.select_for_update().get(id=booking_id)

    if booking.status != Booking.Status.RESERVED:
        return booking

    if booking.expires_at and booking.expires_at <= timezone.now():
        return cancel_booking(booking_id=booking.id)

    return booking


@transaction.atomic
def release_all_expired_reservations() -> int:
    now = timezone.now()

    qs = Booking.objects.select_for_update().filter(
        status=Booking.Status.RESERVED,
        expires_at__isnull=False,
        expires_at__lte=now,
    )

    count = 0
    for b in qs.select_related("flight_fare"):
        cancel_booking(booking_id=b.id)
        count += 1
    return count
