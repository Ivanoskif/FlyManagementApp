from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from core.authz import operator_required

from core.forms_operator import AirportForm, AirlineForm, AircraftModelForm, AircraftForm, CrewMemberForm, RouteForm
from core.models import Airport, Airline, AircraftModel, Aircraft, CrewMember, Route



@method_decorator(operator_required, name="dispatch")
class AirportListView(ListView):
    model = Airport
    template_name = "core/operator/airports/airport_list.html"
    context_object_name = "airports"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(city__icontains=q)
                | Q(country__icontains=q)
                | Q(iata_code__icontains=q)
                | Q(icao_code__icontains=q)
            )
        return qs


@method_decorator(operator_required, name="dispatch")
class AirportCreateView(CreateView):
    model = Airport
    form_class = AirportForm
    template_name = "core/operator/airports/airport_form.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Airport created.")
        return resp

    def get_success_url(self):
        return reverse("core_op:airport_list")


@method_decorator(operator_required, name="dispatch")
class AirportUpdateView(UpdateView):
    model = Airport
    form_class = AirportForm
    template_name = "core/operator/airports/airport_form.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Airport updated.")
        return resp

    def get_success_url(self):
        return reverse("core_op:airport_list")


@method_decorator(operator_required, name="dispatch")
class AirportDeleteView(DeleteView):
    model = Airport
    template_name = "core/operator/airports/airport_confirm_delete.html"

    def post(self, request, *args, **kwargs):
        # ако сакаш "soft delete": само is_active=False
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        messages.success(request, "Airport deactivated.")
        return redirect("core_op:airport_list")

    def get_success_url(self):
        return reverse("core_op:airport_list")

@method_decorator(operator_required, name="dispatch")
class AirlineListView(ListView):
    model = Airline
    template_name = "core/operator/airlines/airline_list.html"
    context_object_name = "airlines"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(iata_code__icontains=q)
                | Q(icao_code__icontains=q)
                | Q(callsign__icontains=q)
            )
        return qs


@method_decorator(operator_required, name="dispatch")
class AirlineCreateView(CreateView):
    model = Airline
    form_class = AirlineForm
    template_name = "core/operator/airlines/airline_form.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Airline created.")
        return resp

    def get_success_url(self):
        return reverse("core_op:airline_list")


@method_decorator(operator_required, name="dispatch")
class AirlineUpdateView(UpdateView):
    model = Airline
    form_class = AirlineForm
    template_name = "core/operator/airlines/airline_form.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Airline updated.")
        return resp

    def get_success_url(self):
        return reverse("core_op:airline_list")


@method_decorator(operator_required, name="dispatch")
class AirlineDeleteView(DeleteView):
    model = Airline
    template_name = "core/operator/airlines/airline_confirm_delete.html"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        messages.success(request, "Airline deactivated.")
        return redirect("core_op:airline_list")

    def get_success_url(self):
        return reverse("core_op:airline_list")

@method_decorator(operator_required, name="dispatch")
class AircraftModelListView(ListView):
    model = AircraftModel
    template_name = "core/operator/aircraft_models/aircraft_model_list.html"
    context_object_name = "models"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(manufacturer__icontains=q)
                | Q(model_name__icontains=q)
            )
        return qs


@method_decorator(operator_required, name="dispatch")
class AircraftModelCreateView(CreateView):
    model = AircraftModel
    form_class = AircraftModelForm
    template_name = "core/operator/aircraft_models/aircraft_model_form.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Aircraft model created.")
        return resp

    def get_success_url(self):
        return reverse("core_op:aircraft_model_list")


@method_decorator(operator_required, name="dispatch")
class AircraftModelUpdateView(UpdateView):
    model = AircraftModel
    form_class = AircraftModelForm
    template_name = "core/operator/aircraft_models/aircraft_model_form.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Aircraft model updated.")
        return resp

    def get_success_url(self):
        return reverse("core_op:aircraft_model_list")


@method_decorator(operator_required, name="dispatch")
class AircraftModelDeleteView(DeleteView):
    model = AircraftModel
    template_name = "core/operator/aircraft_models/aircraft_model_confirm_delete.html"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        messages.success(request, "Aircraft model deactivated.")
        return redirect("core_op:aircraft_model_list")

    def get_success_url(self):
        return reverse("core_op:aircraft_model_list")

