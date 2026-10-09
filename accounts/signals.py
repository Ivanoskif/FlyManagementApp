from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import PassengerProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_passenger_profile_and_default_role(sender, instance, created, **kwargs):
    if not created:
        return

    passenger_group, _ = Group.objects.get_or_create(name="Passenger")
    instance.groups.add(passenger_group)

    PassengerProfile.objects.get_or_create(
        user=instance,
        defaults={
            "first_name": instance.first_name or "",
            "last_name": instance.last_name or "",
        },
    )
