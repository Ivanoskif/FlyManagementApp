from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from bookings.services.services_emails import send_refund_requested_email, send_refund_approved_email, send_refund_completed_email, send_refund_rejected_email
from bookings.models import Booking, Refund, Payment, Ticket, BookingPassenger
from flights.models import FlightFare, FareClass


def _q2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _refund_penalty_rate(refund_policy: str) -> Decimal:

    if refund_policy == FareClass.RefundPolicy.FLEX:
        return Decimal("0.00")
    if refund_policy == FareClass.RefundPolicy.PARTIAL:
        return Decimal("0.20")
    if refund_policy == FareClass.RefundPolicy.NON_REFUNDABLE:
        return Decimal("1.00")
    return Decimal("0.20")


@transaction.atomic
def request_refund(*, booking_id: int, reason: str | None = None) -> Refund:

    booking = (
        Booking.objects.select_for_update()
        .select_related("fare_class", "flight")
        .get(id=booking_id)
    )

    if booking.status != Booking.Status.PAID:
        raise ValidationError("Refund can be requested only for PAID bookings.")

    if booking.refunds.filter(status__in=[Refund.Status.REQUESTED, Refund.Status.APPROVED]).exists():
        raise ValidationError("There is already an active refund request for this booking.")

    policy = booking.fare_class.refund_policy
    if policy == FareClass.RefundPolicy.NON_REFUNDABLE:
        raise ValidationError("This fare is non-refundable.")

    penalty_rate = _refund_penalty_rate(policy)

    if booking.flight.scheduled_departure <= timezone.now():
        raise ValidationError("Cannot refund after the flight has started/departed.")

    gross = Decimal(str(booking.total_amount))
    refundable = _q2(gross * (Decimal("1.00") - penalty_rate))

    if refundable <= 0:
        raise ValidationError("Refundable amount is 0 for this booking.")

    payment = booking.payments.filter(status=Payment.Status.SUCCESS).order_by("-paid_at", "-created_at").first()

    refund = Refund.objects.create(
        booking=booking,
        payment=payment,
        amount=refundable,
        reason=reason,
        status=Refund.Status.REQUESTED,
    )
    send_refund_requested_email(refund)
    return refund


@transaction.atomic
def approve_refund(*, refund_id: int) -> Refund:
    refund = Refund.objects.select_for_update().select_related("booking").get(id=refund_id)
    if refund.status != Refund.Status.REQUESTED:
        raise ValidationError("Only REQUESTED refunds can be approved.")
    refund.status = Refund.Status.APPROVED
    refund.save(update_fields=["status"])
    send_refund_approved_email(refund)
    return refund


@transaction.atomic
def reject_refund(*, refund_id: int, reason: str | None = None) -> Refund:
    refund = Refund.objects.select_for_update().select_related(
        "booking",
        "booking__user",
        "booking__flight",
        "booking__flight__origin",
        "booking__flight__destination",
    ).get(id=refund_id)

    if refund.status not in [Refund.Status.REQUESTED, Refund.Status.APPROVED]:
        raise ValidationError("Only REQUESTED/APPROVED refunds can be rejected.")

    if reason:
        refund.reason = reason

    refund.status = Refund.Status.REJECTED
    refund.save(update_fields=["status", "reason"])

    send_refund_rejected_email(refund)

    return refund



@transaction.atomic
def complete_refund(*, refund_id: int) -> tuple[Refund, Booking]:
    refund = Refund.objects.select_for_update().select_related("booking").get(id=refund_id)
    booking = (
        Booking.objects.select_for_update()
        .select_related("flight_fare", "ticket")
        .get(id=refund.booking_id)
    )

    if refund.status != Refund.Status.APPROVED:
        raise ValidationError("Only APPROVED refunds can be completed.")

    if booking.status != Booking.Status.PAID:
        raise ValidationError("Booking must be PAID to complete refund.")

    if booking.flight_fare_id:
        ff = FlightFare.objects.select_for_update().get(id=booking.flight_fare_id)
        ff.seats_sold = max(0, ff.seats_sold - booking.passengers_count)
        ff.save(update_fields=["seats_sold"])

    BookingPassenger.objects.filter(booking_id=booking.id).update(
        aircraft_seat=None,
        seat_no=None,
    )

    ticket = getattr(booking, "ticket", None)
    if ticket is not None:
        ticket.status = Ticket.Status.REFUNDED
        ticket.save(update_fields=["status"])

    booking.status = Booking.Status.REFUNDED
    booking.save(update_fields=["status"])

    refund.status = Refund.Status.COMPLETED
    refund.refunded_at = timezone.now()
    refund.save(update_fields=["status", "refunded_at"])

    send_refund_completed_email(refund)

    return refund, booking
