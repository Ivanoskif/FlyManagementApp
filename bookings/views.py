from django.shortcuts import render
from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from bookings.forms import BookingCreateForm, PassengerFormSet, RefundRequestForm, DemoPaymentForm
from bookings.models import BookingPassenger, Booking, Refund
from bookings.services.services import create_booking_reserved, cancel_booking
from bookings.services.services_payments import create_payment, mark_payment_success, process_demo_payment
from core.authz import operator_required
from bookings.services.services_refunds import request_refund, approve_refund, reject_refund, complete_refund
from bookings.services.services_emails import send_booking_reserved_email, send_booking_cancelled_email
from django.contrib.auth.decorators import login_required
from bookings.services.services_seats import choose_seat_for_passenger, auto_assign_seats_for_booking
from core.models import AircraftSeat, CityImage
from flights.models import Flight
from baggage.services.services_baggages import  ensure_included_baggage_for_booking, set_passenger_addons_from_post, recalc_booking_total_amount, get_baggage_summary_for_booking
from checkin.services.services_checkins import check_in_passengers
from django.templatetags.static import static
from django.conf import settings
from baggage.models import BookingPassengerBaggage, BaggageType

# Create your views here.

@login_required
def booking_create(request, flight_id: int):
    flight = get_object_or_404(
        Flight.objects.select_related("airline", "origin", "destination").prefetch_related("fares", "fares__fare_class"),
        id=flight_id,
    )

    form = BookingCreateForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        fare_class = form.cleaned_data["fare_class"]
        passengers_count = form.cleaned_data["passengers_count"]

        try:
            booking = create_booking_reserved(
                user=request.user,
                flight_id=flight.id,
                fare_class_id=fare_class.id,
                passengers_count=passengers_count,
            )
            messages.success(request, f"Booking created: {booking.booking_code}")
            return redirect("bookings:booking_passengers", pk=booking.id)
        except ValidationError as ex:
            messages.error(request, ex.message)

    fares = []
    for f in flight.fares.all().order_by("price"):
        fares.append({"fare": f, "available": f.seats_allocated - f.seats_sold})

    city_img = CityImage.objects.filter(
        city=flight.destination.city,
        country=flight.destination.country
    ).first()

    if city_img and city_img.image and not getattr(city_img, "no_image_found", False):
        hero_image_url = settings.MEDIA_URL + str(city_img.image)
    else:
        hero_image_url = static("card_img.jpg")

    return render(
        request,
        "bookings/booking_create.html",
        {"flight": flight, "fares": fares, "form": form, "hero_image_url": hero_image_url},
    )

@login_required
def booking_cancel(request, pk: int):
    if request.method != "POST":
        return redirect("bookings:booking_detail", pk=pk)

    booking = get_object_or_404(Booking, pk=pk, user=request.user)

    if booking.status != Booking.Status.RESERVED:
        messages.error(request, "Only RESERVED bookings can be cancelled.")
        return redirect("bookings:booking_detail", pk=booking.id)

    try:
        booking = cancel_booking(booking_id=booking.id, by_user=request.user)

        send_booking_cancelled_email(booking)

        messages.success(request, "Booking cancelled. Seats released.")
    except ValidationError as ex:
        messages.error(request, ex.message)

    return redirect("bookings:booking_detail", pk=booking.id)


@login_required
def my_bookings(request):
    status = request.GET.get("status")

    qs = (
        Booking.objects.filter(user=request.user)
        .select_related("flight", "flight__origin", "flight__destination", "fare_class", "ticket")
        .order_by("-created_at")
    )

    if status:
        qs = qs.filter(status=status)

    return render(
        request,
        "bookings/my_bookings.html",
        {"bookings": qs, "selected_status": status},
    )



@login_required
def booking_detail(request, pk: int):
    booking = get_object_or_404(
        Booking.objects.select_related(
            "flight",
            "flight__airline",
            "flight__origin",
            "flight__destination",
            "fare_class",
            "ticket",
        ).prefetch_related("passengers", "passengers__baggage_items", "payments", "refunds"),
        pk=pk,
        user=request.user,
    )

    baggage_summary = get_baggage_summary_for_booking(booking_id=booking.id)

    return render(
        request,
        "bookings/booking_detail.html",
        {"booking": booking, "baggage_summary": baggage_summary},
    )

