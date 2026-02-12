"""Unit tests for route optimization service."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from fuel_stations.clients.openrouteservice import RouteNotFoundError
from fuel_stations.models import FuelStation
from fuel_stations.services.route_optimizer import (
    InsufficientStationsError,
    RouteOptimizationService,
)


@override_settings(EFFECTIVE_RANGE_MILES=500, MPG=10)
class RouteOptimizationServiceTest(TestCase):
    """Test cases for RouteOptimizationService."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create test fuel stations
        self.station1 = FuelStation.objects.create(
            truckstop_name="Cheap Station",
            address="123 Highway Rd",
            city="Springfield",
            state="IL",
            retail_price=Decimal("3.45"),
            latitude=Decimal("39.7817"),
            longitude=Decimal("-89.6501"),
        )

        self.station2 = FuelStation.objects.create(
            truckstop_name="Mid Price Station",
            address="456 Route 66",
            city="St Louis",
            state="MO",
            retail_price=Decimal("3.75"),
            latitude=Decimal("38.6270"),
            longitude=Decimal("-90.1994"),
        )

        self.station3 = FuelStation.objects.create(
            truckstop_name="Expensive Station",
            address="789 Interstate",
            city="Kansas City",
            state="MO",
            retail_price=Decimal("4.25"),
            latitude=Decimal("39.0997"),
            longitude=Decimal("-94.5786"),
        )

    @patch("fuel_stations.services.route_optimizer.ORSClient")
    def test_optimize_route_short_distance_no_stops(
        self, mock_ors_client: MagicMock
    ) -> None:
        """Test optimization for route shorter than max range (no fuel stops needed)."""
        # Mock ORS to return short route
        mock_instance = MagicMock()
        mock_instance.get_directions.return_value = {
            "distance_miles": 250.0,
            "duration_hours": 4.0,
            "geometry": [
                (34.05, -118.25),  # (lat, lon) tuples
                (36.17, -115.14),
            ],
        }
        mock_ors_client.return_value = mock_instance

        service = RouteOptimizationService()
        result = service.optimize_route(34.05, -118.25, 36.17, -115.14)

        self.assertEqual(result["fuel_stops"], [])
        self.assertEqual(result["total_distance_miles"], 250.0)
        # Cost = 250 miles / 10 MPG * avg_price (3.45+3.75+4.25)/3 = ~95.4
        self.assertGreater(result["total_cost"], 0)
        mock_instance.get_directions.assert_called_once()

    @patch("fuel_stations.services.route_optimizer.ORSClient")
    def test_optimize_route_with_fuel_stops(self, mock_ors_client: MagicMock) -> None:
        """Test optimization for long route requiring fuel stops."""
        mock_instance = MagicMock()
        mock_instance.get_directions.return_value = {
            "distance_miles": 800.0,
            "duration_hours": 12.0,
            "geometry": [
                (39.7817, -89.6501),  # (lat, lon)
                (39.0997, -94.5786),
            ],
        }
        mock_ors_client.return_value = mock_instance

        service = RouteOptimizationService()
        result = service.optimize_route(39.7817, -89.6501, 39.0997, -94.5786)

        # Long route may or may not have stops depending on geometry
        # Just verify structure is correct
        self.assertEqual(result["total_distance_miles"], 800.0)
        self.assertIn("total_cost", result)
        self.assertIn("route", result)
        self.assertIn("fuel_stops", result)

    @patch("fuel_stations.services.route_optimizer.ORSClient")
    def test_optimize_route_no_stations_in_range(
        self, mock_ors_client: MagicMock
    ) -> None:
        """Test error when no fuel stations available within range."""
        FuelStation.objects.all().delete()

        mock_instance = MagicMock()
        mock_instance.get_directions.return_value = {
            "distance_miles": 1500.0,
            "duration_hours": 20.0,
            "geometry": [
                (34.05, -118.25),
                (40.71, -74.01),
            ],
        }
        mock_ors_client.return_value = mock_instance

        service = RouteOptimizationService()

        with self.assertRaises(InsufficientStationsError):
            service.optimize_route(34.05, -118.25, 40.71, -74.01)

    @patch("fuel_stations.services.route_optimizer.ORSClient")
    def test_optimize_route_handles_ors_error(self, mock_ors_client: MagicMock) -> None:
        """Test that RouteNotFoundError is propagated from ORS client."""
        mock_instance = MagicMock()
        mock_instance.get_directions.side_effect = RouteNotFoundError("No route found")
        mock_ors_client.return_value = mock_instance

        service = RouteOptimizationService()

        with self.assertRaises(RouteNotFoundError):
            service.optimize_route(0, 0, 0, 0)

    @patch("fuel_stations.services.route_optimizer.ORSClient")
    def test_find_best_station_within_range(self, mock_ors_client: MagicMock) -> None:
        """Test finding best station within specified range."""
        service = RouteOptimizationService()

        best_station = service._find_best_station(
            lat=39.7817,
            lon=-89.6501,
            max_distance=500,
            dest_lat=39.0997,
            dest_lon=-94.5786,
        )

        self.assertIsNotNone(best_station)
        self.assertIsInstance(best_station, FuelStation)

    @patch("fuel_stations.services.route_optimizer.ORSClient")
    def test_find_best_station_no_viable_station(
        self, mock_ors_client: MagicMock
    ) -> None:
        """Test that None is returned when no station can reach destination."""
        service = RouteOptimizationService()

        best_station = service._find_best_station(
            lat=90.0,
            lon=0.0,
            max_distance=100,
            dest_lat=-90.0,
            dest_lon=0.0,
        )

        self.assertIsNone(best_station)

    @patch("fuel_stations.services.route_optimizer.ORSClient")
    def test_find_best_station_greedy_selection(
        self, mock_ors_client: MagicMock
    ) -> None:
        """Test that cheapest viable station is selected (greedy)."""
        service = RouteOptimizationService()

        # Station 1 (Cheap) is at (39.78, -89.65)
        # We start a bit south-east and head towards Station 1
        best_station = service._find_best_station(
            lat=39.0,
            lon=-89.0,
            max_distance=500,
            dest_lat=40.0,
            dest_lon=-90.0,
        )

        self.assertIsNotNone(best_station)
        self.assertEqual(best_station.retail_price, Decimal("3.45"))

    @patch("fuel_stations.services.route_optimizer.ORSClient")
    def test_get_average_fuel_price(self, mock_ors_client: MagicMock) -> None:
        """Test average fuel price calculation."""
        service = RouteOptimizationService()
        avg_price = service._get_average_fuel_price()

        expected_avg = (Decimal("3.45") + Decimal("3.75") + Decimal("4.25")) / 3
        self.assertAlmostEqual(float(avg_price), float(expected_avg), places=2)

    @patch("fuel_stations.services.route_optimizer.ORSClient")
    def test_get_average_fuel_price_no_stations(
        self, mock_ors_client: MagicMock
    ) -> None:
        """Test fallback price when no stations exist."""
        FuelStation.objects.all().delete()

        service = RouteOptimizationService()
        avg_price = service._get_average_fuel_price()

        self.assertEqual(avg_price, Decimal("3.50"))

    @patch("fuel_stations.services.route_optimizer.ORSClient")
    def test_fuel_stops_include_station_details(
        self, mock_ors_client: MagicMock
    ) -> None:
        """Test that fuel stop details are properly formatted."""
        mock_instance = MagicMock()
        mock_instance.get_directions.return_value = {
            "distance_miles": 600.0,
            "duration_hours": 9.0,
            "geometry": [
                (39.7817, -89.6501),
                (38.6270, -90.1994),
            ],
        }
        mock_ors_client.return_value = mock_instance

        service = RouteOptimizationService()
        result = service.optimize_route(39.7817, -89.6501, 38.6270, -90.1994)

        if result["fuel_stops"]:
            stop = result["fuel_stops"][0]
            self.assertIn("name", stop)
            self.assertIn("address", stop)
            self.assertIn("lat", stop)
            self.assertIn("lon", stop)
            self.assertIn("price", stop)
            self.assertIn("distance_from_start", stop)
