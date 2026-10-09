from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from bookings.models import Booking
from flights.models import Flight
from bookings.services.services_ticket_pdf import build_ticket_pdf_bytes
from django.core.mail import EmailMessage


def send_booking_reserved_email(booking: Booking) -> None:
    to_email = booking.user.email
    if not to_email:
        return

    subject = f"Reservation confirmed: {booking.booking_code}"

    context = {"booking": booking}
    message_txt = render_to_string("emails/booking_reserved.txt", context)

    send_mail(
        subject=subject,
        message=message_txt,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=False,
    )


def send_booking_paid_email(booking: Booking) -> None:
    to_email = booking.user.email
    if not to_email:
        return

    subject = f"Payment successful: {booking.booking_code}"

    profile = getattr(booking.user, "passenger_profile", None)
    checkin_url = f"{settings.SITE_URL}/check-in/{booking.id}/"
    context = {
        "booking": booking,
        "profile": profile,
        "show_seats": True,
        "checkin_url": checkin_url,
    }
    message_txt = render_to_string("emails/booking_paid.txt", context)

    email = EmailMessage(
        subject=subject,
        body=message_txt,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )

    if getattr(booking, "ticket", None):
        pdf_bytes = build_ticket_pdf_bytes(booking=booking)
        filename = f"ticket_{booking.booking_code}.pdf"
        email.attach(filename, pdf_bytes, "application/pdf")

    email.send(fail_silently=False)


def send_refund_requested_email(refund) -> None:
    booking = refund.booking
    to_email = booking.user.email
    if not to_email:
        return

    subject = f"Refund requested: {booking.booking_code}"
    context = {"booking": booking, "refund": refund}
    message_txt = render_to_string("emails/refund_requested.txt", context)

    send_mail(subject, message_txt, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)


def send_refund_approved_email(refund) -> None:
    booking = refund.booking
    to_email = booking.user.email
    if not to_email:
        return

    subject = f"Refund approved: {booking.booking_code}"
    context = {"booking": booking, "refund": refund}
    message_txt = render_to_string("emails/refund_approved.txt", context)

    send_mail(subject, message_txt, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)


def send_refund_completed_email(refund) -> None:
    booking = refund.booking
    to_email = booking.user.email
    if not to_email:
        return

    subject = f"Refund completed: {booking.booking_code}"
    context = {"booking": booking, "refund": refund}
    message_txt = render_to_string("emails/refund_completed.txt", context)

    send_mail(subject, message_txt, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)

def send_refund_rejected_email(refund) -> None:
    booking = refund.booking
    to_email = booking.user.email
    if not to_email:
        return

    subject = f"Refund rejected: {booking.booking_code}"
    context = {"booking": booking, "refund": refund}
    message_txt = render_to_string("emails/refund_rejected.txt", context)

    send_mail(
        subject,
        message_txt,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
        fail_silently=False,
    )

def send_booking_cancelled_email(booking: Booking) -> None:
    to_email = booking.user.email
    if not to_email:
        return

    subject = f"Booking cancelled: {booking.booking_code}"

    context = {"booking": booking}
    message_txt = render_to_string("emails/booking_cancelled.txt", context)

    send_mail(
        subject=subject,
        message=message_txt,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=False,
    )

def send_flight_delayed_email_to_user(*, to_email: str, flight: Flight, old_departure, old_arrival) -> None:
    if not to_email:
        return
    subject = f"Flight delayed: {flight.flight_number}"
    context = {
        "flight": flight,
        "old_departure": old_departure,
        "old_arrival": old_arrival,
    }
    message_txt = render_to_string("emails/flight_delayed.txt", context)
    send_mail(subject, message_txt, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)


def send_flight_cancelled_email_to_user(*, to_email: str, flight: Flight) -> None:
    if not to_email:
        return
    subject = f"Flight cancelled: {flight.flight_number}"
    context = {"flight": flight}
    message_txt = render_to_string("emails/flight_cancelled.txt", context)
    send_mail(subject, message_txt, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)


def send_flight_status_changed_email_to_user(*, to_email: str, flight, old_status: str, new_status: str) -> None:
    if not to_email:
        return
    subject = f"Flight status update: {flight.flight_number}"
    context = {"flight": flight, "old_status": old_status, "new_status": new_status}
    message_txt = render_to_string("emails/flight_status_changed.txt", context)
    send_mail(subject, message_txt, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)


def send_checkin_success_email(*, booking: Booking, passenger_ids: list[int], boarding_pass_url: str) -> None:
    to_email = booking.user.email
    if not to_email:
        return

    passengers = booking.passengers.filter(id__in=passenger_ids).order_by("id")

    subject = f"Check-in successful: {booking.booking_code}"
    context = {
        "booking": booking,
        "passengers": passengers,
        "boarding_pass_url": boarding_pass_url,
    }
    message_txt = render_to_string("emails/checkin_success.txt", context)

    send_mail(
        subject=subject,
        message=message_txt,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=False,
    )