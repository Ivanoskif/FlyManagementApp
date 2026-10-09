from __future__ import annotations
import os
import re
from urllib.parse import urlparse
import requests
from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from core.models import CityImage
from flights.models import Flight

WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = "FlyManagement/1.0"


def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    return s or "x"


def get_wiki_thumb(city: str, country: str | None) -> str | None:
    titles = []
    if country:
        titles.append(f"{city}, {country}")
    titles.append(city)

    for t in titles:
        try:
            params = {
                "action": "query",
                "format": "json",
                "prop": "pageimages",
                "piprop": "thumbnail",
                "pithumbsize": 900,
                "titles": t,
                "redirects": 1,
            }
            r = requests.get(WIKI_API, params=params, headers={"User-Agent": UA}, timeout=8)
            if r.status_code != 200:
                continue
            data = r.json()
            pages = (data.get("query") or {}).get("pages") or {}
            for _, page in pages.items():
                src = ((page or {}).get("thumbnail") or {}).get("source")
                if src:
                    return src
        except Exception:
            continue
    return None


def guess_ext(url: str) -> str:
    path = urlparse(url).path.lower()
    if path.endswith(".png"):
        return "png"
    if path.endswith(".webp"):
        return "webp"
    return "jpg"


@transaction.atomic
def save_city_image(city: str, country: str | None) -> CityImage:
    city = (city or "").strip()
    country = (country or "").strip() or None

    obj, _ = CityImage.objects.select_for_update().get_or_create(
        city=city, country=country, defaults={"no_image_found": False}
    )

    if obj.image:
        return obj

    thumb = get_wiki_thumb(city, country)
    if not thumb:
        obj.no_image_found = True
        obj.save(update_fields=["no_image_found"])
        return obj

    cities_dir = os.path.join(settings.MEDIA_ROOT, "cities")
    os.makedirs(cities_dir, exist_ok=True)

    ext = guess_ext(thumb)
    filename = f"{slugify(city)}_{slugify(country or 'xx')}.{ext}"
    file_path = os.path.join(cities_dir, filename)

    resp = requests.get(thumb, stream=True, headers={"User-Agent": UA}, timeout=12)
    if resp.status_code != 200:
        obj.no_image_found = True
        obj.save(update_fields=["no_image_found"])
        return obj

    with open(file_path, "wb") as f:
        for chunk in resp.iter_content(8192):
            if chunk:
                f.write(chunk)

    with open(file_path, "rb") as f:
        obj.image.save(f"cities/{filename}", File(f), save=True)

    obj.no_image_found = False
    obj.save(update_fields=["no_image_found"])
    return obj


class Command(BaseCommand):
    help = "Manually download city images (Wikipedia thumbnails) for unique destination cities used in Flights."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=200)

    def handle(self, *args, **opts):
        limit = opts["limit"]

        rows = (
            Flight.objects.select_related("destination")
            .values(city=F("destination__city"), country=F("destination__country"))
            .distinct()
        )[:limit]

        self.stdout.write(f"Found {len(rows)} unique destination cities")

        ok = 0
        no = 0

        for r in rows:
            ci = save_city_image(r["city"], r["country"])
            if ci.image:
                ok += 1
                self.stdout.write(self.style.SUCCESS(f"OK  {ci.city}, {ci.country} -> {ci.image.name}"))
            else:
                no += 1
                self.stdout.write(self.style.WARNING(f"NO  {ci.city}, {ci.country} (no image)"))

        self.stdout.write(self.style.SUCCESS(f"Done. Downloaded: {ok}, Missing: {no}"))
        self.stdout.write(f"Saved under: {settings.MEDIA_ROOT}/cities/")
