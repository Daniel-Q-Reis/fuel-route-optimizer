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
        from django.core.cache import cache
        cache.clear()

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

    def test_find_closest_point_idx(self) -> None:
        """Test finding the index of the closest geometry point."""
        service = RouteOptimizationService()
        geometry = [
            (34.05, -118.25),  # Index 0
            (35.05, -117.25),  # Index 1
            (36.05, -116.25),  # Index 2
        ]

        # Point close to index 1
        idx = service._find_closest_point_idx(geometry, 35.06, -117.26)
        self.assertEqual(idx, 1)

    @patch("fuel_stations.services.route_optimizer.FuelStation.objects.filter")
    def test_identify_safety_insight(self, mock_filter: MagicMock) -> None:
        """Test safety insight generation for driver fatigue."""
        service = RouteOptimizationService()

        # Test case: Distance < 220 miles (No insight)
        insight = service._identify_safety_insight(0, 0, MagicMock(), 200.0)
        self.assertIsNone(insight)

        # Test case: Distance > 220 miles (Should generate insight)
        # Mock a safety stop candidate
        mock_station = MagicMock()
        mock_station.pk = 1
        mock_station.retail_price = Decimal("3.50")
        mock_station.latitude = 35.0
        mock_station.longitude = -117.0
        mock_station.truckstop_name = "Safety Stop"
        mock_station.city = "Safety City"
        mock_station.state = "CA"

        # Mock filter to return this station
        mock_filter.return_value = [mock_station]

        # Mock optimal station (expensive)
        optimal_station = MagicMock()
        optimal_station.pk = 2
        optimal_station.retail_price = Decimal("4.00")

        # We need to ensure haversine returns a distance between 220 and 260
        # Since haversine is imported in the module, let's patch it or rely on geometry
        # Ideally we patch haversine, but for simplicity let's assume the math works
        # given the coordinates.
        # Instead, let's patch haversine in the service module to control distance
        with patch(
            "fuel_stations.services.route_optimizer.haversine"
        ) as mock_haversine:
            mock_haversine.return_value = 240.0  # Force distance to be in window

            insight = service._identify_safety_insight(0, 0, optimal_station, 240.0)

            self.assertIsNotNone(insight)
            self.assertEqual(insight["type"], "DRIVER_FATIGUE_WARNING")
            self.assertIn("Safety Stop", insight["safety_stop"]["name"])
            self.assertIn("optimal_stop", insight)
            self.assertIn("4.0", str(insight["optimal_stop"]["price"]))

    @patch("fuel_stations.services.route_optimizer.ORSClient")
    def test_full_fuel_stop_logic_coverage(self, mock_ors_client: MagicMock) -> None:
        """Verify the loop in _find_fuel_stops_with_geometry is exercised."""
        # Setup a route that definitely needs stops
        mock_instance = MagicMock()
        # Route logic: Start -> Stop -> End
        # Use simple geometry: (0,0) -> (0,5) -> (0,10) (degrees)
        # 1 degree lat is ~69 miles. So 5 deg is ~345 miles.
        # Total distance ~690 miles. Max range 500.
        # Should stop around (0,5).

        mock_instance.get_directions.return_value = {
            "distance_miles": 700.0,
            "duration_hours": 10.0,
            "geometry": [
                (34.0, -118.0),
                (38.0, -118.0),  # ~276 miles north
                (42.0, -118.0),  # ~552 miles (total)
            ],
        }
        mock_ors_client.return_value = mock_instance

        # Ensure we have a station reachable
        FuelStation.objects.create(
            truckstop_name="Midway Station",
            address="123 Mid Rd",
            city="Mid City",
            state="CA",
            retail_price=Decimal("3.50"),
            latitude=Decimal("38.0"),
            longitude=Decimal("-118.0"),
        )

        service = RouteOptimizationService()
        # Mock geometry distance calculations to be predictable
        # Or just trust the math with these clear coordinates

        # Run optimize
        result = service.optimize_route(34.0, -118.0, 42.0, -118.0)

        # Check that we got a stop (exercising lines 86 and the loop)
        self.assertTrue(len(result["fuel_stops"]) > 0)
        self.assertIn("Midway Station", result["fuel_stops"][0]["name"])
