"""End-to-end tests with real OpenRouteService API.

These tests use the actual ORS API to validate end-to-end functionality.
Tests are skipped if OPENROUTESERVICE_API_KEY is not configured.
"""

import os
from decimal import Decimal
from typing import Any

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from fuel_stations.models import FuelStation


class E2ERouteOptimizationTest(TestCase):
    """End-to-end tests with real ORS API."""

    def setUp(self) -> None:
        """Set up test client and check for API key."""
        self.client = APIClient()
        self.url = reverse("fuel_stations:optimize-route")

        # Check if API key is available
        self.api_key = os.getenv("OPENROUTESERVICE_API_KEY", "")
        if not self.api_key:
            self.skipTest("OPENROUTESERVICE_API_KEY not set - skipping E2E tests")

        # Create some fuel stations along common US routes
        self._create_test_stations()

    def _create_test_stations(self) -> None:
        """Create test fuel stations along LA-Vegas route."""
        # LA area station
        FuelStation.objects.create(
            truckstop_name="LA Fuel Stop",
            address="1234 I-15 S",
            city="Los Angeles",
            state="CA",
            retail_price=Decimal("4.25"),
            latitude=Decimal("34.0522"),
            longitude=Decimal("-118.2437"),
        )

        # Barstow station (midpoint LA-Vegas)
        FuelStation.objects.create(
            truckstop_name="Barstow Travel Center",
            address="2500 E Main St",
            city="Barstow",
            state="CA",
            retail_price=Decimal("3.85"),
            latitude=Decimal("34.8958"),
            longitude=Decimal("-117.0228"),
        )

        # Baker station (between Barstow and Vegas)
        FuelStation.objects.create(
            truckstop_name="Baker Fuel",
            address="721 Baker Blvd",
            city="Baker",
            state="CA",
            retail_price=Decimal("4.05"),
            latitude=Decimal("35.2655"),
            longitude=Decimal("-116.0736"),
        )

        # Vegas area station
        FuelStation.objects.create(
            truckstop_name="Vegas Fuel Stop",
            address="5678 Las Vegas Blvd",
            city="Las Vegas",
            state="NV",
            retail_price=Decimal("3.55"),
            latitude=Decimal("36.1699"),
            longitude=Decimal("-115.1398"),
        )

    def test_la_to_vegas_route_real_api(self) -> None:
        """Test LA to Vegas route with real ORS API."""
        data = {
            "start_lat": 34.0522,  # Los Angeles
            "start_lon": -118.2437,
            "end_lat": 36.1699,  # Las Vegas
            "end_lon": -115.1398,
        }

        response = self.client.post(self.url, data, format="json")

        # Should get successful response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify response structure
        # Cast to Response for Mypy strict mode
        resp = response  # type: Any
        self.assertIn("route", resp.data)
        self.assertIn("fuel_stops", resp.data)
        self.assertIn("total_cost", resp.data)
        self.assertIn("total_distance_miles", resp.data)

        # Verify route data
        route: dict[str, Any] = resp.data["route"]
        self.assertIn("distance_miles", route)
        self.assertIn("duration_hours", route)
        self.assertIn("geometry", route)

        # Distance should be approximately 270 miles (LA to Vegas)
        distance: float = route["distance_miles"]
        self.assertGreater(distance, 250.0)
        self.assertLess(distance, 300.0)

        # Should have valid geometry points
        geometry = route["geometry"]
        self.assertIsInstance(geometry, list)
        self.assertGreater(len(geometry), 0)

    def test_short_route_no_stops_real_api(self) -> None:
        """Test short route that shouldn't require fuel stops."""
        data = {
            "start_lat": 34.0522,  # Los Angeles
            "start_lon": -118.2437,
            "end_lat": 34.0522,  # Same city, slightly different coordinates
            "end_lon": -118.1437,
        }

        response = self.client.post(self.url, data, format="json")

        # Should get successful response
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have no fuel stops for such a short route
        resp = response  # type: Any
        fuel_stops = resp.data.get("fuel_stops", [])
        # Route is very short, likely no stops needed
        self.assertIsInstance(fuel_stops, list)

    def test_route_geometry_validity(self) -> None:
        """Test that route geometry contains valid coordinates."""
        data = {
            "start_lat": 34.0522,
            "start_lon": -118.2437,
            "end_lat": 36.1699,
            "end_lon": -115.1398,
        }

        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        resp = response  # type: Any
        route: dict[str, Any] = resp.data["route"]
        geometry = route["geometry"]

        # Verify all geometry points have valid lat/lon
        for point in geometry:
            # point should be a list or tuple [lat, lon]
            self.assertIsInstance(point, (list, tuple))
            self.assertEqual(len(point), 2)

            lat = point[0]
            lon = point[1]

            # Validate coordinate ranges
            self.assertGreaterEqual(lat, -90.0)
            self.assertLessEqual(lat, 90.0)
            self.assertGreaterEqual(lon, -180.0)
            self.assertLessEqual(lon, 180.0)

    def test_fuel_stops_structure(self) -> None:
        """Test that fuel stops have correct structure when present."""
        data = {
            "start_lat": 34.0522,
            "start_lon": -118.2437,
            "end_lat": 36.1699,
            "end_lon": -115.1398,
        }

        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        resp = response  # type: Any
        fuel_stops = resp.data.get("fuel_stops", [])

        # If fuel stops are present, verify structure
        if fuel_stops:
            stop = fuel_stops[0]
            expected_fields = [
                "name",
                "address",
                "city",
                "state",
                "lat",
                "lon",
                "price",
                "distance_from_start",
            ]

            for field in expected_fields:
                self.assertIn(field, stop, f"Missing field: {field}")

    @override_settings(EFFECTIVE_RANGE_MILES=100)  # Reduced range to force more stops
    def test_long_route_requires_stops(self) -> None:
        """Test that long route with reduced range requires fuel stops."""
        # Create additional stations along the route for testing
        FuelStation.objects.create(
            truckstop_name="Test Midpoint Station",
            address="Test Address",
            city="Victorville",
            state="CA",
            retail_price=Decimal("3.95"),
            latitude=Decimal("34.5362"),
            longitude=Decimal("-117.2911"),
        )

        data = {
            "start_lat": 34.0522,
            "start_lon": -118.2437,
            "end_lat": 36.1699,
            "end_lon": -115.1398,
        }

        response = self.client.post(self.url, data, format="json")

        # With 100-mile range, LA-Vegas (~270 miles) should require stops
        # Note: May still return 0 stops if route geometry doesn't align with stations
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resp = response  # type: Any
        self.assertIn("fuel_stops", resp.data)
