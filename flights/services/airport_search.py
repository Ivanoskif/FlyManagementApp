from django.db.models import Q

from core.models import Airport


MAX_AIRPORT_RESULTS = 10


def find_airports(query: str) -> list[dict]:
    """
    Find active airports by:
    - exact IATA code
    - exact ICAO code
    - airport name
    - city
    - country
    """

    query = (query or "").strip()

    if not query:
        return []

    exact_matches = (
        Airport.objects
        .filter(is_active=True)
        .filter(
            Q(iata_code__iexact=query)
            | Q(icao_code__iexact=query)
        )
        .order_by("city", "iata_code")
    )

    if exact_matches.exists():
        airports = exact_matches

    else:

        airports = (
            Airport.objects
            .filter(is_active=True)
            .filter(
                Q(name__icontains=query)
                | Q(city__icontains=query)
                | Q(country__icontains=query)
            )
            .order_by("city", "iata_code")
        )

    results = []

    for airport in airports[:MAX_AIRPORT_RESULTS]:
        results.append(
            {
                "id": airport.id,
                "iata_code": airport.iata_code,
                "icao_code": airport.icao_code,
                "name": airport.name,
                "city": airport.city,
                "country": airport.country,
                "timezone": airport.timezone,
            }
        )

    return results