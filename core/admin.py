from django.contrib import admin
from .models import Airport, Airline, AircraftModel, Aircraft, CrewMember, Route, AircraftSeat
from django.db import transaction

# Register your models here.

@admin.register(Airline)
class AirlineAdmin(admin.ModelAdmin):
    list_display = ("name", "iata_code", "icao_code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "iata_code", "icao_code")


@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ("iata_code", "name", "city", "country", "timezone", "is_active")
    list_filter = ("country", "is_active")
    search_fields = ("iata_code", "icao_code", "name", "city", "country")
    ordering = ("country", "city", "iata_code")

class AircraftSeatInline(admin.TabularInline):
    model = AircraftSeat
    extra = 0
    fields = ("seat_code", "row_number", "seat_letter", "seat_type", "is_extra_legroom")
    readonly_fields = ("seat_code",)
    ordering = ("row_number", "seat_letter")

@admin.register(AircraftModel)
class AircraftModelAdmin(admin.ModelAdmin):
    list_display = ("manufacturer", "model_name", "default_total_seats", "is_active")
    list_filter = ("manufacturer", "is_active")
    search_fields = ("manufacturer", "model_name")
    inlines = [AircraftSeatInline]
    actions = ["generate_default_seats"]

    @admin.action(description="Generate seats (A-F) for selected aircraft models")
    def generate_default_seats(self, request, queryset):
        created_total = 0

        letters = ["A", "B", "C", "D", "E", "F"]
        window = {"A", "F"}
        aisle = {"C", "D"}
        extra_rows = {1, 12}

        with transaction.atomic():
            for model in queryset:
                if model.seats.exists():
                    continue

                total = int(model.default_total_seats or 0)
                if total <= 0:
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

        self.message_user(request, f"Seats created: {created_total}")


@admin.register(Aircraft)
class AircraftAdmin(admin.ModelAdmin):
    list_display = ("registration_code", "airline", "model", "status")
    list_filter = ("status", "airline")
    search_fields = ("registration_code", "model__model_name", "airline__name")


@admin.register(CrewMember)
class CrewMemberAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "role", "status", "airline")
    list_filter = ("role", "status", "airline")
    search_fields = ("first_name", "last_name", "email", "license_no")
    

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("airline", "origin", "destination", "is_active")
    list_filter = ("airline", "is_active", "origin__country", "destination__country")
    search_fields = ("airline__name", "origin__iata_code", "destination__iata_code", "origin__city", "destination__city")



