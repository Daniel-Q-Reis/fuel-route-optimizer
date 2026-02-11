"""OpenRouteService API client for geocoding addresses."""

import requests  # type: ignore[import-untyped]
from decouple import config
from requests.adapters import HTTPAdapter  # type: ignore[import-untyped]
from urllib3.util.retry import Retry


class GeocodingError(Exception):
    """Exception raised when geocoding fails after all retries."""

    pass


class ORSClient:
    """
    Client for the OpenRouteService Geocoding API.

    Implements retry logic and rate limiting to respect API constraints.
    Free tier: 2000 requests/day, 40 requests/minute.
    """

    BASE_URL = "https://api.openrouteservice.org/geocode/search"

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
            allowed_methods=["GET"],
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
                self.BASE_URL,
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
