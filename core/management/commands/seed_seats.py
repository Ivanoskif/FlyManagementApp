from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import AircraftModel, AircraftSeat


class Command(BaseCommand):
    help = "Generate default seats (A-F layout) for AircraftModel(s)."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Generate seats for all aircraft models")
        parser.add_argument("--model-id", type=int, default=0, help="Generate seats for a single AircraftModel id")
        parser.add_argument("--overwrite", action="store_true", help="Delete existing seats before generating")
        parser.add_argument("--extra-rows", type=str, default="1,12", help="Comma-separated row numbers for extra legroom")

    @transaction.atomic
    def handle(self, *args, **opts):
        do_all = opts["all"]
        model_id = opts["model_id"]
        overwrite = opts["overwrite"]

        extra_rows = set()
        raw = (opts["extra_rows"] or "").strip()
        if raw:
            for part in raw.split(","):
                part = part.strip()
                if part.isdigit():
                    extra_rows.add(int(part))

        if do_all:
            qs = AircraftModel.objects.all()
        elif model_id:
            qs = AircraftModel.objects.filter(id=model_id)
        else:
            self.stdout.write(self.style.ERROR("Provide --all or --model-id=<id>"))
            return

        letters = ["A", "B", "C", "D", "E", "F"]
        window = {"A", "F"}
        aisle = {"C", "D"}

        created_total = 0
        skipped = 0

        for model in qs:
            if overwrite:
                model.seats.all().delete()
            else:
                if model.seats.exists():
                    skipped += 1
                    continue

            total = int(model.default_total_seats or 0)
            if total <= 0:
                skipped += 1
                continue

            to_create = []
            seat_counter = 0
            row = 1

            while seat_counter < total:
                for letter in letters:
                    if seat_counter >= total:
                        break

                    if letter in window:
                        seat_type = AircraftSeat.SeatType.WINDOW
                    elif letter in aisle:
                        seat_type = AircraftSeat.SeatType.AISLE
                    else:
                        seat_type = AircraftSeat.SeatType.MIDDLE

                    code = f"{row}{letter}"

                    to_create.append(
                        AircraftSeat(
                            aircraft_model=model,
                            seat_code=code,
                            row_number=row,
                            seat_letter=letter,
                            seat_type=seat_type,
                            is_extra_legroom=(row in extra_rows),
                        )
                    )

                    seat_counter += 1
                row += 1

            AircraftSeat.objects.bulk_create(to_create, batch_size=2000)
            created_total += len(to_create)

        self.stdout.write(self.style.SUCCESS(f"Seats created: {created_total}. Models skipped: {skipped}."))
