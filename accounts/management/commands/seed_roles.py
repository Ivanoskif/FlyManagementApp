from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


ROLE_NAMES = ["Admin", "Operator", "Passenger"]


class Command(BaseCommand):
    help = "Create default roles for the system."

    def handle(self, *args, **options):
        for role in ROLE_NAMES:
            group, created = Group.objects.get_or_create(name=role)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created group: {role}"))
            else:
                self.stdout.write(f"Group already exists: {role}")

        self.stdout.write(self.style.SUCCESS("Done."))
