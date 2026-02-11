"""URL configuration for fuel_stations app."""

from django.urls import path

from fuel_stations.views import OptimizeRouteView

app_name = "fuel_stations"

urlpatterns = [
    path("api/v1/optimize-route/", OptimizeRouteView.as_view(), name="optimize-route"),
]
