from __future__ import annotations

from core.models import Airport
from flights.services.airport_search import find_airports
from flights.services.flight_search import search_flights

from flights.services.flight_calendar import (
    find_available_flight_days,
)


def find_airports_tool(query: str) -> list[dict]:
    """
    Find airports matching a city, airport name, IATA code, ICAO code,
    or country.

    Args:
        query: Airport search text, for example Skopje, London, LHR or Paris.

    Returns:
        A list of matching active airports.
    """

    return find_airports(query)


def search_flights_tool(
    origin_airport_id: int,
    destination_airport_id: int,
    departure_date: str,
    passengers: int = 1,
    fare_class_id: int | None = None,
    max_price: float | None = None,
    max_stops: int | None = None,
    departure_after: str | None = None,
    arrival_before: str | None = None,
    sort_by: str | None = None,
) -> list[dict]:
    """
    Search available flights between two airports.

    The search can return direct flights and flights with one connection.
    Only flights with enough available seats are returned.

    Args:
        origin_airport_id: Database ID of the origin airport.
        destination_airport_id: Database ID of the destination airport.
        departure_date: Departure date in YYYY-MM-DD format.
        passengers: Number of passengers.
        fare_class_id: Optional fare class database ID.
        max_price: Optional maximum total price in EUR for all passengers.
        max_stops: Maximum number of stops. Use 0 for direct flights only.
        departure_after: Optional earliest departure time in HH:MM format.
        arrival_before: Optional latest arrival time in HH:MM format.
        sort_by: Optional sorting. Use "price" for cheapest or "duration"
            for fastest.

    Returns:
        Available flight options with prices, times, segments and
        connection information.
    """

    try:
        origin = Airport.objects.get(
            id=origin_airport_id,
            is_active=True,
        )
    except Airport.DoesNotExist:
        return {
            "error": "Origin airport does not exist or is inactive."
        }

    try:
        destination = Airport.objects.get(
            id=destination_airport_id,
            is_active=True,
        )
    except Airport.DoesNotExist:
        return {
            "error": "Destination airport does not exist or is inactive."
        }

    return search_flights(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        passengers=passengers,
        fare_class_id=fare_class_id,
        max_price=max_price,
        max_stops=max_stops,
        departure_after=departure_after,
        arrival_before=arrival_before,
        sort_by=sort_by,
    )


def find_flight_days_tool(
    origin_airport_id: int,
    destination_airport_id: int,
    year: int,
    month: int,
    passengers: int = 1,
    max_stops: int | None = None,
) -> dict:
    """
    Find all dates in a month for which at least one available
    flight option exists between two airports.
    """

    try:
        origin = Airport.objects.get(
            id=origin_airport_id,
            is_active=True,
        )
    except Airport.DoesNotExist:
        return {
            "error": "Origin airport does not exist or is inactive."
        }

    try:
        destination = Airport.objects.get(
            id=destination_airport_id,
            is_active=True,
        )
    except Airport.DoesNotExist:
        return {
            "error": "Destination airport does not exist or is inactive."
        }

    dates = find_available_flight_days(
        origin=origin,
        destination=destination,
        year=year,
        month=month,
        passengers=passengers,
        max_stops=max_stops,
    )

    return {
        "origin": origin.iata_code,
        "destination": destination.iata_code,
        "year": year,
        "month": month,
        "available_dates": dates,
        "count": len(dates),
    }