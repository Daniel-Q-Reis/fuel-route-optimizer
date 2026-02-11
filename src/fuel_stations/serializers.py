"""Serializers for the fuel stations API."""

from typing import Any

from rest_framework import serializers


class RouteOptimizationRequestSerializer(serializers.Serializer[dict[str, float]]):  # type: ignore[misc]
    """Serializer for route optimization request."""

    start_lat = serializers.FloatField(
        min_value=-90.0,
        max_value=90.0,
        help_text="Starting latitude (-90 to 90)",
    )
    start_lon = serializers.FloatField(
        min_value=-180.0,
        max_value=180.0,
        help_text="Starting longitude (-180 to 180)",
    )
    end_lat = serializers.FloatField(
        min_value=-90.0,
        max_value=90.0,
        help_text="Ending latitude (-90 to 90)",
    )
    end_lon = serializers.FloatField(
        min_value=-180.0,
        max_value=180.0,
        help_text="Ending longitude (-180 to 180)",
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Ensure start and end coordinates are different."""
        start_lat = attrs.get("start_lat")
        start_lon = attrs.get("start_lon")
        end_lat = attrs.get("end_lat")
        end_lon = attrs.get("end_lon")

        if start_lat == end_lat and start_lon == end_lon:
            raise serializers.ValidationError(
                "Start and end coordinates must be different"
            )

        return attrs


class FuelStopSerializer(serializers.Serializer[dict[str, Any]]):  # type: ignore[misc]
    """Serializer for fuel stop information."""

    name = serializers.CharField(read_only=True)
    address = serializers.CharField(read_only=True)
    city = serializers.CharField(read_only=True)
    state = serializers.CharField(read_only=True)
    lat = serializers.FloatField(read_only=True)
    lon = serializers.FloatField(read_only=True)
    price = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    distance_from_start = serializers.FloatField(read_only=True)


class RouteGeometryPointSerializer(serializers.Serializer[dict[str, float]]):  # type: ignore[misc]
    """Serializer for route geometry point."""

    lat = serializers.FloatField(read_only=True)
    lon = serializers.FloatField(read_only=True)


class SafetyStopSerializer(serializers.Serializer[dict[str, Any]]):  # type: ignore[misc]
    """Serializer for safety stop recommendation."""

    name = serializers.CharField(read_only=True)
    city = serializers.CharField(read_only=True)
    price = serializers.FloatField(read_only=True)
    distance_miles = serializers.FloatField(read_only=True)


class SafetyInsightSerializer(serializers.Serializer[dict[str, Any]]):  # type: ignore[misc]
    """Serializer for safety insights."""

    type = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    safety_stop = SafetyStopSerializer(read_only=True, required=False)


class RouteSerializer(serializers.Serializer[dict[str, Any]]):  # type: ignore[misc]
    """Serializer for route information."""

    distance_miles = serializers.FloatField(read_only=True)
    duration_hours = serializers.FloatField(read_only=True)
    geometry = RouteGeometryPointSerializer(many=True, read_only=True)


class RouteOptimizationResponseSerializer(serializers.Serializer[dict[str, Any]]):  # type: ignore[misc]
    """Serializer for route optimization response."""

    route = RouteSerializer(read_only=True)
    fuel_stops = FuelStopSerializer(many=True, read_only=True)
    safety_insights = SafetyInsightSerializer(many=True, read_only=True)
    total_cost = serializers.FloatField(read_only=True)
    total_distance_miles = serializers.FloatField(read_only=True)
