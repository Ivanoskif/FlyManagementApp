from django.core.management.base import BaseCommand
from bookings.services.services import release_all_expired_reservations


class Command(BaseCommand):
    help = "Release seats by cancelling expired RESERVED bookings."

    def handle(self, *args, **options):
        released = release_all_expired_reservations()
        self.stdout.write(self.style.SUCCESS(f"Cancelled expired bookings: {released}"))
