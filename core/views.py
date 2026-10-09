from django.shortcuts import render

# Create your views here.
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.db.models import Count
from django.utils import timezone
from django.templatetags.static import static
from django.conf import settings

from core.forms import RouteSearchForm
from core.models import Airport, Airline, Route, CityImage

from flights.forms import FlightSearchForm
from flights.models import Flight

from django.db.models import Q


def home(request):
    form = FlightSearchForm(request.GET or None)

    stats = {
        "airports": Airport.objects.count(),
        "airlines": Airline.objects.count(),
        "routes": Route.objects.count(),
        "flights": Flight.objects.count(),
    }

    top_origins = (
        Flight.objects.values("origin__iata_code", "origin__city", "origin__country")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")[:8]
    )

    popular_routes = (
        Flight.objects.values(
            "origin__iata_code", "origin__city", "origin__country",
            "destination__iata_code", "destination__city", "destination__country",
        )
        .annotate(cnt=Count("id"))
        .order_by("-cnt")[:6]
    )

    now = timezone.now()
    suggested_flights = (
        Flight.objects.select_related("airline", "origin", "destination")
        .filter(scheduled_departure__gte=now)
        .order_by("scheduled_departure")[:6]
    )

    dest_pairs = {(f.destination.city, f.destination.country) for f in suggested_flights}

    city_images = {}
    if dest_pairs:
        q = Q()
        for city, country in dest_pairs:
            q |= Q(city=city, country=country)
        for ci in CityImage.objects.filter(q):
            city_images.setdefault((ci.city, ci.country), ci)

    fallback_url = static("card_img.jpg")

    suggested_flight_cards = []
    for f in suggested_flights:
        ci = city_images.get((f.destination.city, f.destination.country))
        if ci and ci.image and not getattr(ci, "no_image_found", False):
            image_url = settings.MEDIA_URL + str(ci.image)
        else:
            image_url = fallback_url

        suggested_flight_cards.append({"flight": f, "image_url": image_url})

    return render(
        request,
        "core/home.html",
        {
            "form": form,
            "stats": stats,
            "top_origins": top_origins,
            "popular_routes": popular_routes,
            "suggested_flights": suggested_flights,
            "suggested_flight_cards": suggested_flight_cards,
            "today": timezone.localdate(),
        },
    )


def route_list(request):
    form = RouteSearchForm(request.GET or None)

    qs = Route.objects.select_related("airline", "origin", "destination").order_by("airline__name", "origin__iata_code")

    if form.is_valid():
        from_q = (form.cleaned_data.get("from_q") or "").strip()
        to_q = (form.cleaned_data.get("to_q") or "").strip()
        origin = form.cleaned_data.get("origin")
        destination = form.cleaned_data.get("destination")
        airline_q = (form.cleaned_data.get("airline_q") or "").strip()

        if airline_q:
            qs = qs.filter(
                Q(airline__name__icontains=airline_q)
                | Q(airline__iata_code__icontains=airline_q)
                | Q(airline__icao_code__icontains=airline_q)
            )

        if from_q:
            qs = qs.filter(
                Q(origin__city__icontains=from_q) |
                Q(origin__country__icontains=from_q) |
                Q(origin__iata_code__icontains=from_q)
            )

        if to_q:
            qs = qs.filter(
                Q(destination__city__icontains=to_q) |
                Q(destination__country__icontains=to_q) |
                Q(destination__iata_code__icontains=to_q)
            )

        if origin:
            qs = qs.filter(origin=origin)
        if destination:
            qs = qs.filter(destination=destination)



    paginator = Paginator(qs, 18)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "core/route_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "paginator": paginator,
        },
    )


def route_detail(request, pk: int):
    route = get_object_or_404(
        Route.objects.select_related("airline", "origin", "destination"),
        pk=pk
    )

    city_img = CityImage.objects.filter(
        city=route.destination.city,
        country=route.destination.country
    ).first()

    if city_img and city_img.image and not getattr(city_img, "no_image_found", False):
        hero_image_url = settings.MEDIA_URL + str(city_img.image)
    else:
        hero_image_url = static("card_img.jpg")

    return render(
        request,
        "core/route_detail.html",
        {"route": route, "hero_image_url": hero_image_url},
    )