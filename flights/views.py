from django.shortcuts import render

# Create your views here.
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404

from flights.forms import FlightSearchForm
from flights.models import Flight

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from core.authz import operator_required

from flights.forms import FlightDelayForm, FlightRescheduleForm, FlightCancelForm
from flights.services.services_ops import apply_delay_minutes, reschedule_departure, cancel_flight

from flights.forms import FlightStatusForm
from flights.services.services_ops import set_flight_status

from django.db.models import Q
from django.templatetags.static import static
from django.conf import settings
from core.models import CityImage


def _best_fare_for_flight(flight, passengers: int | None, fare_class_id: int | None):
    fares = list(flight.fares.all())

    if fare_class_id:
        fares = [f for f in fares if f.fare_class_id == fare_class_id]

    options = []
    for f in fares:
        available = f.seats_allocated - f.seats_sold
        if passengers and available < passengers:
            continue
        options.append({"fare": f, "available": available})

    if not options:
        return None

    options.sort(key=lambda x: x["fare"].price)
    best = options[0]
    return {
        "fare_class": best["fare"].fare_class,
        "price": best["fare"].price,
        "available": best["available"],
    }


def flight_list(request):
    form = FlightSearchForm(request.GET or None)

    qs = (
        Flight.objects.select_related("airline", "origin", "destination")
        .prefetch_related("fares", "fares__fare_class")
        .order_by("scheduled_departure")
    )

    passengers = None
    fare_class_id = None

    if form.is_valid():
        q = (form.cleaned_data.get("q") or "").strip()
        origin = form.cleaned_data.get("origin")
        destination = form.cleaned_data.get("destination")
        date = form.cleaned_data.get("date")
        passengers = form.cleaned_data.get("passengers") or 1
        fare_class = form.cleaned_data.get("fare_class")
        fare_class_id = fare_class.id if fare_class else None

        if q:
            qs = qs.filter(
                Q(origin__city__icontains=q)
                | Q(origin__country__icontains=q)
                | Q(origin__iata_code__icontains=q)
                | Q(destination__city__icontains=q)
                | Q(destination__country__icontains=q)
                | Q(destination__iata_code__icontains=q)
            )

        if origin:
            qs = qs.filter(origin=origin)
        if destination:
            qs = qs.filter(destination=destination)
        if date:
            qs = qs.filter(scheduled_departure__date=date)

        qs = qs.exclude(status=Flight.Status.CANCELLED)

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    pairs = {(f.destination.city, f.destination.country) for f in page_obj}

    city_images = CityImage.objects.filter(
        Q(city__in=[c for c, _ in pairs])
    ).only("city", "country", "image")

    img_map = {}
    for ci in city_images:
        key = (ci.city, ci.country)
        if ci.image:
            img_map[key] = ci.image.url

    flight_cards = []
    for f in page_obj:
        best = _best_fare_for_flight(f, passengers, fare_class_id)
        img_url = img_map.get((f.destination.city, f.destination.country))
        flight_cards.append({"flight": f, "best": best, "image_url": img_url})

    return render(
        request,
        "flights/flight_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "flight_cards": flight_cards,
        },
    )




def flight_detail(request, pk: int):
    flight = get_object_or_404(
        Flight.objects.select_related("airline", "origin", "destination").prefetch_related("fares", "fares__fare_class"),
        pk=pk,
    )

    fares = []
    for f in flight.fares.all().order_by("price"):
        fares.append({"fare": f, "available": f.seats_allocated - f.seats_sold})

    city_img = CityImage.objects.filter(city=flight.destination.city, country=flight.destination.country).first()
    if city_img and city_img.image and not getattr(city_img, "no_image_found", False):
        hero_image_url = settings.MEDIA_URL + str(city_img.image)
    else:
        hero_image_url = static("card_img.jpg")

    is_operator = False
    if request.user.is_authenticated:
        is_operator = (
            request.user.is_superuser
            or request.user.is_staff
            or request.user.groups.filter(name="Operator").exists()
        )

    is_passenger = False
    if request.user.is_authenticated:
        is_passenger = request.user.groups.filter(name="Passenger").exists()

    can_book = is_passenger and flight.status in [Flight.Status.PLANNED, Flight.Status.DELAYED]

    return render(
        request,
        "flights/flight_detail.html",
        {"flight": flight, "fares": fares, "is_operator": is_operator, "can_book": can_book, "hero_image_url": hero_image_url},
    )


@operator_required
def flight_delay(request, pk: int):
    flight = get_object_or_404(Flight, pk=pk)

    form = FlightDelayForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            apply_delay_minutes(flight_id=flight.id, minutes=form.cleaned_data["delay_minutes"])
            messages.success(request, "Flight delayed and passengers notified.")
            return redirect("flights:flight_detail", pk=flight.id)
        except ValidationError as ex:
            form.add_error(None, ex.message)

    return render(request, "flights/flight_ops_delay.html", {"flight": flight, "form": form})


@operator_required
def flight_reschedule(request, pk: int):
    flight = get_object_or_404(Flight, pk=pk)

    form = FlightRescheduleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            reschedule_departure(flight_id=flight.id, new_departure=form.cleaned_data["new_departure"])
            messages.success(request, "Flight rescheduled and passengers notified.")
            return redirect("flights:flight_detail", pk=flight.id)
        except ValidationError as ex:
            form.add_error(None, ex.message)

    return render(request, "flights/flight_ops_reschedule.html", {"flight": flight, "form": form})


@operator_required
def flight_cancel(request, pk: int):
    flight = get_object_or_404(Flight, pk=pk)

    form = FlightCancelForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            cancel_flight(flight_id=flight.id, note=form.cleaned_data.get("note"))
            messages.success(request, "Flight cancelled and passengers notified.")
            return redirect("flights:flight_detail", pk=flight.id)
        except ValidationError as ex:
            form.add_error(None, ex.message)

    return render(request, "flights/flight_ops_cancel.html", {"flight": flight, "form": form})


@operator_required
def flight_set_status(request, pk: int):
    flight = get_object_or_404(Flight, pk=pk)

    form = FlightStatusForm(request.POST or None, initial={"new_status": flight.status})
    if request.method == "POST" and form.is_valid():
        try:
            set_flight_status(
                flight_id=flight.id,
                new_status=form.cleaned_data["new_status"],
                note=form.cleaned_data.get("note"),
            )
            messages.success(request, "Flight status updated and passengers notified.")
            return redirect("flights:flight_detail", pk=flight.id)
        except ValidationError as ex:
            form.add_error(None, ex.message)

    return render(request, "flights/flight_ops_status.html", {"flight": flight, "form": form})
