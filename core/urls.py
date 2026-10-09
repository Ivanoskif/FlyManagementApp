from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("routes/", views.route_list, name="route_list"),
    path("routes/<int:pk>/", views.route_detail, name="route_detail"),
]
