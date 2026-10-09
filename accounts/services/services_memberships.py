from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import PassengerProfile


_LEVEL_ORDER = {
    PassengerProfile.MembershipLevel.BASIC: 1,
    PassengerProfile.MembershipLevel.PLUS: 2,
    PassengerProfile.MembershipLevel.PREMIUM: 3,
}


@transaction.atomic
def upgrade_membership(*, user, target_level: str, provider_ref: str | None = None) -> PassengerProfile:
    profile = PassengerProfile.objects.select_for_update().get(user=user)

    current = profile.membership_level
    if _LEVEL_ORDER[target_level] <= _LEVEL_ORDER[current]:
        raise ValidationError(f"Cannot upgrade to {target_level}. Current level is {current}.")

    profile.membership_level = target_level
    profile.save(update_fields=["membership_level"])
    return profile
