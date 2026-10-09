from __future__ import annotations
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from bookings.models import Booking, Payment, Ticket
from bookings.services.services_emails import send_booking_paid_email
from bookings.services.services_seats import auto_assign_seats_for_booking


@transaction.atomic
def create_payment(
    *,
    booking_id: int,
    amount: Decimal,
    method: str = Payment.Method.CARD,
    provider_ref: str | None = None,
) -> Payment:
    booking = Booking.objects.select_for_update().get(id=booking_id)

    if booking.status in [Booking.Status.CANCELLED, Booking.Status.REFUNDED]:
        raise ValidationError("Cannot pay for a cancelled/refunded booking.")

    if booking.status == Booking.Status.PAID:
        raise ValidationError("Booking is already PAID.")

    if amount <= 0:
        raise ValidationError("Payment amount must be > 0.")

    if booking.total_amount and Decimal(amount) != Decimal(booking.total_amount):
        raise ValidationError("Payment amount must match booking total amount.")

    payment = Payment.objects.create(
        booking=booking,
        amount=amount,
        method=method,
        provider_ref=provider_ref,
        status=Payment.Status.PENDING,
    )
    return payment


@transaction.atomic
def mark_payment_success(*, payment_id: int) -> tuple[Payment, Booking, Ticket]:
    payment = Payment.objects.select_for_update().select_related("booking").get(id=payment_id)
    booking = (
        Booking.objects.select_for_update()
        .select_related("ticket", "flight", "fare_class", "user", "flight__origin", "flight__destination",
                        "flight__airline")
        .prefetch_related("passengers")
        .get(id=payment.booking_id)
    )

    if payment.status == Payment.Status.SUCCESS:
        ticket = getattr(booking, "ticket", None)
        if ticket is None and booking.status == Booking.Status.PAID:
            ticket = Ticket.objects.create(booking=booking)

        return payment, booking, ticket

    if payment.status == Payment.Status.CANCELLED:
        raise ValidationError("Cannot mark cancelled payment as success.")

    if booking.status in [Booking.Status.CANCELLED, Booking.Status.REFUNDED]:
        raise ValidationError("Cannot pay for cancelled/refunded booking.")

    if booking.status == Booking.Status.PAID:
        raise ValidationError("Booking is already PAID.")

    if booking.total_amount and Decimal(payment.amount) != Decimal(booking.total_amount):
        raise ValidationError("Payment amount must match booking total amount.")

    payment.status = Payment.Status.SUCCESS
    payment.paid_at = timezone.now()
    payment.save(update_fields=["status", "paid_at"])

    profile = getattr(booking.user, "passenger_profile", None)
    if profile and not profile.can_choose_seat:
        if booking.passengers.filter(aircraft_seat__isnull=True).exists():
            auto_assign_seats_for_booking(booking_id=booking.id)

    booking.status = Booking.Status.PAID
    booking.save(update_fields=["status"])

    ticket = getattr(booking, "ticket", None)
    if ticket is None:
        ticket = Ticket.objects.create(booking=booking)

    if not booking.paid_email_sent:
        send_booking_paid_email(booking)
        booking.paid_email_sent = True
        booking.save(update_fields=["paid_email_sent"])

    return payment, booking, ticket


@transaction.atomic
def mark_payment_failed(*, payment_id: int) -> Payment:
    payment = Payment.objects.select_for_update().select_related("booking").get(id=payment_id)

    if payment.status == Payment.Status.SUCCESS:
        raise ValidationError("Cannot mark a successful payment as failed.")

    payment.status = Payment.Status.FAILED
    payment.save(update_fields=["status"])
    return payment


@transaction.atomic
def process_demo_payment(
    *,
    booking_id: int,
    user_id: int,
    method: str = Payment.Method.CARD,
    provider_ref: str | None = None,
    succeed: bool = True,
) -> tuple[Payment, Booking, Ticket | None]:

    booking = Booking.objects.select_for_update().get(id=booking_id)

    if booking.user_id != user_id:
        raise ValidationError("You cannot pay for someone else's booking.")

    payment = create_payment(
        booking_id=booking.id,
        amount=Decimal(str(booking.total_amount)),
        method=method,
        provider_ref=provider_ref,
    )

    if succeed:
        profile = getattr(booking.user, "passenger_profile", None)
        if profile and not profile.can_choose_seat:
            auto_assign_seats_for_booking(booking_id=booking.id)

        payment, booking, ticket = mark_payment_success(payment_id=payment.id)
        return payment, booking, ticket

    mark_payment_failed(payment_id=payment.id)
    return payment, booking, None