@login_required
def booking_passengers(request, pk: int):
    booking = get_object_or_404(
        Booking.objects.select_related("flight", "fare_class"),
        pk=pk,
        user=request.user,
    )

    existing = BookingPassenger.objects.filter(booking=booking).order_by("id")
    existing_count = existing.count()

    if existing_count == booking.passengers_count and request.method != "POST" and request.GET.get("edit") != "1":
        return redirect("bookings:booking_detail", pk=booking.id)

    if existing_count < booking.passengers_count:
        missing = booking.passengers_count - existing_count
        BookingPassenger.objects.bulk_create(
            [BookingPassenger(booking=booking, first_name="", last_name="", date_of_birth="2000-01-01", document_no="") for _ in range(missing)]
        )
        existing = BookingPassenger.objects.filter(booking=booking).order_by("id")

    ensure_included_baggage_for_booking(booking_id=booking.id)

    formset = PassengerFormSet(
        request.POST or None,
        queryset=existing,
    )

    if request.method == "POST":
        if not formset.is_valid():
            print("FORMSET ERRORS:", formset.errors)
            print("NON FORM ERRORS:", formset.non_form_errors())


    if request.method == "POST" and formset.is_valid():
        for orm in formset:
            pass

        formset.save()

        ensure_included_baggage_for_booking(booking_id=booking.id)

        passengers = BookingPassenger.objects.filter(booking_id=booking.id).order_by("id")
        for p in passengers:
            extra_cabin = int(request.POST.get(f"extra_cabin_{p.id}", "0") or "0")
            extra_checked = int(request.POST.get(f"extra_checked_{p.id}", "0") or "0")

            set_passenger_addons_from_post(
                booking_id=booking.id,
                passenger_id=p.id,
                extra_cabin_pieces=extra_cabin,
                extra_checked_pieces=extra_checked,
            )

        recalc_booking_total_amount(booking_id=booking.id)

        profile = getattr(request.user, "passenger_profile", None)
        if profile and not profile.can_choose_seat:
            try:
                auto_assign_seats_for_booking(booking_id=booking.id)
                messages.info(request, "Seats will be automatically assigned after check-in (BASIC membership).")
            except ValidationError as ex:
                messages.error(request, ex.message)
                return redirect("bookings:booking_passengers", pk=booking.id)

        if booking.passengers.count() == booking.passengers_count and not booking.reserved_email_sent:
            send_booking_reserved_email(booking)
            booking.reserved_email_sent = True
            booking.save(update_fields=["reserved_email_sent"])

        messages.success(request, "Passenger details saved. Confirmation email sent.")
        return redirect("bookings:booking_detail", pk=booking.id)

    if request.method == "POST" and not formset.is_valid():
        messages.error(request, "Please fix the errors below and try again.")

    passengers = BookingPassenger.objects.filter(booking_id=booking.id).order_by("id")

    addon_defaults = {}
    if request.method == "POST":
        for p in passengers:
            addon_defaults[p.id] = {
                "extra_cabin": int(request.POST.get(f"extra_cabin_{p.id}", "0") or "0"),
                "extra_checked": int(request.POST.get(f"extra_checked_{p.id}", "0") or "0"),
            }
    else:
        addon_rows = (
            BookingPassengerBaggage.objects
            .filter(booking_passenger__booking_id=booking.id, is_included=False)
        )
        for p in passengers:
            addon_defaults[p.id] = {"extra_cabin": 0, "extra_checked": 0}

        for row in addon_rows:
            if row.baggage_type == BaggageType.CABIN:
                addon_defaults[row.booking_passenger_id]["extra_cabin"] = row.pieces
            elif row.baggage_type == BaggageType.CHECKED:
                addon_defaults[row.booking_passenger_id]["extra_checked"] = row.pieces

    baggage_summary = get_baggage_summary_for_booking(booking_id=booking.id)
    return render(
        request,
        "bookings/booking_passengers.html",
        {
            "booking": booking,
            "formset": formset,
            "baggage_summary": baggage_summary,
            "addon_defaults": addon_defaults,
        },
    )


