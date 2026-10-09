from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView

from core.authz import operator_required
from flights.models import Flight, FareClass
from flights.forms_operator import FlightForm, FlightFareFormSet
from django.shortcuts import get_object_or_404, render
from django.core.exceptions import ValidationError

from flights.models import FlightCrewAssignment
from flights.forms_operator import AssignCrewForm
from flights.services.services_ops import assign_crew_to_flight, remove_crew_assignment

@method_decorator(operator_required, name="dispatch")
class OpFlightListView(ListView):
    model = Flight
    template_name = "flights/operator/flights/flight_list.html"
    context_object_name = "flights"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super().get_queryset()
            .select_related("airline", "origin", "destination", "aircraft", "aircraft__model")
            .prefetch_related("fares", "fares__fare_class")
            .order_by("-scheduled_departure")
        )
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(flight_number__icontains=q)
                | Q(airline__name__icontains=q)
                | Q(origin__iata_code__icontains=q)
                | Q(destination__iata_code__icontains=q)
                | Q(status__icontains=q)
                | Q(aircraft__registration_code__icontains=q)
            )
        return qs


@method_decorator(operator_required, name="dispatch")
class OpFlightCreateView(CreateView):
    model = Flight
    form_class = FlightForm
    template_name = "flights/operator/flights/flight_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            ctx["fare_formset"] = FlightFareFormSet(self.request.POST, instance=self.object)
        else:
            ctx["fare_formset"] = FlightFareFormSet(instance=self.object)

        for f in ctx["fare_formset"].forms:
            if "fare_class" in f.fields:
                f.fields["fare_class"].queryset = FareClass.objects.filter(is_active=True).order_by("code")
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        ctx = self.get_context_data()
        fare_formset = ctx["fare_formset"]

        if not fare_formset.is_valid():
            return self.form_invalid(form)

        self.object = form.save()
        fare_formset.instance = self.object
        fare_formset.save()

        messages.success(self.request, "Flight created.")
        return redirect("flights_op:flight_edit", pk=self.object.pk)


@method_decorator(operator_required, name="dispatch")
class OpFlightUpdateView(UpdateView):
    model = Flight
    form_class = FlightForm
    template_name = "flights/operator/flights/flight_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            ctx["fare_formset"] = FlightFareFormSet(self.request.POST, instance=self.object)
        else:
            ctx["fare_formset"] = FlightFareFormSet(instance=self.object)

        for f in ctx["fare_formset"].forms:
            if "fare_class" in f.fields:
                f.fields["fare_class"].queryset = FareClass.objects.filter(is_active=True).order_by("code")
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        ctx = self.get_context_data()
        fare_formset = ctx["fare_formset"]

        if not fare_formset.is_valid():
            messages.error(self.request,
                           f"Fare formset invalid: {fare_formset.non_form_errors()} {fare_formset.errors}")
            return self.form_invalid(form)

        self.object = form.save()
        fare_formset.instance = self.object
        fare_formset.save()

        messages.success(self.request, "Flight updated.")
        return redirect("flights_op:flight_edit", pk=self.object.pk)


@operator_required
def op_flight_manage_crew(request, pk: int):
    flight = get_object_or_404(
        Flight.objects.select_related("airline", "origin", "destination"),
        pk=pk,
    )

    if request.method == "POST" and request.POST.get("remove_assignment_id"):
        ass_id = int(request.POST["remove_assignment_id"])
        remove_crew_assignment(assignment_id=ass_id)
        messages.success(request, "Crew assignment removed.")
        return redirect("flights_op:flight_manage_crew", pk=flight.id)

    form = AssignCrewForm(request.POST or None)
    if request.method == "POST" and not request.POST.get("remove_assignment_id") and form.is_valid():
        try:
            assign_crew_to_flight(
                flight_id=flight.id,
                crew_member_id=form.cleaned_data["crew_member"].id,
                duty=form.cleaned_data["duty"],
            )
            messages.success(request, "Crew assigned successfully.")
            return redirect("flights_op:flight_manage_crew", pk=flight.id)
        except ValidationError as ex:
            form.add_error(None, ex.message)

    assignments = (
        FlightCrewAssignment.objects
        .filter(flight_id=flight.id)
        .select_related("crew_member")
        .order_by("crew_member__last_name", "crew_member__first_name")
    )

    return render(
        request,
        "flights/operator/flights/flight_manage_crew.html",
        {"flight": flight, "form": form, "assignments": assignments},
    )