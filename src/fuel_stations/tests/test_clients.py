"""Unit tests for OpenRouteService client."""

from unittest.mock import Mock, patch

from django.test import TestCase
from requests.exceptions import (  # type: ignore[import-untyped]
    RequestException,
    Timeout,
)

from fuel_stations.clients.openrouteservice import GeocodingError, ORSClient


class ORSClientTest(TestCase):
    """Test cases for the OpenRouteService client."""

    def setUp(self) -> None:
        """Set up test client."""
        with patch("fuel_stations.clients.openrouteservice.config") as mock_config:
            mock_config.return_value = "test-api-key"
            self.ors_client = ORSClient()

    @patch("fuel_stations.clients.openrouteservice.requests.Session.get")
    def test_successful_geocoding(self, mock_get: Mock) -> None:
        """Test successful geocoding of an address."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "features": [
                {"geometry": {"coordinates": [-89.650148, 39.781721]}}  # [lon, lat]
            ]
        }
        mock_get.return_value = mock_response

        lat, lon = self.ors_client.geocode("123 Highway Rd, Springfield, IL")

        self.assertAlmostEqual(lat, 39.781721, places=6)
        self.assertAlmostEqual(lon, -89.650148, places=6)
        mock_get.assert_called_once()

    @patch("fuel_stations.clients.openrouteservice.requests.Session.get")
    def test_geocoding_no_results(self, mock_get: Mock) -> None:
        """Test geocoding with no results found."""
        # Mock API response with empty features
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"features": []}
        mock_get.return_value = mock_response

        with self.assertRaises(GeocodingError) as context:
            self.ors_client.geocode("Invalid Address XYZ123")

        self.assertIn("No geocoding results found", str(context.exception))

    @patch("fuel_stations.clients.openrouteservice.requests.Session.get")
    def test_geocoding_timeout(self, mock_get: Mock) -> None:
        """Test geocoding with request timeout."""
        # Mock timeout exception
        mock_get.side_effect = Timeout("Request timed out")

        with self.assertRaises(GeocodingError) as context:
            self.ors_client.geocode("123 Test St")

        self.assertIn("Failed to geocode", str(context.exception))

    @patch("fuel_stations.clients.openrouteservice.requests.Session.get")
    def test_geocoding_request_exception(self, mock_get: Mock) -> None:
        """Test geocoding with request exception."""
        # Mock request exception
        mock_get.side_effect = RequestException("Connection error")

        with self.assertRaises(GeocodingError) as context:
            self.ors_client.geocode("123 Test St")

        self.assertIn("Failed to geocode", str(context.exception))

    @patch("fuel_stations.clients.openrouteservice.requests.Session.get")
    def test_geocoding_http_error(self, mock_get: Mock) -> None:
        """Test geocoding with HTTP error response."""
        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = RequestException("Server error")
        mock_get.return_value = mock_response

        with self.assertRaises(GeocodingError):
            self.ors_client.geocode("123 Test St")

    def test_session_has_retry_strategy(self) -> None:
        """Test that session is configured with retry strategy."""
        # Check that session has adapters mounted
        self.assertIn("https://", self.ors_client.session.adapters)
        self.assertIn("http://", self.ors_client.session.adapters)

        # Check retry configuration
        https_adapter = self.ors_client.session.adapters["https://"]
        self.assertIsNotNone(https_adapter.max_retries)
        self.assertEqual(https_adapter.max_retries.total, 3)
        self.assertEqual(
            https_adapter.max_retries.status_forcelist, [429, 500, 502, 503]
        )
        self.assertEqual(https_adapter.max_retries.backoff_factor, 0.5)


# Tests for get_directions method
class ORSClientDirectionsTest(TestCase):
    """Test cases for the get_directions method."""

    def setUp(self) -> None:
        """Set up test client."""
        with patch("fuel_stations.clients.openrouteservice.config") as mock_config:
            mock_config.return_value = "test-api-key"
            self.ors_client = ORSClient()

    @patch("fuel_stations.clients.openrouteservice.requests.Session.post")
    def test_successful_directions(self, mock_post: Mock) -> None:
        """Test successful route directions retrieval."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "features": [
                {
                    "properties": {
                        "summary": {
                            "distance": 402336.0,  # meters (250 miles)
                            "duration": 14400.0,  # seconds (4 hours)
                        }
                    },
                    "geometry": {
                        "coordinates": [
                            [-118.25, 34.05],  # [lon, lat] LA
                            [-115.14, 36.17],  # [lon, lat] Vegas
                        ]
                    },
                }
            ]
        }
        mock_post.return_value = mock_response

        result = self.ors_client.get_directions(34.05, -118.25, 36.17, -115.14)

        # Check conversions
        self.assertAlmostEqual(result["distance_miles"], 250.0, delta=1.0)
        self.assertAlmostEqual(result["duration_hours"], 4.0, places=1)
        self.assertEqual(len(result["geometry"]), 2)
        self.assertEqual(result["geometry"][0]["lat"], 34.05)
        self.assertEqual(result["geometry"][0]["lon"], -118.25)
        mock_post.assert_called_once()

    @patch("fuel_stations.clients.openrouteservice.requests.Session.post")
    def test_directions_no_route_found(self, mock_post: Mock) -> None:
        """Test get_directions with no route found."""
        # Mock API response with empty routes
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"features": []}
        mock_post.return_value = mock_response

        from fuel_stations.clients.openrouteservice import RouteNotFoundError

        with self.assertRaises(RouteNotFoundError) as context:
            self.ors_client.get_directions(0, 0, 0, 0)

        self.assertIn("No route found", str(context.exception))

    @patch("fuel_stations.clients.openrouteservice.requests.Session.post")
    def test_directions_timeout(self, mock_post: Mock) -> None:
        """Test get_directions with request timeout."""
        mock_post.side_effect = Timeout("Request timed out")

        from fuel_stations.clients.openrouteservice import RouteNotFoundError

        with self.assertRaises(RouteNotFoundError) as context:
            self.ors_client.get_directions(34.05, -118.25, 36.17, -115.14)

        self.assertIn("Failed to get route", str(context.exception))

    @patch("fuel_stations.clients.openrouteservice.requests.Session.post")
    def test_directions_http_error(self, mock_post: Mock) -> None:
        """Test get_directions with HTTP error response."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = RequestException("Forbidden")
        mock_post.return_value = mock_response

        from fuel_stations.clients.openrouteservice import RouteNotFoundError

        with self.assertRaises(RouteNotFoundError):
            self.ors_client.get_directions(34.05, -118.25, 36.17, -115.14)

    @patch("fuel_stations.clients.openrouteservice.requests.Session.post")
    def test_directions_coordinate_transformation(self, mock_post: Mock) -> None:
        """Test that coordinates are properly transformed from [lon,lat] to {lat,lon}."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "features": [
                {
                    "properties": {"summary": {"distance": 100000, "duration": 3600}},
                    "geometry": {
                        "coordinates": [
                            [-89.65, 39.78],  # Springfield, IL [lon, lat]
                            [-90.19, 38.62],  # St Louis, MO [lon, lat]
                        ]
                    },
                }
            ]
        }
        mock_post.return_value = mock_response

        result = self.ors_client.get_directions(39.78, -89.65, 38.62, -90.19)

        # Verify coordinate transformation
        self.assertEqual(result["geometry"][0]["lat"], 39.78)
        self.assertEqual(result["geometry"][0]["lon"], -89.65)
        self.assertEqual(result["geometry"][1]["lat"], 38.62)
        self.assertEqual(result["geometry"][1]["lon"], -90.19)