@login_required
def booking_pay(request, pk: int):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)

    if booking.status != Booking.Status.RESERVED:
        messages.info(request, "Booking is not in RESERVED status.")
        return redirect("bookings:booking_detail", pk=booking.id)

    if booking.passengers.count() != booking.passengers_count:
        messages.error(request, "Please fill passenger details before payment.")
        return redirect("bookings:booking_passengers", pk=booking.id)

    try:
        p = create_payment(
            booking_id=booking.id,
            amount=Decimal(str(booking.total_amount)),
            method="CARD",
            provider_ref="DEMO-PAYMENT",
        )
        _, booking2, ticket = mark_payment_success(payment_id=p.id)
        messages.success(request, f"Payment successful. Ticket issued: {ticket.ticket_number}")
        return redirect("bookings:booking_detail", pk=booking2.id)
    except ValidationError as ex:
        messages.error(request, ex.message)
        return redirect("bookings:booking_detail", pk=booking.id)


@login_required
def refund_request_view(request, pk: int):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)

    form = RefundRequestForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            request_refund(booking_id=booking.id, reason=form.cleaned_data["reason"])
            messages.success(request, "Refund request submitted.")
            return redirect("bookings:booking_detail", pk=booking.id)
        except ValidationError as ex:
            messages.error(request, ex.message)
            form.add_error(None, ex.message)

    return render(request, "bookings/refund_request.html", {"booking": booking, "form": form})


@operator_required
def refund_queue_view(request):
    refunds = (
        Refund.objects.select_related("booking", "booking__user", "booking__flight")
        .order_by("-created_at")
    )
    return render(request, "bookings/refund_queue.html", {"refunds": refunds})


@operator_required
def refund_approve_view(request, refund_id: int):
    if request.method != "POST":
        return redirect("bookings:refund_queue")

    try:
        approve_refund(refund_id=refund_id)
        messages.success(request, "Refund approved.")
    except ValidationError as ex:
        messages.error(request, ex.message)

    return redirect("bookings:refund_queue")


@operator_required
def refund_reject_view(request, refund_id: int):
    if request.method != "POST":
        return redirect("bookings:refund_queue")

    try:
        reject_refund(refund_id=refund_id, reason=None)
        messages.success(request, "Refund rejected.")
    except ValidationError as ex:
        messages.error(request, ex.message)

    return redirect("bookings:refund_queue")


@operator_required
def refund_complete_view(request, refund_id: int):
    if request.method != "POST":
        return redirect("bookings:refund_queue")

    try:
        refund, booking = complete_refund(refund_id=refund_id)
        messages.success(request, f"Refund completed. Booking {booking.booking_code} is REFUNDED.")
    except ValidationError as ex:
        messages.error(request, ex.message)

    return redirect("bookings:refund_queue")

@login_required
def demo_payment(request, pk: int):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)

    if booking.status != Booking.Status.RESERVED:
        messages.error(request, "This booking cannot be paid (status must be RESERVED).")
        return redirect("bookings:booking_detail", pk=booking.id)

    form = DemoPaymentForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            provider_ref = f"DEMO-{booking.booking_code}"
            process_demo_payment(booking_id=booking.id, user_id=request.user.id, provider_ref=provider_ref)
            messages.success(request, "Payment successful. Confirmation email sent.")
            return redirect("bookings:booking_detail", pk=booking.id)
        except ValidationError as ex:
            messages.error(request, ex.message)

    return render(request, "bookings/demo_payment.html", {"booking": booking, "form": form})

