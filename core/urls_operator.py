from django.urls import path
from core import views_operator as v

app_name = "core_op"

urlpatterns = [
    path("airports/", v.AirportListView.as_view(), name="airport_list"),
    path("airports/create/", v.AirportCreateView.as_view(), name="airport_create"),
    path("airports/<int:pk>/edit/", v.AirportUpdateView.as_view(), name="airport_edit"),
    path("airports/<int:pk>/delete/", v.AirportDeleteView.as_view(), name="airport_delete"),


    path("airlines/", v.AirlineListView.as_view(), name="airline_list"),
    path("airlines/create/", v.AirlineCreateView.as_view(), name="airline_create"),
    path("airlines/<int:pk>/edit/", v.AirlineUpdateView.as_view(), name="airline_edit"),
    path("airlines/<int:pk>/delete/", v.AirlineDeleteView.as_view(), name="airline_delete"),


    path("aircraft-models/", v.AircraftModelListView.as_view(), name="aircraft_model_list"),
    path("aircraft-models/create/", v.AircraftModelCreateView.as_view(), name="aircraft_model_create"),
    path("aircraft-models/<int:pk>/edit/", v.AircraftModelUpdateView.as_view(), name="aircraft_model_edit"),
    path("aircraft-models/<int:pk>/delete/", v.AircraftModelDeleteView.as_view(), name="aircraft_model_delete"),

    path("aircraft/", v.AircraftListView.as_view(), name="aircraft_list"),
    path("aircraft/create/", v.AircraftCreateView.as_view(), name="aircraft_create"),
    path("aircraft/<int:pk>/edit/", v.AircraftUpdateView.as_view(), name="aircraft_edit"),
    path("aircraft/<int:pk>/deactivate/", v.AircraftDeactivateView.as_view(), name="aircraft_deactivate"),

    path("crew/", v.CrewMemberListView.as_view(), name="crew_list"),
    path("crew/create/", v.CrewMemberCreateView.as_view(), name="crew_create"),
    path("crew/<int:pk>/edit/", v.CrewMemberUpdateView.as_view(), name="crew_edit"),
    path("crew/<int:pk>/deactivate/", v.CrewMemberDeactivateView.as_view(), name="crew_deactivate"),

    path("routes/", v.RouteListView.as_view(), name="route_list"),
    path("routes/create/", v.RouteCreateView.as_view(), name="route_create"),
    path("routes/<int:pk>/edit/", v.RouteUpdateView.as_view(), name="route_edit"),
    path("routes/<int:pk>/deactivate/", v.RouteDeactivateView.as_view(), name="route_deactivate"),

]
