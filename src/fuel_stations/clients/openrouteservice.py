"""OpenRouteService API client for geocoding and routing."""

from typing import Any

import requests  # type: ignore[import-untyped]
from decouple import config
from requests.adapters import HTTPAdapter  # type: ignore[import-untyped]
from urllib3.util.retry import Retry


class GeocodingError(Exception):
    """Exception raised when geocoding fails after all retries."""

    pass


class RouteNotFoundError(Exception):
    """Exception raised when route cannot be found between two points."""

    pass


class ORSClient:
    """
    Client for the OpenRouteService APIs (Geocoding + Directions).

    Implements retry logic and rate limiting to respect API constraints.
    Free tier: 2000 requests/day, 40 requests/minute.
    """

    GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
    DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"

    def __init__(self) -> None:
        """Initialize the ORS client with API key and retry strategy."""
        self.api_key = config("OPENROUTESERVICE_API_KEY")
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry strategy.

        Retries on:
        - 429 (Too Many Requests)
        - 500 (Internal Server Error)
        - 502 (Bad Gateway)
        - 503 (Service Unavailable)

        Strategy: max 3 retries with exponential backoff (0.5s, 1s, 2s).
        """
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503],
            backoff_factor=0.5,  # 0.5s, 1s, 2s
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def geocode(self, address: str) -> tuple[float, float]:
        """
        Geocode an address to (latitude, longitude) coordinates.

        Args:
            address: Full address string to geocode

        Returns:
            Tuple of (latitude, longitude)

        Raises:
            GeocodingError: If geocoding fails after all retries

        Example:
            >>> client = ORSClient()
            >>> lat, lon = client.geocode("1600 Pennsylvania Ave, Washington, DC")
            >>> print(f"Coordinates: {lat}, {lon}")
        """
        params = {"api_key": self.api_key, "text": address, "size": 1}

        try:
            response = self.session.get(
                self.GEOCODE_URL,
                params=params,
                timeout=10,  # 10 second timeout
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise GeocodingError(f"Failed to geocode address '{address}': {e}") from e

        # Extract coordinates from response
        features = data.get("features", [])
        if not features:
            raise GeocodingError(f"No geocoding results found for address: {address}")

        coordinates = features[0]["geometry"]["coordinates"]
        # OpenRouteService returns [lon, lat], we need (lat, lon)
        lon, lat = coordinates
        return (float(lat), float(lon))

    def get_directions(
        self, start_lat: float, start_lon: float, end_lat: float, end_lon: float
    ) -> dict[str, Any]:
        """
        Get route information from OpenRouteService Directions API.

        Args:
            start_lat: Starting latitude
            start_lon: Starting longitude
            end_lat: Ending latitude
            end_lon: Ending longitude

        Returns:
            Dictionary with route information:
            {
                'distance_miles': float,
                'duration_hours': float,
                'geometry': [{'lat': float, 'lon': float}, ...]
            }

        Raises:
            RouteNotFoundError: If route cannot be found

        Example:
            >>> client = ORSClient()
            >>> route = client.get_directions(34.05, -118.25, 40.71, -74.01)
            >>> print(f"Distance: {route['distance_miles']} miles")
        """
        # ORS expects coordinates as [lon, lat]
        coordinates = [[start_lon, start_lat], [end_lon, end_lat]]

        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

        body = {"coordinates": coordinates}

        try:
            response = self.session.post(
                self.DIRECTIONS_URL, json=body, headers=headers, timeout=10
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise RouteNotFoundError(
                f"Failed to get route from ({start_lat}, {start_lon}) "
                f"to ({end_lat}, {end_lon}): {e}"
            ) from e

        # Parse response
        routes = data.get("routes", [])
        if not routes:
            raise RouteNotFoundError(
                f"No route found from ({start_lat}, {start_lon}) "
                f"to ({end_lat}, {end_lon})"
            )

        route = routes[0]
        summary = route["summary"]

        # Convert meters to miles (1 meter = 0.000621371 miles)
        distance_miles = summary["distance"] * 0.000621371

        # Convert seconds to hours
        duration_hours = summary["duration"] / 3600.0

        # Extract geometry (list of [lon, lat] points)
        geometry_raw = route["geometry"]["coordinates"]
        geometry = [{"lat": coord[1], "lon": coord[0]} for coord in geometry_raw]

        return {
            "distance_miles": distance_miles,
            "duration_hours": duration_hours,
            "geometry": geometry,
        }