@login_required
def booking_seats(request, pk: int):
    booking = get_object_or_404(
        Booking.objects.select_related(
            "flight",
            "flight__airline",
            "flight__origin",
            "flight__destination",
            "flight__aircraft",
            "flight__aircraft__airline",
            "flight__aircraft__model",
        ).prefetch_related("passengers"),
        pk=pk,
        user=request.user,
    )

    if booking.status != Booking.Status.RESERVED:
        messages.error(request, "Seat selection is allowed only for RESERVED bookings.")
        return redirect("bookings:booking_detail", pk=booking.id)

    profile = getattr(request.user, "passenger_profile", None)
    if not profile or not profile.can_choose_seat:
        messages.error(request, "Your membership level does not allow seat selection.")
        return redirect("bookings:booking_detail", pk=booking.id)

    if not booking.flight.aircraft_id:
        messages.error(request, "This flight has no aircraft assigned yet.")
        return redirect("bookings:booking_detail", pk=booking.id)

    model = booking.flight.aircraft.model
    seats = list(
        AircraftSeat.objects.filter(aircraft_model=model).order_by("row_number", "seat_letter")
    )

    occupied = {}
    qs = (
        BookingPassenger.objects
        .select_related("booking")
        .filter(
            booking__flight_id=booking.flight_id,
            booking__status__in=[Booking.Status.RESERVED, Booking.Status.PAID],
            aircraft_seat__isnull=False,
        )
        .values("aircraft_seat_id", "booking__status")
    )
    for x in qs:
        occupied[x["aircraft_seat_id"]] = x["booking__status"]

    passengers = list(booking.passengers.all().order_by("id"))
    default_passenger_id = None
    for p in passengers:
        if not p.aircraft_seat_id:
            default_passenger_id = p.id
            break
    if default_passenger_id is None and passengers:
        default_passenger_id = passengers[0].id

    if request.method == "POST":
        passenger_id = int(request.POST.get("passenger_id") or "0")
        seat_id = int(request.POST.get("seat_id") or "0")
        try:
            choose_seat_for_passenger(
                booking_id=booking.id,
                passenger_id=passenger_id,
                seat_id=seat_id,
                user_id=request.user.id,
            )

            p = BookingPassenger.objects.select_related("aircraft_seat").get(id=passenger_id, booking_id=booking.id)
            seat_code = p.aircraft_seat.seat_code if p.aircraft_seat else "—"

            messages.success(request, f"{p.first_name} {p.last_name} reserved seat {seat_code}.")
            return redirect("bookings:booking_seats", pk=booking.id)
        except ValidationError as ex:
            messages.error(request, ex.message)

    rows = {}
    for s in seats:
        rows.setdefault(s.row_number, []).append(s)

    return render(
        request,
        "bookings/booking_seats.html",
        {
            "booking": booking,
            "profile": profile,
            "rows": rows,
            "occupied": occupied,
            "passengers": passengers,
            "default_passenger_id": default_passenger_id,
        },
    )


@login_required
def booking_check_in(request, pk: int):
    booking = get_object_or_404(
        Booking.objects.select_related("flight", "user").prefetch_related("passengers"),
        pk=pk,
        user=request.user,
    )

    if booking.status != Booking.Status.PAID:
        messages.error(request, "Check-in is available only after payment.")
        return redirect("bookings:booking_detail", pk=booking.id)

    if booking.flight.status == Flight.Status.CANCELLED:
        messages.error(request, "Flight is cancelled. Check-in is not available.")
        return redirect("bookings:booking_detail", pk=booking.id)

    passengers = list(booking.passengers.all().order_by("id"))

    if request.method == "POST":
        selected_ids = request.POST.getlist("passenger_ids")
        selected_ids = [int(x) for x in selected_ids if x.isdigit()]

        try:
            check_in_passengers(
                booking_id=booking.id,
                passenger_ids=selected_ids,
                user_id=request.user.id,
            )
            messages.success(request, "Check-in successful. Confirmation email sent.")
            return redirect("bookings:booking_detail", pk=booking.id)
        except ValidationError as ex:
            messages.error(request, ex.message)

    return render(request, "checkin/checkin_page.html", {"booking": booking, "passengers": passengers})