from django.urls import path
from . import views

app_name = "checkin"

urlpatterns = [
    path("<int:booking_id>/", views.checkin_page, name="checkin_page"),
    path("<int:booking_id>/submit/", views.checkin_submit, name="checkin_submit"),

    path("<int:booking_id>/boarding-pass.pdf", views.boarding_pass_pdf, name="boarding_pass_pdf"),
]
