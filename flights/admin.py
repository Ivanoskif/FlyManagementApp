from django.contrib import admin

# Register your models here.

from .models import FareClass, Flight, FlightFare, FlightCrewAssignment


@admin.register(FareClass)
class FareClassAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "refund_policy", "is_active")
    list_filter = ("refund_policy", "is_active")
    search_fields = ("code", "name")


class FlightFareInline(admin.TabularInline):
    model = FlightFare
    extra = 0


class FlightCrewAssignmentInline(admin.TabularInline):
    model = FlightCrewAssignment
    extra = 0


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = (
        "flight_number",
        "airline",
        "origin",
        "destination",
        "scheduled_departure",
        "scheduled_arrival",
        "status",
        "aircraft",
    )
    list_filter = ("status", "airline", "origin", "destination")
    search_fields = ("flight_number", "origin__iata_code", "destination__iata_code", "airline__name")
    date_hierarchy = "scheduled_departure"
    inlines = [FlightFareInline, FlightCrewAssignmentInline]


@admin.register(FlightFare)
class FlightFareAdmin(admin.ModelAdmin):
    list_display = ("flight", "fare_class", "price", "seats_allocated", "seats_sold")
    list_filter = ("fare_class",)
    search_fields = ("flight__flight_number", "fare_class__code")


@admin.register(FlightCrewAssignment)
class FlightCrewAssignmentAdmin(admin.ModelAdmin):
    list_display = ("flight", "crew_member", "duty", "assigned_at")
    list_filter = ("duty",)
    search_fields = ("flight__flight_number", "crew_member__first_name", "crew_member__last_name")




