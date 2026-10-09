from calendar import monthrange
from datetime import date

from flights.services.flight_search import search_flights


def find_available_flight_days(
    *,
    origin,
    destination,
    year: int,
    month: int,
    passengers: int = 1,
    max_stops: int | None = None,
) -> list[str]:
    """
    Return all dates in a given month for which at least one
    available flight option exists.
    """

    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12.")

    if passengers < 1:
        raise ValueError("passengers must be >= 1.")

    number_of_days = monthrange(year, month)[1]

    available_dates = []

    for day in range(1, number_of_days + 1):

        departure_date = date(
            year,
            month,
            day,
        )

        results = search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            passengers=passengers,
            max_stops=max_stops,
        )

        if results:
            available_dates.append(
                departure_date.isoformat()
            )

    return available_dates