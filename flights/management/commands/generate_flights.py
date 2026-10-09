import random
from datetime import datetime, timedelta, time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Route
from flights.models import Flight, FareClass, FlightFare


def _make_aware(dt: datetime) -> datetime:
    if timezone.is_aware(dt):
        return dt
    return timezone.make_aware(dt, timezone.get_current_timezone())


def _rand_time():
    hour = random.randint(5, 22)
    minute = random.choice([0, 10, 15, 20, 30, 40, 45, 50])
    return time(hour=hour, minute=minute)


def _rand_duration_minutes():
    return random.randint(50, 240)


def _ensure_fare_classes():
    defaults = [
        ("ECONOMY", "Economy", FareClass.RefundPolicy.PARTIAL),
        ("PREMIUM", "Premium", FareClass.RefundPolicy.PARTIAL),
        ("BUSINESS", "Business", FareClass.RefundPolicy.FLEX),
    ]
    created = 0
    for code, name, policy in defaults:
        obj, was_created = FareClass.objects.get_or_create(
            code=code,
            defaults={"name": name, "refund_policy": policy, "is_active": True},
        )
        if not was_created:
            if not obj.is_active:
                obj.is_active = True
                obj.save(update_fields=["is_active"])
        else:
            created += 1
    return created


def _gen_flight_number(airline):
    prefix = (airline.iata_code or airline.icao_code or "FLY").upper()
    prefix = prefix[:3]
    return f"{prefix}{random.randint(100, 9999)}"


@transaction.atomic
def _create_flight_for_route(route, depart_dt, seats_total=180):
    duration = _rand_duration_minutes()
    arrive_dt = depart_dt + timedelta(minutes=duration)

    for _ in range(20):
        fn = _gen_flight_number(route.airline)
        if not Flight.objects.filter(flight_number=fn, scheduled_departure=depart_dt).exists():
            break
    else:
        return None

    flight = Flight.objects.create(
        flight_number=fn,
        airline=route.airline,
        origin=route.origin,
        destination=route.destination,
        scheduled_departure=depart_dt,
        scheduled_arrival=arrive_dt,
        status=Flight.Status.PLANNED,
        aircraft=None,
        base_price=0,
    )

    econ = int(seats_total * 0.75)
    prem = int(seats_total * 0.15)
    bus = seats_total - econ - prem

    base = random.randint(35, 220)
    fares = [
        ("ECONOMY", float(base), econ),
        ("PREMIUM", float(base * 1.4), prem),
        ("BUSINESS", float(base * 2.2), bus),
    ]

    for code, price, alloc in fares:
        fc = FareClass.objects.get(code=code)
        FlightFare.objects.create(
            flight=flight,
            fare_class=fc,
            price=price,
            seats_allocated=max(0, alloc),
            seats_sold=0,
        )

    return flight


class Command(BaseCommand):
    help = "Generate Flight + FlightFare entries from existing Routes."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=14, help="How many future days to generate flights for.")
        parser.add_argument("--max-flights", type=int, default=120, help="Total max flights to generate.")
        parser.add_argument("--routes-sample", type=int, default=0, help="Use only N random routes (0=all routes).")
        parser.add_argument("--per-route", type=int, default=1, help="How many flights per route per day (avg).")
        parser.add_argument("--seed", type=int, default=0, help="Random seed (0=none).")

    def handle(self, *args, **opts):
        if opts["seed"]:
            random.seed(opts["seed"])

        created_fareclasses = _ensure_fare_classes()
        if created_fareclasses:
            self.stdout.write(self.style.SUCCESS(f"Fare classes created: {created_fareclasses}"))

        days = max(1, opts["days"])
        max_flights = max(1, opts["max_flights"])
        per_route = max(1, opts["per_route"])
        routes_sample = max(0, opts["routes_sample"])

        routes_qs = Route.objects.select_related("airline", "origin", "destination").filter(is_active=True)
        routes = list(routes_qs)

        if not routes:
            self.stdout.write(self.style.ERROR("No routes found. Seed routes first."))
            return

        if routes_sample and routes_sample < len(routes):
            routes = random.sample(routes, routes_sample)

        start_date = timezone.localdate()
        created = 0

        for d in range(days):
            if created >= max_flights:
                break

            day = start_date + timedelta(days=d)

            day_routes = routes[:]
            random.shuffle(day_routes)

            for route in day_routes:
                if created >= max_flights:
                    break

                chance = 0.45 if per_route == 1 else 0.75
                if random.random() > chance:
                    continue

                t = _rand_time()
                depart_dt = _make_aware(datetime.combine(day, t))

                flight = _create_flight_for_route(route, depart_dt)
                if flight:
                    created += 1

        self.stdout.write(self.style.SUCCESS(f"Flights generated: {created}"))
