from django.contrib import admin

# Register your models here.
from .models import PassengerProfile

@admin.register(PassengerProfile)
class PassengerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "first_name", "last_name", "membership_level", "phone", "nationality")
    list_filter = ("membership_level", "nationality")
    search_fields = ("user__username", "user__email", "first_name", "last_name", "document_no")
