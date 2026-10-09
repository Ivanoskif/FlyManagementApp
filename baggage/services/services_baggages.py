from __future__ import annotations
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db import models
from dataclasses import dataclass
from typing import Dict, List
from accounts.models import PassengerProfile
from bookings.models import Booking, BookingPassenger
from baggage.models import BaggageRule, BookingPassengerBaggage, BaggageType


def _membership_level_for_user(user) -> str:
    profile = getattr(user, "passenger_profile", None)
    if profile:
        return profile.membership_level
    return PassengerProfile.MembershipLevel.BASIC


def _rule(level: str, baggage_type: str) -> BaggageRule:
    rule = BaggageRule.objects.filter(
        membership_level=level,
        baggage_type=baggage_type,
        is_active=True,
    ).first()
    if not rule:
        raise ValidationError(f"Missing baggage rule for {level}/{baggage_type}.")
    return rule


@transaction.atomic
def ensure_included_baggage_for_booking(*, booking_id: int) -> None:
    booking = Booking.objects.select_for_update().select_related("user").get(id=booking_id)
    level = _membership_level_for_user(booking.user)

    passengers = list(
        BookingPassenger.objects.select_for_update()
        .filter(booking_id=booking.id)
        .order_by("id")
    )
    for p in passengers:
        _ensure_included_for_passenger(p, level)


def _ensure_included_for_passenger(passenger: BookingPassenger, level: str) -> None:
    for bt in (BaggageType.PERSONAL, BaggageType.CABIN, BaggageType.CHECKED):
        r = _rule(level, bt)
        wanted = int(r.included_pieces)

        existing_qs = BookingPassengerBaggage.objects.select_for_update().filter(
            booking_passenger_id=passenger.id,
            baggage_type=bt,
            is_included=True,
        )

        existing = existing_qs.first()
        if wanted <= 0:
            existing_qs.delete()
            continue

        total_price = Decimal("0.00")
        if existing:
            existing.pieces = wanted
            existing.max_weight_kg_per_piece = r.max_weight_kg_per_piece
            existing.max_linear_cm = r.max_linear_cm
            existing.price_eur = total_price
            existing.save(update_fields=["pieces", "max_weight_kg_per_piece", "max_linear_cm", "price_eur"])
        else:
            BookingPassengerBaggage.objects.create(
                booking_passenger_id=passenger.id,
                baggage_type=bt,
                pieces=wanted,
                max_weight_kg_per_piece=r.max_weight_kg_per_piece,
                max_linear_cm=r.max_linear_cm,
                is_included=True,
                price_eur=total_price,
            )


@transaction.atomic
def set_passenger_addons_from_post(
    *,
    booking_id: int,
    passenger_id: int,
    extra_cabin_pieces: int,
    extra_checked_pieces: int,
) -> None:
    booking = Booking.objects.select_for_update().select_related("user").get(id=booking_id)
    level = _membership_level_for_user(booking.user)

    p = BookingPassenger.objects.select_for_update().get(id=passenger_id, booking_id=booking.id)

    _set_addon(p, level, BaggageType.CABIN, extra_cabin_pieces)

    _set_addon(p, level, BaggageType.CHECKED, extra_checked_pieces)


def _set_addon(passenger: BookingPassenger, level: str, baggage_type: str, pieces: int) -> None:
    r = _rule(level, baggage_type)

    if pieces < 0:
        raise ValidationError("Invalid baggage pieces.")
    if pieces > int(r.max_additional_pieces):
        raise ValidationError(f"Max additional {baggage_type} is {r.max_additional_pieces}.")

    qs = BookingPassengerBaggage.objects.select_for_update().filter(
        booking_passenger_id=passenger.id,
        baggage_type=baggage_type,
        is_included=False,
    )

    if pieces == 0:
        qs.delete()
        return

    price_total = (Decimal(pieces) * Decimal(r.price_eur)).quantize(Decimal("0.01"))

    obj = qs.first()
    if obj:
        obj.pieces = pieces
        obj.max_weight_kg_per_piece = r.max_weight_kg_per_piece
        obj.max_linear_cm = r.max_linear_cm
        obj.price_eur = price_total
        obj.save(update_fields=["pieces", "max_weight_kg_per_piece", "max_linear_cm", "price_eur"])
    else:
        BookingPassengerBaggage.objects.create(
            booking_passenger_id=passenger.id,
            baggage_type=baggage_type,
            pieces=pieces,
            max_weight_kg_per_piece=r.max_weight_kg_per_piece,
            max_linear_cm=r.max_linear_cm,
            is_included=False,
            price_eur=price_total,
        )


@transaction.atomic
def recalc_booking_total_amount(*, booking_id: int) -> Booking:
    booking = (
        Booking.objects.select_for_update()
        .select_related("flight_fare")
        .get(id=booking_id)
    )

    if not booking.flight_fare_id:
        raise ValidationError("Booking has no flight_fare linked")

    base = (Decimal(booking.passengers_count) * Decimal(booking.flight_fare.price)).quantize(Decimal("0.01"))

    extras = (
        BookingPassengerBaggage.objects
        .filter(booking_passenger__booking_id=booking.id, is_included=False)
        .aggregate(total=models.Sum("price_eur"))
    )["total"] or Decimal("0.00")

    booking.total_amount = (base + Decimal(extras)).quantize(Decimal("0.01"))
    booking.save(update_fields=["total_amount"])
    return booking

@dataclass
class BaggageLine:
    baggage_type: str
    pieces: int
    max_weight_kg_per_piece: Decimal
    max_linear_cm: int
    is_included: bool
    price_eur: Decimal


def get_baggage_summary_for_booking(booking_id: int) -> Dict[int, List[BaggageLine]]:

    items = (
        BookingPassengerBaggage.objects
        .select_related("booking_passenger")
        .filter(booking_passenger__booking_id=booking_id)
        .order_by("booking_passenger_id", "-is_included", "baggage_type")
    )

    out: Dict[int, List[BaggageLine]] = {}
    for x in items:
        out.setdefault(x.booking_passenger_id, []).append(
            BaggageLine(
                baggage_type=x.baggage_type,
                pieces=x.pieces,
                max_weight_kg_per_piece=x.max_weight_kg_per_piece,
                max_linear_cm=x.max_linear_cm,
                is_included=x.is_included,
                price_eur=x.price_eur,
            )
        )
    return out
