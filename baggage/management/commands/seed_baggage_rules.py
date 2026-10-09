from decimal import Decimal
from django.core.management.base import BaseCommand
from accounts.models import PassengerProfile
from baggage.models import BaggageRule, BaggageType


class Command(BaseCommand):
    def handle(self, *args, **options):
        BASIC = PassengerProfile.MembershipLevel.BASIC
        PLUS = PassengerProfile.MembershipLevel.PLUS
        PREMIUM = PassengerProfile.MembershipLevel.PREMIUM

        rules = [
            dict(membership_level=BASIC, baggage_type=BaggageType.PERSONAL, included_pieces=1, max_weight_kg_per_piece=Decimal("0.00"), max_linear_cm=90, price_eur=Decimal("0.00"), max_additional_pieces=0),
            dict(membership_level=PLUS, baggage_type=BaggageType.PERSONAL, included_pieces=1, max_weight_kg_per_piece=Decimal("0.00"), max_linear_cm=90, price_eur=Decimal("0.00"), max_additional_pieces=0),
            dict(membership_level=PREMIUM, baggage_type=BaggageType.PERSONAL, included_pieces=1, max_weight_kg_per_piece=Decimal("0.00"), max_linear_cm=90, price_eur=Decimal("0.00"), max_additional_pieces=0),

            dict(membership_level=BASIC, baggage_type=BaggageType.CABIN, included_pieces=0, max_weight_kg_per_piece=Decimal("10.00"), max_linear_cm=115, price_eur=Decimal("30.00"), max_additional_pieces=1),
            dict(membership_level=PLUS, baggage_type=BaggageType.CABIN, included_pieces=1, max_weight_kg_per_piece=Decimal("10.00"), max_linear_cm=115, price_eur=Decimal("30.00"), max_additional_pieces=1),
            dict(membership_level=PREMIUM, baggage_type=BaggageType.CABIN, included_pieces=1, max_weight_kg_per_piece=Decimal("10.00"), max_linear_cm=115, price_eur=Decimal("30.00"), max_additional_pieces=1),

            dict(membership_level=BASIC, baggage_type=BaggageType.CHECKED, included_pieces=0, max_weight_kg_per_piece=Decimal("20.00"), max_linear_cm=158, price_eur=Decimal("50.00"), max_additional_pieces=1),
            dict(membership_level=PLUS, baggage_type=BaggageType.CHECKED, included_pieces=0, max_weight_kg_per_piece=Decimal("20.00"), max_linear_cm=158, price_eur=Decimal("50.00"), max_additional_pieces=1),
            dict(membership_level=PREMIUM, baggage_type=BaggageType.CHECKED, included_pieces=1, max_weight_kg_per_piece=Decimal("20.00"), max_linear_cm=158, price_eur=Decimal("50.00"), max_additional_pieces=1),
        ]

        created = 0
        updated = 0

        for r in rules:
            obj, was_created = BaggageRule.objects.update_or_create(
                membership_level=r["membership_level"],
                baggage_type=r["baggage_type"],
                defaults=r,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Seed done. Created: {created}, Updated: {updated}"))
