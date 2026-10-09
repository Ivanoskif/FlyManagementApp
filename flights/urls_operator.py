from django.urls import path
from flights import views_operator as v

app_name = "flights_op"

urlpatterns = [
    path("flights/", v.OpFlightListView.as_view(), name="flight_list"),
    path("flights/create/", v.OpFlightCreateView.as_view(), name="flight_create"),
    path("flights/<int:pk>/edit/", v.OpFlightUpdateView.as_view(), name="flight_edit"),
    path("flights/<int:pk>/crew/", v.op_flight_manage_crew, name="flight_manage_crew"),


]
