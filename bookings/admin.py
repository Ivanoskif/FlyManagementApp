from django.contrib import admin

# Register your models here.

from .models import Booking, BookingPassenger, Payment, Refund, Ticket
from bookings.services.services_payments import mark_payment_success
from bookings.services.services_refunds import approve_refund, complete_refund

class BookingPassengerInline(admin.TabularInline):
    model = BookingPassenger
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


class RefundInline(admin.TabularInline):
    model = Refund
    extra = 0


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("booking_code", "user", "flight", "fare_class", "passengers_count", "status", "total_amount", "currency", "created_at")
    list_filter = ("status", "fare_class", "currency")
    search_fields = ("booking_code", "user__username", "user__email", "flight__flight_number")
    date_hierarchy = "created_at"
    inlines = [BookingPassengerInline, PaymentInline, RefundInline]


@admin.register(BookingPassenger)
class BookingPassengerAdmin(admin.ModelAdmin):
    list_display = ("booking", "first_name", "last_name", "document_type", "document_no", "date_of_birth")
    search_fields = ("booking__booking_code", "first_name", "last_name", "document_no")
    list_filter = ("document_type",)

@admin.action(description="Mark selected payments as SUCCESS (issue ticket)")
def admin_mark_success(modeladmin, request, queryset):
    for payment in queryset:
        try:
            mark_payment_success(payment_id=payment.id)
        except Exception as ex:
            modeladmin.message_user(request, f"Payment {payment.id} failed: {ex}", level="ERROR")

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "amount", "method", "status", "paid_at", "created_at")
    list_filter = ("status", "method")
    search_fields = ("booking__booking_code", "provider_ref")
    actions = [admin_mark_success]

@admin.action(description="Approve selected refunds")
def admin_approve_refunds(modeladmin, request, queryset):
    for r in queryset:
        try:
            approve_refund(refund_id=r.id)
        except Exception as ex:
            modeladmin.message_user(request, f"Refund {r.id} approve failed: {ex}", level="ERROR")


@admin.action(description="Complete selected refunds (release seats, update booking/ticket)")
def admin_complete_refunds(modeladmin, request, queryset):
    for r in queryset:
        try:
            complete_refund(refund_id=r.id)
        except Exception as ex:
            modeladmin.message_user(request, f"Refund {r.id} complete failed: {ex}", level="ERROR")



@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "amount", "status", "refunded_at", "created_at")
    list_filter = ("status",)
    search_fields = ("booking__booking_code",)
    actions = [admin_approve_refunds, admin_complete_refunds]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_number", "booking", "status", "issued_at")
    list_filter = ("status",)
    search_fields = ("ticket_number", "booking__booking_code")


