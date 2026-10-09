from django.urls import path
from . import views

app_name = "bookings"

urlpatterns = [
    path("create/<int:flight_id>/", views.booking_create, name="booking_create"),
    path("my/", views.my_bookings, name="my_bookings"),
    path("<int:pk>/", views.booking_detail, name="booking_detail"),
    path("<int:pk>/passengers/", views.booking_passengers, name="booking_passengers"),
    path("<int:pk>/pay/", views.booking_pay, name="booking_pay"),
    path("<int:pk>/cancel/", views.booking_cancel, name="booking_cancel"),

    path("<int:pk>/refund/request/", views.refund_request_view, name="refund_request"),
    path("refunds/", views.refund_queue_view, name="refund_queue"),
    path("refunds/<int:refund_id>/approve/", views.refund_approve_view, name="refund_approve"),
    path("refunds/<int:refund_id>/reject/", views.refund_reject_view, name="refund_reject"),
    path("refunds/<int:refund_id>/complete/", views.refund_complete_view, name="refund_complete"),

    path("<int:pk>/demo-pay/", views.demo_payment, name="demo_payment"),

    path("<int:pk>/seats/", views.booking_seats, name="booking_seats"),

    path("<int:pk>/check-in/", views.booking_check_in, name="booking_check_in"),

]
