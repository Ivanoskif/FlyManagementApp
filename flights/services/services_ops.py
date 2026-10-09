from __future__ import annotations

from datetime import timedelta
from django.db import transaction
from django.core.exceptions import ValidationError

from bookings.models import Booking
from bookings.services.services_emails import send_flight_delayed_email_to_user, send_flight_cancelled_email_to_user, send_flight_status_changed_email_to_user

from flights.models import Flight, FlightCrewAssignment
from core.models import CrewMember

ALLOWED_AFFECTED_BOOKING_STATUSES = [Booking.Status.RESERVED, Booking.Status.PAID]

def _affected_bookings_qs(flight: Flight):
    return (
        Booking.objects
        .select_related("user")
        .filter(flight=flight, status__in=ALLOWED_AFFECTED_BOOKING_STATUSES)
    )


def _notify_delay(flight: Flight, old_dep, old_arr):
    qs = _affected_bookings_qs(flight)
    seen = set()
    for b in qs:
        email = (b.user.email or "").strip().lower()
        if not email or email in seen:
            continue
        seen.add(email)
        send_flight_delayed_email_to_user(
            to_email=email,
            flight=flight,
            old_departure=old_dep,
            old_arrival=old_arr,
        )


def _notify_cancel(flight: Flight):
    qs = _affected_bookings_qs(flight)
    seen = set()
    for b in qs:
        email = (b.user.email or "").strip().lower()
        if not email or email in seen:
            continue
        seen.add(email)
        send_flight_cancelled_email_to_user(to_email=email, flight=flight)


@transaction.atomic
def apply_delay_minutes(*, flight_id: int, minutes: int) -> Flight:
    if minutes <= 0:
        raise ValidationError("Delay minutes must be > 0.")

    flight = Flight.objects.select_for_update().get(id=flight_id)

    if flight.status in [Flight.Status.CANCELLED, Flight.Status.LANDED]:
        raise ValidationError("Cannot delay a cancelled/landed flight.")

    old_dep = flight.scheduled_departure
    old_arr = flight.scheduled_arrival

    delta = timedelta(minutes=minutes)
    flight.scheduled_departure = old_dep + delta
    flight.scheduled_arrival = old_arr + delta
    flight.status = Flight.Status.DELAYED
    flight.full_clean()
    flight.save(update_fields=["scheduled_departure", "scheduled_arrival", "status"])

    _notify_delay(flight, old_dep, old_arr)
    return flight


@transaction.atomic
def reschedule_departure(*, flight_id: int, new_departure) -> Flight:

    flight = Flight.objects.select_for_update().get(id=flight_id)

    if flight.status in [Flight.Status.CANCELLED, Flight.Status.LANDED]:
        raise ValidationError("Cannot reschedule a cancelled/landed flight.")

    old_dep = flight.scheduled_departure
    old_arr = flight.scheduled_arrival

    if new_departure <= old_dep:
        raise ValidationError("New departure must be after the current departure time.")

    delta = new_departure - old_dep
    flight.scheduled_departure = new_departure
    flight.scheduled_arrival = old_arr + delta
    flight.status = Flight.Status.DELAYED
    flight.full_clean()
    flight.save(update_fields=["scheduled_departure", "scheduled_arrival", "status"])

    _notify_delay(flight, old_dep, old_arr)
    return flight


@transaction.atomic
def cancel_flight(*, flight_id: int, note: str | None = None) -> Flight:
    flight = Flight.objects.select_for_update().get(id=flight_id)

    if flight.status == Flight.Status.CANCELLED:
        return flight
    if flight.status == Flight.Status.LANDED:
        raise ValidationError("Cannot cancel a landed flight.")

    flight.status = Flight.Status.CANCELLED
    if note:
        flight.notes = (flight.notes or "").strip()
        flight.notes = (flight.notes + "\n" if flight.notes else "") + f"[CANCEL NOTE] {note}"
    flight.full_clean()
    flight.save(update_fields=["status", "notes"])

    _notify_cancel(flight)
    return flight

@transaction.atomic
def set_flight_status(*, flight_id: int, new_status: str, note: str | None = None) -> Flight:
    flight = Flight.objects.select_for_update().get(id=flight_id)

    if flight.status == Flight.Status.LANDED and new_status != Flight.Status.LANDED:
        raise ValidationError("Cannot change status of a landed flight.")

    old_status = flight.status

    if new_status == old_status:
        return flight

    if new_status == Flight.Status.CANCELLED:
        return cancel_flight(flight_id=flight_id, note=note)

    flight.status = new_status
    if note:
        flight.notes = (flight.notes or "").strip()
        flight.notes = (flight.notes + "\n" if flight.notes else "") + f"[STATUS NOTE] {note}"
    flight.full_clean()
    flight.save(update_fields=["status", "notes"])

    qs = _affected_bookings_qs(flight)
    seen = set()
    for b in qs:
        email = (b.user.email or "").strip().lower()
        if not email or email in seen:
            continue
        seen.add(email)
        send_flight_status_changed_email_to_user(
            to_email=email,
            flight=flight,
            old_status=old_status,
            new_status=new_status,
        )

    return flight


@transaction.atomic
def assign_crew_to_flight(*, flight_id: int, crew_member_id: int, duty: str) -> FlightCrewAssignment:
    flight = Flight.objects.select_for_update().get(id=flight_id)

    if flight.status == Flight.Status.CANCELLED:
        raise ValidationError("Cannot assign crew to a cancelled flight.")

    if not flight.scheduled_departure or not flight.scheduled_arrival:
        raise ValidationError("Flight must have scheduled departure/arrival before assigning crew.")

    crew = CrewMember.objects.select_for_update().get(id=crew_member_id)
    if crew.status != CrewMember.Status.ACTIVE:
        raise ValidationError("Crew member is not active.")

    if FlightCrewAssignment.objects.filter(flight_id=flight.id, crew_member_id=crew.id).exists():
        raise ValidationError("This crew member is already assigned to this flight.")

    conflict = (
        Flight.objects
        .filter(crew_assignments__crew_member_id=crew.id)
        .exclude(id=flight.id)
        .exclude(status=Flight.Status.CANCELLED)
        .filter(
            scheduled_departure__lt=flight.scheduled_arrival,
            scheduled_arrival__gt=flight.scheduled_departure,
        )
        .select_related("origin", "destination")
        .order_by("scheduled_departure")
        .first()
    )

    if conflict:
        raise ValidationError(
            f"Crew member overlaps with flight {conflict.flight_number}"
        )

    ass = FlightCrewAssignment(
        flight_id=flight.id,
        crew_member_id=crew.id,
        duty=duty,
    )
    ass.full_clean()
    ass.save()
    return ass


@transaction.atomic
def remove_crew_assignment(*, assignment_id: int) -> None:
    FlightCrewAssignment.objects.select_for_update().filter(id=assignment_id).delete()
