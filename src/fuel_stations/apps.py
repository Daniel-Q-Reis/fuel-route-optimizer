"""Fuel Stations Django App Configuration."""

from django.apps import AppConfig


class FuelStationsConfig(AppConfig):
    """Configuration for the fuel_stations app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "fuel_stations"
    verbose_name = "Fuel Stations"
