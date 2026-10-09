import csv
import io
import urllib.request

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Airport, Airline, Route


AIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
AIRLINES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"
ROUTES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"


def _download_text(url: str) -> str:
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode("utf-8", errors="replace")


class Command(BaseCommand):
    help = "Seed Airports, Airlines, Routes from OpenFlights dataset (free)."

    def add_arguments(self, parser):
        parser.add_argument("--limit-airports", type=int, default=0)
        parser.add_argument("--limit-airlines", type=int, default=0)
        parser.add_argument("--limit-routes", type=int, default=0)

    @transaction.atomic
    def handle(self, *args, **opts):
        lim_airports = opts["limit_airports"]
        lim_airlines = opts["limit_airlines"]
        lim_routes = opts["limit_routes"]

        self.stdout.write("Downloading OpenFlights files...")
        airports_txt = _download_text(AIRPORTS_URL)
        airlines_txt = _download_text(AIRLINES_URL)
        routes_txt = _download_text(ROUTES_URL)

        self._seed_airports(airports_txt, lim_airports)
        self._seed_airlines(airlines_txt, lim_airlines)
        self._seed_routes(routes_txt, lim_routes)

        self.stdout.write(self.style.SUCCESS("Seed completed."))

    def _seed_airports(self, text: str, limit: int):
        self.stdout.write("Seeding airports...")

        reader = csv.reader(io.StringIO(text))
        to_create = []
        seen = set(Airport.objects.values_list("iata_code", flat=True))

        count = 0
        for row in reader:
            # airports.dat fields:
            # 0 Airport ID
            # 1 Name
            # 2 City
            # 3 Country
            # 4 IATA
            # 5 ICAO
            # 6 Latitude
            # 7 Longitude
            # 8 Altitude
            # 9 Timezone
            # 10 DST
            # 11 TZ database time zone
            # 12 type
            # 13 source

            if len(row) < 12:
                continue

            name = row[1].strip()
            city = row[2].strip()
            country = row[3].strip()
            iata = (row[4] or "").strip()
            icao = (row[5] or "").strip() or None
            lat = row[6].strip() or None
            lon = row[7].strip() or None
            tz = (row[11] or "").strip() or "UTC"
            kind = (row[12] or "").strip()

            if not iata or iata == r"\N" or len(iata) != 3:
                continue
            if kind and kind not in ("airport",):
                continue
            if iata in seen:
                continue

            to_create.append(
                Airport(
                    name=name[:200],
                    city=city[:120] or "Unknown",
                    country=country[:120] or "Unknown",
                    iata_code=iata,
                    icao_code=icao,
                    timezone=tz[:64],
                    latitude=float(lat) if lat else None,
                    longitude=float(lon) if lon else None,
                    is_active=True,
                )
            )
            seen.add(iata)
            count += 1

            if limit and count >= limit:
                break

        Airport.objects.bulk_create(to_create, batch_size=2000)
        self.stdout.write(self.style.SUCCESS(f"Airports created: {len(to_create)}"))

    def _seed_airlines(self, text: str, limit: int):
        self.stdout.write("Seeding airlines...")

        reader = csv.reader(io.StringIO(text))
        existing_iata = set(Airline.objects.exclude(iata_code__isnull=True).values_list("iata_code", flat=True))
        existing_icao = set(Airline.objects.exclude(icao_code__isnull=True).values_list("icao_code", flat=True))

        to_create = []
        count = 0
        for row in reader:
            # airlines.dat fields:
            # 0 Airline ID
            # 1 Name
            # 2 Alias
            # 3 IATA
            # 4 ICAO
            # 5 Callsign
            # 6 Country
            # 7 Active (Y/N)

            if len(row) < 8:
                continue

            name = row[1].strip()
            iata = (row[3] or "").strip()
            icao = (row[4] or "").strip()
            callsign = (row[5] or "").strip() or None
            active = (row[7] or "").strip()

            if not name:
                continue

            if iata in ("", r"\N"):
                iata = None
            if icao in ("", r"\N"):
                icao = None

            if iata and iata in existing_iata:
                iata = None
            if icao and icao in existing_icao:
                icao = None

            to_create.append(
                Airline(
                    name=name[:200],
                    iata_code=iata,
                    icao_code=icao,
                    callsign=callsign,
                    is_active=(active == "Y"),
                )
            )
            if iata:
                existing_iata.add(iata)
            if icao:
                existing_icao.add(icao)

            count += 1
            if limit and count >= limit:
                break

        Airline.objects.bulk_create(to_create, batch_size=2000, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"Airlines attempted: {len(to_create)} (duplicates ignored)"))

    def _seed_routes(self, text: str, limit: int):
        self.stdout.write("Seeding routes...")

        airport_by_iata = dict(Airport.objects.values_list("iata_code", "id"))
        airline_by_iata = dict(Airline.objects.exclude(iata_code__isnull=True).values_list("iata_code", "id"))
        airline_by_icao = dict(Airline.objects.exclude(icao_code__isnull=True).values_list("icao_code", "id"))

        reader = csv.reader(io.StringIO(text))
        to_create = []
        count = 0

        # routes.dat fields:
        # 0 airline (IATA or ICAO sometimes)
        # 1 airline_id
        # 2 source_airport (IATA)
        # 3 source_airport_id
        # 4 destination_airport (IATA)
        # 5 destination_airport_id
        # 6 codeshare
        # 7 stops
        # 8 equipment

        for row in reader:
            if len(row) < 6:
                continue

            air_code = (row[0] or "").strip()
            src = (row[2] or "").strip()
            dst = (row[4] or "").strip()

            if air_code in ("", r"\N") or src in ("", r"\N") or dst in ("", r"\N"):
                continue
            if src == dst:
                continue

            origin_id = airport_by_iata.get(src)
            dest_id = airport_by_iata.get(dst)
            if not origin_id or not dest_id:
                continue

            airline_id = airline_by_iata.get(air_code) or airline_by_icao.get(air_code)
            if not airline_id:
                continue

            to_create.append(
                Route(
                    airline_id=airline_id,
                    origin_id=origin_id,
                    destination_id=dest_id,
                    is_active=True,
                )
            )
            count += 1
            if limit and count >= limit:
                break

        Route.objects.bulk_create(to_create, batch_size=5000, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"Routes attempted: {len(to_create)} (duplicates ignored)"))
