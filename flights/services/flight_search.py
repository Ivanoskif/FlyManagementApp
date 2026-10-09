from __future__ import annotations

from datetime import date, time, timedelta, datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from decimal import Decimal

from django.db.models import Prefetch

from flights.models import Flight, FlightFare


MIN_CONNECTION_MINUTES = 60
MAX_CONNECTION_HOURS = 6
MAX_RESULTS = 20

def _get_timezone(timezone_name: str | None) -> ZoneInfo:
    """
    Returns a valid timezone.

    If an airport has an invalid/missing timezone,
    UTC is used as a safe fallback.
    """

    try:
        return ZoneInfo(timezone_name or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _to_local_datetime(dt_value, timezone_name: str | None):
    """
    Convert an aware datetime to the airport's local timezone.
    """

    timezone_obj = _get_timezone(timezone_name)
    return dt_value.astimezone(timezone_obj)


def _departure_date_utc_range(
    departure_date: date,
    origin,
):
    """
    Convert one local calendar day at the origin airport
    into a UTC datetime range.

    Example:
        2026-01-19 in Berlin
        is converted to the corresponding UTC start/end.
    """

    origin_timezone = _get_timezone(origin.timezone)

    local_start = datetime.combine(
        departure_date,
        time.min,
        tzinfo=origin_timezone,
    )

    local_end = local_start + timedelta(days=1)

    utc_start = local_start.astimezone(dt_timezone.utc)
    utc_end = local_end.astimezone(dt_timezone.utc)

    return utc_start, utc_end


def _normalize_date(value) -> date:
    if isinstance(value, date):
        return value

    if isinstance(value, str):
        return date.fromisoformat(value)

    raise ValueError("departure_date must be a date or YYYY-MM-DD string.")


def _normalize_time(value) -> time | None:
    if value is None:
        return None

    if isinstance(value, time):
        return value

    if isinstance(value, str):
        return time.fromisoformat(value)

    raise ValueError("Time value must be HH:MM or a time object.")


def _normalize_price(value) -> Decimal | None:
    if value is None:
        return None

    return Decimal(str(value))


def _available_fare(
    flight: Flight,
    *,
    passengers: int,
    fare_class_id: int | None = None,
):
    """
    Returns the cheapest available fare for the requested number
    of passengers.

    If fare_class_id is provided, only that fare class is considered.
    """

    fares = list(flight.fares.all())

    if fare_class_id is not None:
        fares = [
            fare
            for fare in fares
            if fare.fare_class_id == fare_class_id
        ]

    available_options = []

    for fare in fares:
        available_seats = fare.seats_allocated - fare.seats_sold

        if available_seats < passengers:
            continue

        available_options.append(
            {
                "fare": fare,
                "available_seats": available_seats,
            }
        )

    if not available_options:
        return None

    available_options.sort(
        key=lambda item: item["fare"].price
    )

    best = available_options[0]

    return {
        "fare": best["fare"],
        "available_seats": best["available_seats"],
    }


def _segment_data(
    flight: Flight,
    fare_data: dict,
    passengers: int,
):
    fare = fare_data["fare"]

    price_per_passenger = fare.price
    total_segment_price = price_per_passenger * passengers

    duration = flight.scheduled_arrival - flight.scheduled_departure
    duration_minutes = int(duration.total_seconds() // 60)

    local_departure = _to_local_datetime(
        flight.scheduled_departure,
        flight.origin.timezone,
    )

    local_arrival = _to_local_datetime(
        flight.scheduled_arrival,
        flight.destination.timezone,
    )

    return {
        "flight_id": flight.id,
        "flight_number": flight.flight_number,

        "airline": {
            "id": flight.airline_id,
            "name": flight.airline.name,
            "iata_code": flight.airline.iata_code,
        },

        "origin": {
            "id": flight.origin_id,
            "iata_code": flight.origin.iata_code,
            "city": flight.origin.city,
            "country": flight.origin.country,
            "name": flight.origin.name,
        },

        "destination": {
            "id": flight.destination_id,
            "iata_code": flight.destination.iata_code,
            "city": flight.destination.city,
            "country": flight.destination.country,
            "name": flight.destination.name,
        },

        "scheduled_departure": local_departure.isoformat(),
        "scheduled_arrival": local_arrival.isoformat(),

        "departure_timezone": flight.origin.timezone,
        "arrival_timezone": flight.destination.timezone,

        "duration_minutes": duration_minutes,

        "fare": {
            "fare_class_id": fare.fare_class_id,
            "fare_class_code": fare.fare_class.code,
            "fare_class_name": fare.fare_class.name,
            "price_per_passenger": str(price_per_passenger),
            "available_seats": fare_data["available_seats"],
        },

        "segment_total_price": str(total_segment_price),
    }


def _build_direct_result(
    flight: Flight,
    fare_data: dict,
    passengers: int,
):
    segment = _segment_data(
        flight,
        fare_data,
        passengers,
    )

    price_per_passenger = fare_data["fare"].price
    total_price = price_per_passenger * passengers

    duration = flight.scheduled_arrival - flight.scheduled_departure
    duration_minutes = int(duration.total_seconds() // 60)

    return {
        "type": "direct",
        "stops": 0,

        "segments": [
            segment,
        ],

        "price_per_passenger": str(price_per_passenger),
        "total_price": str(total_price),

        "total_duration_minutes": duration_minutes,
        "connection_minutes": None,

        "_sort_price": total_price,
        "_sort_duration": duration_minutes,
        "_sort_departure": flight.scheduled_departure,
    }


def _build_connection_result(
    first_flight: Flight,
    second_flight: Flight,
    first_fare_data: dict,
    second_fare_data: dict,
    passengers: int,
):
    first_segment = _segment_data(
        first_flight,
        first_fare_data,
        passengers,
    )

    second_segment = _segment_data(
        second_flight,
        second_fare_data,
        passengers,
    )

    first_price = first_fare_data["fare"].price
    second_price = second_fare_data["fare"].price

    price_per_passenger = first_price + second_price
    total_price = price_per_passenger * passengers

    total_duration = (
        second_flight.scheduled_arrival
        - first_flight.scheduled_departure
    )

    total_duration_minutes = int(
        total_duration.total_seconds() // 60
    )

    connection_duration = (
        second_flight.scheduled_departure
        - first_flight.scheduled_arrival
    )

    connection_minutes = int(
        connection_duration.total_seconds() // 60
    )

    return {
        "type": "connecting",
        "stops": 1,

        "segments": [
            first_segment,
            second_segment,
        ],

        "connection_airport": {
            "id": first_flight.destination_id,
            "iata_code": first_flight.destination.iata_code,
            "city": first_flight.destination.city,
            "country": first_flight.destination.country,
            "name": first_flight.destination.name,
        },

        "price_per_passenger": str(price_per_passenger),
        "total_price": str(total_price),

        "total_duration_minutes": total_duration_minutes,
        "connection_minutes": connection_minutes,

        "_sort_price": total_price,
        "_sort_duration": total_duration_minutes,
        "_sort_departure": first_flight.scheduled_departure,
    }


def search_flights(
    *,
    origin,
    destination,
    departure_date,
    passengers: int = 1,
    fare_class_id: int | None = None,
    max_price=None,
    max_stops: int | None = None,
    departure_after=None,
    arrival_before=None,
    sort_by: str | None = None,
):
    """
    Search direct flights and routes with one connection.

    origin and destination are Airport objects.

    Supported filters:
        passengers
        fare_class_id
        max_price
        max_stops
        departure_after
        arrival_before
        sort_by = "price" or "duration"

    Current version supports:
        direct flights
        maximum one connection
    """

    if passengers < 1:
        raise ValueError("passengers must be >= 1.")

    departure_date = _normalize_date(departure_date)
    departure_after = _normalize_time(departure_after)
    arrival_before = _normalize_time(arrival_before)
    max_price = _normalize_price(max_price)

    if origin.id == destination.id:
        return []

    if max_stops is not None and max_stops < 0:
        raise ValueError("max_stops cannot be negative.")

    if sort_by not in {None, "price", "duration"}:
        raise ValueError(
            "sort_by must be 'price', 'duration' or None."
        )

    fare_queryset = (
        FlightFare.objects
        .select_related("fare_class")
        .order_by("price")
    )

    base_queryset = (
        Flight.objects
        .select_related(
            "airline",
            "origin",
            "destination",
        )
        .prefetch_related(
            Prefetch(
                "fares",
                queryset=fare_queryset,
            )
        )
        .exclude(status=Flight.Status.CANCELLED)
    )

    utc_start, utc_end = _departure_date_utc_range(
        departure_date,
        origin,
    )

    first_leg_queryset = (
        base_queryset
        .filter(
            origin=origin,
            scheduled_departure__gte=utc_start,
            scheduled_departure__lt=utc_end,
        )
        .order_by("scheduled_departure")
    )

    first_legs = list(first_leg_queryset)

    results = []

    # ---------------------------------------------------------
    # DIRECT FLIGHTS
    # ---------------------------------------------------------

    for flight in first_legs:
        if flight.destination_id != destination.id:
            continue

        if departure_after:
            local_departure = _to_local_datetime(
                flight.scheduled_departure,
                flight.origin.timezone,
            )

            if local_departure.time() < departure_after:
                continue

        if arrival_before:
            local_arrival = _to_local_datetime(
                flight.scheduled_arrival,
                flight.destination.timezone,
            )

            if local_arrival.time() > arrival_before:
                continue

        fare_data = _available_fare(
            flight,
            passengers=passengers,
            fare_class_id=fare_class_id,
        )

        if not fare_data:
            continue

        result = _build_direct_result(
            flight,
            fare_data,
            passengers,
        )

        if (
            max_price is not None
            and result["_sort_price"] > max_price
        ):
            continue

        results.append(result)

    # Ако корисникот бара само директни летови
    if max_stops == 0:
        return _finalize_results(
            results,
            sort_by=sort_by,
        )

    # ---------------------------------------------------------
    # FIRST LEGS FOR CONNECTING FLIGHTS
    # ---------------------------------------------------------

    possible_first_legs = [
        flight
        for flight in first_legs
        if flight.destination_id != destination.id
        and flight.destination_id != origin.id
    ]

    if possible_first_legs:

        connection_airport_ids = {
            flight.destination_id
            for flight in possible_first_legs
        }

        earliest_second_departure = min(
            flight.scheduled_arrival
            for flight in possible_first_legs
        ) + timedelta(minutes=MIN_CONNECTION_MINUTES)

        latest_second_departure = max(
            flight.scheduled_arrival
            for flight in possible_first_legs
        ) + timedelta(hours=MAX_CONNECTION_HOURS)

        second_legs = list(
            base_queryset
            .filter(
                origin_id__in=connection_airport_ids,
                destination=destination,
                scheduled_departure__gte=earliest_second_departure,
                scheduled_departure__lte=latest_second_departure,
            )
            .order_by("scheduled_departure")
        )

        second_legs_by_origin = {}

        for flight in second_legs:
            second_legs_by_origin.setdefault(
                flight.origin_id,
                [],
            ).append(flight)

        # -----------------------------------------------------
        # CREATE CONNECTION COMBINATIONS
        # -----------------------------------------------------

        for first_flight in possible_first_legs:

            if departure_after:
                local_first_departure = _to_local_datetime(
                    first_flight.scheduled_departure,
                    first_flight.origin.timezone,
                )

                if local_first_departure.time() < departure_after:
                    continue

            first_fare_data = _available_fare(
                first_flight,
                passengers=passengers,
                fare_class_id=fare_class_id,
            )

            if not first_fare_data:
                continue

            candidates = second_legs_by_origin.get(
                first_flight.destination_id,
                [],
            )

            minimum_second_departure = (
                first_flight.scheduled_arrival
                + timedelta(minutes=MIN_CONNECTION_MINUTES)
            )

            maximum_second_departure = (
                first_flight.scheduled_arrival
                + timedelta(hours=MAX_CONNECTION_HOURS)
            )

            for second_flight in candidates:

                if (
                    second_flight.scheduled_departure
                    < minimum_second_departure
                ):
                    continue

                if (
                    second_flight.scheduled_departure
                    > maximum_second_departure
                ):
                    continue

                if arrival_before:
                    local_final_arrival = _to_local_datetime(
                        second_flight.scheduled_arrival,
                        second_flight.destination.timezone,
                    )

                    if local_final_arrival.time() > arrival_before:
                        continue

                second_fare_data = _available_fare(
                    second_flight,
                    passengers=passengers,
                    fare_class_id=fare_class_id,
                )

                if not second_fare_data:
                    continue

                result = _build_connection_result(
                    first_flight,
                    second_flight,
                    first_fare_data,
                    second_fare_data,
                    passengers,
                )

                if (
                    max_price is not None
                    and result["_sort_price"] > max_price
                ):
                    continue

                results.append(result)

    return _finalize_results(
        results,
        sort_by=sort_by,
    )


def _finalize_results(
    results: list[dict],
    *,
    sort_by: str | None,
):
    if sort_by == "price":
        results.sort(
            key=lambda item: (
                item["_sort_price"],
                item["_sort_duration"],
            )
        )

    elif sort_by == "duration":
        results.sort(
            key=lambda item: (
                item["_sort_duration"],
                item["_sort_price"],
            )
        )

    else:
        results.sort(
            key=lambda item: (
                item["stops"],
                item["_sort_departure"],
                item["_sort_price"],
            )
        )

    results = results[:MAX_RESULTS]

    for result in results:
        result.pop("_sort_price", None)
        result.pop("_sort_duration", None)
        result.pop("_sort_departure", None)

    return results