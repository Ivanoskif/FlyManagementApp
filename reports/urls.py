from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("ops/", views.operator_dashboard, name="operator_dashboard"),
    path("ops/export.csv", views.export_bookings_csv, name="export_bookings_csv"),
    path("ops/export.xlsx", views.export_bookings_xlsx, name="export_bookings_xlsx"),
]