@method_decorator(operator_required, name="dispatch")
class AircraftListView(ListView):
    model = Aircraft
    template_name = "core/operator/aircraft/aircraft_list.html"
    context_object_name = "aircraft_list"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super().get_queryset()
            .select_related("airline", "model")
        )
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(registration_code__icontains=q)
                | Q(airline__name__icontains=q)
                | Q(model__manufacturer__icontains=q)
                | Q(model__model_name__icontains=q)
                | Q(status__icontains=q)
            )
        return qs


@method_decorator(operator_required, name="dispatch")
class AircraftCreateView(CreateView):
    model = Aircraft
    form_class = AircraftForm
    template_name = "core/operator/aircraft/aircraft_form.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Aircraft created.")
        return resp

    def get_success_url(self):
        return reverse("core_op:aircraft_list")


@method_decorator(operator_required, name="dispatch")
class AircraftUpdateView(UpdateView):
    model = Aircraft
    form_class = AircraftForm
    template_name = "core/operator/aircraft/aircraft_form.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Aircraft updated.")
        return resp

    def get_success_url(self):
        return reverse("core_op:aircraft_list")


@method_decorator(operator_required, name="dispatch")
class AircraftDeactivateView(DeleteView):
    model = Aircraft
    template_name = "core/operator/aircraft/aircraft_confirm_deactivate.html"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.status = Aircraft.Status.OUT_OF_SERVICE
        obj.save(update_fields=["status"])
        messages.success(request, "Aircraft set to OUT_OF_SERVICE.")
        return redirect("core_op:aircraft_list")

    def get_success_url(self):
        return reverse("core_op:aircraft_list")

@method_decorator(operator_required, name="dispatch")
class CrewMemberListView(ListView):
    model = CrewMember
    template_name = "core/operator/crew/crew_list.html"
    context_object_name = "crew"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("airline")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(license_no__icontains=q)
                | Q(role__icontains=q)
                | Q(airline__name__icontains=q)
            )
        return qs.order_by("last_name", "first_name")


@method_decorator(operator_required, name="dispatch")
class CrewMemberCreateView(CreateView):
    model = CrewMember
    form_class = CrewMemberForm
    template_name = "core/operator/crew/crew_form.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Crew member created.")
        return resp

    def get_success_url(self):
        return reverse("core_op:crew_list")


@method_decorator(operator_required, name="dispatch")
class CrewMemberUpdateView(UpdateView):
    model = CrewMember
    form_class = CrewMemberForm
    template_name = "core/operator/crew/crew_form.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Crew member updated.")
        return resp

    def get_success_url(self):
        return reverse("core_op:crew_list")


@method_decorator(operator_required, name="dispatch")
class CrewMemberDeactivateView(DeleteView):
    model = CrewMember
    template_name = "core/operator/crew/crew_confirm_deactivate.html"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.status = CrewMember.Status.INACTIVE
        obj.save(update_fields=["status"])
        messages.success(request, "Crew member set to INACTIVE.")
        return redirect("core_op:crew_list")

    def get_success_url(self):
        return reverse("core_op:crew_list")


@method_decorator(operator_required, name="dispatch")
class RouteListView(ListView):
    model = Route
    template_name = "core/operator/routes/route_list.html"
    context_object_name = "routes"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super().get_queryset()
            .select_related("airline", "origin", "destination")
        )
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(airline__name__icontains=q)
                | Q(origin__iata_code__icontains=q)
                | Q(destination__iata_code__icontains=q)
                | Q(origin__city__icontains=q)
                | Q(destination__city__icontains=q)
            )
        return qs


@method_decorator(operator_required, name="dispatch")
class RouteCreateView(CreateView):
    model = Route
    form_class = RouteForm
    template_name = "core/operator/routes/route_form.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Route created.")
        return resp

    def get_success_url(self):
        return reverse("core_op:route_list")


@method_decorator(operator_required, name="dispatch")
class RouteUpdateView(UpdateView):
    model = Route
    form_class = RouteForm
    template_name = "core/operator/routes/route_form.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Route updated.")
        return resp

    def get_success_url(self):
        return reverse("core_op:route_list")


@method_decorator(operator_required, name="dispatch")
class RouteDeactivateView(DeleteView):
    model = Route
    template_name = "core/operator/routes/route_confirm_deactivate.html"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        messages.success(request, "Route deactivated.")
        return redirect("core_op:route_list")

    def get_success_url(self):
        return reverse("core_op:route_list")
