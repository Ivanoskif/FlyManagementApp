from django.db import transaction
from django.core.exceptions import ValidationError
from bookings.models import Booking, BookingPassenger
from core.models import AircraftSeat
from accounts.models import PassengerProfile


@transaction.atomic
def choose_seat_for_passenger(*, booking_id: int, passenger_id: int, seat_id: int, user_id: int) -> BookingPassenger:
    booking = (
        Booking.objects.select_for_update()
        .select_related("flight", "flight__aircraft", "flight__aircraft__model")
        .get(id=booking_id, user_id=user_id)
    )

    if booking.status != Booking.Status.RESERVED:
        raise ValidationError("Seat selection is allowed only for RESERVED bookings.")

    profile, _ = PassengerProfile.objects.get_or_create(
        user_id=user_id,
        defaults={"first_name": "", "last_name": ""},
    )
    if not profile.can_choose_seat:
        raise ValidationError("Your membership level does not allow seat selection.")

    if not booking.flight.aircraft_id:
        raise ValidationError("This flight has no aircraft assigned yet.")

    aircraft_model = booking.flight.aircraft.model

    seat = AircraftSeat.objects.select_for_update().get(id=seat_id, aircraft_model=aircraft_model)

    if seat.is_extra_legroom and not profile.can_choose_extra_legroom:
        raise ValidationError("Extra legroom seats are available only for PREMIUM members.")

    passenger = BookingPassenger.objects.select_for_update().get(id=passenger_id, booking=booking)

    taken = (
        BookingPassenger.objects.select_for_update()
        .filter(
            booking__flight_id=booking.flight_id,
            booking__status__in=[Booking.Status.RESERVED, Booking.Status.PAID],
            aircraft_seat_id=seat.id,
        )
        .exclude(id=passenger.id)
        .exists()
    )
    if taken:
        raise ValidationError("This seat is already taken.")

    passenger.aircraft_seat = seat
    passenger.seat_no = seat.seat_code
    passenger.save(update_fields=["aircraft_seat", "seat_no"])

    return passenger

def _occupied_seat_ids_for_flight(flight_id: int) -> set[int]:
    qs = (
        BookingPassenger.objects
        .select_related("booking")
        .filter(
            booking__flight_id=flight_id,
            booking__status__in=[Booking.Status.RESERVED, Booking.Status.PAID],
            aircraft_seat__isnull=False,
        )
        .values_list("aircraft_seat_id", flat=True)
    )
    return set(qs)


def _seat_priority(seat: AircraftSeat) -> int:
    if seat.is_extra_legroom:
        return 99
    if seat.seat_type == AircraftSeat.SeatType.MIDDLE:
        return 0
    if seat.seat_type == AircraftSeat.SeatType.AISLE:
        return 1
    return 2


@transaction.atomic
def auto_assign_seats_for_booking(*, booking_id: int) -> None:
    booking = (
        Booking.objects
        .select_for_update()
        .select_related(
            "flight",
            "flight__aircraft",
            "flight__aircraft__model",
            "user",
        )
        .get(id=booking_id)
    )

    if booking.status != Booking.Status.RESERVED:
        return

    profile = getattr(booking.user, "passenger_profile", None)
    if not profile or profile.membership_level != profile.MembershipLevel.BASIC:
        return

    if not booking.flight.aircraft_id:
        return

    model = booking.flight.aircraft.model

    all_seats = list(
        AircraftSeat.objects
        .filter(aircraft_model=model)
        .order_by("row_number", "seat_letter")
    )
    if not all_seats:
        return

    occupied_ids = _occupied_seat_ids_for_flight(booking.flight_id)

    free = [s for s in all_seats if s.id not in occupied_ids]
    free.sort(key=_seat_priority)

    passengers = list(
        BookingPassenger.objects
        .select_for_update()
        .filter(booking_id=booking.id)
        .order_by("id")
    )

    need = [p for p in passengers if not p.aircraft_seat_id]
    if not need:
        return

    if len(free) < len(need):
        raise ValidationError("Not enough free seats to auto-assign.")

    for p, seat in zip(need, free):
        p.aircraft_seat = seat
        p.seat_no = seat.seat_code
        p.save(update_fields=["aircraft_seat", "seat_no"])

def _seat_priority_any_membership(seat: AircraftSeat, *, allow_extra_legroom: bool) -> int:
    if seat.is_extra_legroom and not allow_extra_legroom:
        return 10_000

    if seat.is_extra_legroom:
        base = 50
    else:
        base = 0

    if seat.seat_type == AircraftSeat.SeatType.MIDDLE:
        return base + 0
    if seat.seat_type == AircraftSeat.SeatType.AISLE:
        return base + 1
    return base + 2


@transaction.atomic
def auto_assign_missing_seats_for_booking(*, booking_id: int) -> None:
    booking = (
        Booking.objects
        .select_for_update()
        .select_related("flight", "flight__aircraft", "flight__aircraft__model", "user")
        .get(id=booking_id)
    )

    if booking.status not in [Booking.Status.RESERVED, Booking.Status.PAID]:
        return

    if not booking.flight.aircraft_id:
        return

    profile = getattr(booking.user, "passenger_profile", None)
    if not profile:
        profile, _ = PassengerProfile.objects.get_or_create(
            user_id=booking.user_id,
            defaults={"first_name": "", "last_name": ""},
        )

    allow_xl = bool(getattr(profile, "can_choose_extra_legroom", False))

    model = booking.flight.aircraft.model

    all_seats = list(
        AircraftSeat.objects
        .filter(aircraft_model=model)
        .order_by("row_number", "seat_letter")
    )
    if not all_seats:
        return

    occupied_ids = _occupied_seat_ids_for_flight(booking.flight_id)
    free = [s for s in all_seats if s.id not in occupied_ids]

    free.sort(key=lambda s: _seat_priority_any_membership(s, allow_extra_legroom=allow_xl))

    passengers = list(
        BookingPassenger.objects
        .select_for_update()
        .filter(booking_id=booking.id)
        .order_by("id")
    )
    need = [p for p in passengers if not p.aircraft_seat_id]
    if not need:
        return

    if len(free) < len(need):
        raise ValidationError("Not enough free seats to auto-assign.")

    for p, seat in zip(need, free):
        if seat.is_extra_legroom and not allow_xl:
            continue
        p.aircraft_seat = seat
        p.seat_no = seat.seat_code
        p.save(update_fields=["aircraft_seat", "seat_no"])

    if BookingPassenger.objects.filter(booking_id=booking.id, aircraft_seat__isnull=True).exists():
        raise ValidationError("Unable to auto-assign seats (seat constraints).")


