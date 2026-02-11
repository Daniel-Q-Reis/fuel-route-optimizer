"""API integration tests for route optimization endpoint."""

from decimal import Decimal
from typing import Any, Protocol, cast
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from fuel_stations.clients.openrouteservice import RouteNotFoundError
from fuel_stations.models import FuelStation
from fuel_stations.services.route_optimizer import InsufficientStationsError


class DRFResponse(Protocol):
    """Protocol for DRF response objects in tests."""

    data: Any
    status_code: int


class OptimizeRouteAPITest(TestCase):
    """Test cases for the optimize route API endpoint."""

    def setUp(self) -> None:
        """Set up test client and test data."""
        self.client = APIClient()
        self.url = reverse("fuel_stations:optimize-route")

        # Create test fuel stations
        FuelStation.objects.create(
            truckstop_name="Test Station 1",
            address="123 Test Rd",
            city="Test City",
            state="CA",
            retail_price=Decimal("3.45"),
            latitude=Decimal("34.05"),
            longitude=Decimal("-118.25"),
        )
        FuelStation.objects.create(
            truckstop_name="Test Station 2",
            address="456 Test Ave",
            city="Test Town",
            state="NV",
            retail_price=Decimal("3.75"),
            latitude=Decimal("36.17"),
            longitude=Decimal("-115.14"),
        )

    @patch("fuel_stations.views.RouteOptimizationService")
    def test_successful_route_optimization(self, mock_service_class: MagicMock) -> None:
        """Test successful route optimization with valid coordinates."""
        # Mock service response
        mock_service = MagicMock()
        mock_service.optimize_route.return_value = {
            "route": {
                "distance_miles": 250.0,
                "duration_hours": 4.0,
                "geometry": [
                    {"lat": 34.05, "lon": -118.25},
                    {"lat": 36.17, "lon": -115.14},
                ],
            },
            "fuel_stops": [
                {
                    "name": "Test Station",
                    "address": "123 Test Rd",
                    "city": "Test City",
                    "state": "CA",
                    "lat": 35.0,
                    "lon": -117.0,
                    "price": Decimal("3.50"),
                    "distance_from_start": 125.0,
                }
            ],
            "total_cost": 87.5,
            "total_distance_miles": 250.0,
        }
        mock_service_class.return_value = mock_service

        # Make request
        data = {
            "start_lat": 34.05,
            "start_lon": -118.25,
            "end_lat": 36.17,
            "end_lon": -115.14,
        }
        response = self.client.post(self.url, data, format="json")

        # Assertions
        res: DRFResponse = cast(DRFResponse, response)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("route", res.data)
        self.assertIn("fuel_stops", res.data)
        self.assertIn("total_cost", res.data)
        self.assertEqual(res.data["total_distance_miles"], 250.0)

    def test_invalid_latitude_validation(self) -> None:
        """Test validation error for invalid latitude."""
        data = {
            "start_lat": 95.0,  # Invalid: > 90
            "start_lon": -118.25,
            "end_lat": 36.17,
            "end_lon": -115.14,
        }
        response = self.client.post(self.url, data, format="json")

        res: DRFResponse = cast(DRFResponse, response)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_lat", res.data)

    def test_invalid_longitude_validation(self) -> None:
        """Test validation error for invalid longitude."""
        data = {
            "start_lat": 34.05,
            "start_lon": -200.0,  # Invalid: < -180
            "end_lat": 36.17,
            "end_lon": -115.14,
        }
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_lon", response.data)  # type: ignore[attr-defined]

    def test_same_start_end_coordinates(self) -> None:
        """Test validation error when start and end are the same."""
        data = {
            "start_lat": 34.05,
            "start_lon": -118.25,
            "end_lat": 34.05,
            "end_lon": -118.25,
        }
        response = self.client.post(self.url, data, format="json")

        res: DRFResponse = cast(DRFResponse, response)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", res.data)

    @patch("fuel_stations.views.RouteOptimizationService")
    def test_route_not_found_error(self, mock_service_class: MagicMock) -> None:
        """Test 404 response when route cannot be found."""
        mock_service = MagicMock()
        mock_service.optimize_route.side_effect = RouteNotFoundError(
            "No route available"
        )
        mock_service_class.return_value = mock_service

        data = {
            "start_lat": 0.0,
            "start_lon": 0.0,
            "end_lat": 90.0,
            "end_lon": 0.0,
        }
        response = self.client.post(self.url, data, format="json")

        res: DRFResponse = cast(DRFResponse, response)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", res.data)
        self.assertIn("Route not found", res.data["error"])

    @patch("fuel_stations.views.RouteOptimizationService")
    def test_insufficient_stations_error(self, mock_service_class: MagicMock) -> None:
        """Test 500 response when insufficient fuel stations available."""
        mock_service = MagicMock()
        mock_service.optimize_route.side_effect = InsufficientStationsError(
            "No viable stations"
        )
        mock_service_class.return_value = mock_service

        data = {
            "start_lat": 34.05,
            "start_lon": -118.25,
            "end_lat": 40.71,
            "end_lon": -74.01,
        }
        response = self.client.post(self.url, data, format="json")

        res: DRFResponse = cast(DRFResponse, response)
        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", res.data)
        self.assertIn("Insufficient fuel stations", res.data["error"])

    def test_missing_required_fields(self) -> None:
        """Test validation error when required fields are missing."""
        data = {
            "start_lat": 34.05,
            # Missing start_lon, end_lat, end_lon
        }
        response = self.client.post(self.url, data, format="json")

        res: DRFResponse = cast(DRFResponse, response)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_lon", res.data)
        self.assertIn("end_lat", res.data)
        self.assertIn("end_lon", res.data)

    @patch("fuel_stations.views.RouteOptimizationService")
    def test_response_structure(self, mock_service_class: MagicMock) -> None:
        """Test that response has correct structure with all required fields."""
        mock_service = MagicMock()
        mock_service.optimize_route.return_value = {
            "route": {
                "distance_miles": 100.0,
                "duration_hours": 2.0,
                "geometry": [{"lat": 34.05, "lon": -118.25}],
            },
            "fuel_stops": [],
            "total_cost": 35.0,
            "total_distance_miles": 100.0,
        }
        mock_service_class.return_value = mock_service

        data = {
            "start_lat": 34.05,
            "start_lon": -118.25,
            "end_lat": 34.15,
            "end_lon": -118.15,
        }
        response = self.client.post(self.url, data, format="json")

        res: DRFResponse = cast(DRFResponse, response)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify route structure
        self.assertIn("route", res.data)
        route = res.data["route"]
        self.assertIn("distance_miles", route)
        self.assertIn("duration_hours", route)
        self.assertIn("geometry", route)

        # Verify top-level fields
        self.assertIn("fuel_stops", res.data)
        self.assertIn("total_cost", res.data)
        self.assertIn("total_distance_miles", res.data)
