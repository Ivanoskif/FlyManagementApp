from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import List, Dict

from django.db.models import Sum, Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone

from bookings.models import Booking
from flights.models import Flight, FlightFare


@dataclass
class FlightRow:
    flight_id: int
    flight_number: str
    origin: str
    destination: str
    departure: datetime
    status: str
    pax_paid: int
    revenue_paid: Decimal
    capacity: int
    load_factor: Decimal


def _dt_range(from_date: date, to_date: date):
    start = datetime.combine(from_date, time.min)
    end = datetime.combine(to_date, time.max)
    if timezone.is_naive(start):
        start = timezone.make_aware(start)
    if timezone.is_naive(end):
        end = timezone.make_aware(end)
    return start, end


def _period_trunc(group_by: str, field_name: str):
    if group_by == "week":
        return TruncWeek(field_name)
    if group_by == "month":
        return TruncMonth(field_name)
    return TruncDay(field_name)


def flights_count_by_period(*, from_date: date, to_date: date, group_by: str = "day"):
    start, end = _dt_range(from_date, to_date)
    trunc = _period_trunc(group_by, "scheduled_departure")

    qs = (
        Flight.objects.filter(scheduled_departure__range=(start, end))
        .annotate(period=trunc)
        .values("period")
        .annotate(cnt=Count("id"))
        .order_by("period")
    )
    return list(qs)


def revenue_by_period(*, from_date: date, to_date: date, group_by: str = "day"):
    start, end = _dt_range(from_date, to_date)
    trunc = _period_trunc(group_by, "flight__scheduled_departure")

    qs = (
        Booking.objects.filter(
            status=Booking.Status.PAID,
            flight__scheduled_departure__range=(start, end),
        )
        .annotate(period=trunc)
        .values("period")
        .annotate(revenue=Sum("total_amount"), pax=Sum("passengers_count"))
        .order_by("period")
    )
    return list(qs)


def revenue_by_route(*, from_date: date, to_date: date):
    start, end = _dt_range(from_date, to_date)

    qs = (
        Booking.objects.filter(
            status=Booking.Status.PAID,
            flight__scheduled_departure__range=(start, end),
        )
        .values(
            "flight__origin__iata_code",
            "flight__destination__iata_code",
        )
        .annotate(
            revenue=Sum("total_amount"),
            pax=Sum("passengers_count"),
            bookings=Count("id"),
        )
        .order_by("-revenue")
    )
    return list(qs)


def flight_capacity_map(*, flight_ids: List[int]) -> Dict[int, int]:

    if not flight_ids:
        return {}

    qs = (
        FlightFare.objects.filter(flight_id__in=flight_ids)
        .values("flight_id")
        .annotate(capacity=Sum("seats_allocated"))
    )
    return {x["flight_id"]: int(x["capacity"] or 0) for x in qs}


def top_flights_with_load_factor(*, from_date: date, to_date: date, limit: int = 20) -> List[FlightRow]:
    start, end = _dt_range(from_date, to_date)

    paid = (
        Booking.objects.filter(
            status=Booking.Status.PAID,
            flight__scheduled_departure__range=(start, end),
        )
        .values("flight_id")
        .annotate(pax_paid=Sum("passengers_count"), revenue_paid=Sum("total_amount"))
    )
    paid_map = {x["flight_id"]: x for x in paid}

    flights = list(
        Flight.objects.filter(scheduled_departure__range=(start, end))
        .select_related("origin", "destination")
        .order_by("-scheduled_departure")[:500]
    )
    flight_ids = [f.id for f in flights]
    cap_map = flight_capacity_map(flight_ids=flight_ids)

    out: List[FlightRow] = []
    for f in flights:
        agg = paid_map.get(f.id) or {}
        pax = int(agg.get("pax_paid") or 0)
        rev = agg.get("revenue_paid") or Decimal("0.00")
        cap = int(cap_map.get(f.id) or 0)

        lf = Decimal("0.00")
        if cap > 0:
            lf = (Decimal(pax) / Decimal(cap))

        out.append(
            FlightRow(
                flight_id=f.id,
                flight_number=f.flight_number,
                origin=f.origin.iata_code,
                destination=f.destination.iata_code,
                departure=f.scheduled_departure,
                status=f.status,
                pax_paid=pax,
                revenue_paid=Decimal(rev),
                capacity=cap,
                load_factor=lf,
            )
        )

    out.sort(key=lambda x: (x.revenue_paid, x.pax_paid), reverse=True)
    return out[:limit]