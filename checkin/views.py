from __future__ import annotations
from django.shortcuts import render,  get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from bookings.services.services_emails import send_checkin_success_email
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from bookings.models import Booking
from checkin.services.services_checkins import check_in_passengers
from checkin.services.services_boardingpass_pdf import build_boarding_pass_pdf_bytes

# Create your views here.

@login_required
def checkin_page(request, booking_id: int):
    booking = get_object_or_404(
        Booking.objects.select_related("flight", "flight__origin", "flight__destination", "user")
        .prefetch_related("passengers"),
        id=booking_id,
        user=request.user,
    )

    passengers = list(booking.passengers.all().order_by("id"))
    all_checked_in = passengers and all(p.checked_in for p in passengers)

    return render(
        request,
        "checkin/checkin_page.html",
        {
            "booking": booking,
            "passengers": passengers,
            "all_checked_in": all_checked_in,
        },
    )


@login_required
def checkin_submit(request, booking_id: int):
    if request.method != "POST":
        return redirect("checkin:checkin_page", booking_id=booking_id)

    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    raw = request.POST.getlist("passenger_ids")
    passenger_ids = [int(x) for x in raw if x.isdigit()]

    try:
        check_in_passengers(booking_id=booking.id, user_id=request.user.id, passenger_ids=passenger_ids)
        boarding_pass_url = f"{settings.SITE_URL}/check-in/{booking.id}/boarding-pass.pdf"
        send_checkin_success_email(
            booking=booking,
            passenger_ids=passenger_ids,
            boarding_pass_url=boarding_pass_url,
        )
        messages.success(request, "Check-in completed.")
    except ValidationError as ex:
        messages.error(request, ex.message)

    return redirect("checkin:checkin_page", booking_id=booking.id)


@login_required
def boarding_pass_pdf(request, booking_id: int):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    pdf_bytes = build_boarding_pass_pdf_bytes(booking_id=booking.id)
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="boarding_pass_{booking.booking_code}.pdf"'
    return resp
