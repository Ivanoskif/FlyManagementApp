from django.urls import path, include
from . import views

app_name = "flights"

urlpatterns = [
    path("", views.flight_list, name="flight_list"),
    path("<int:pk>/", views.flight_detail, name="flight_detail"),

# operator/admin ops
    path("<int:pk>/ops/delay/", views.flight_delay, name="flight_delay"),
    path("<int:pk>/ops/reschedule/", views.flight_reschedule, name="flight_reschedule"),
    path("<int:pk>/ops/cancel/", views.flight_cancel, name="flight_cancel"),
    path("<int:pk>/ops/status/", views.flight_set_status, name="flight_set_status"),

]
