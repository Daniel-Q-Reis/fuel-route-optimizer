"""Route optimization service using Greedy algorithm."""

from decimal import Decimal
from typing import Any

from django.conf import settings

from fuel_stations.clients.openrouteservice import ORSClient
from fuel_stations.models import FuelStation
from fuel_stations.utils.geo import get_bounding_box, haversine


class InsufficientStationsError(Exception):
    """Exception raised when no fuel stations are available within range."""

    pass


class RouteOptimizationService:
    """
    Service for optimizing fuel stops along a route using Greedy algorithm.

    Algorithm:
    1. Get route from OpenRouteService
    2. Divide route into segments based on vehicle range
    3. For each segment, find cheapest station within range
    4. Calculate total fuel cost

    Performance: O(n × m) where n=segments, m=nearby stations (~50)
    Expected: <50ms for cross-country routes
    """

    def __init__(self) -> None:
        """Initialize the optimization service."""
        self.ors_client = ORSClient()
        self.max_range = settings.EFFECTIVE_RANGE_MILES
        self.mpg = settings.MPG

    def optimize_route(
        self, start_lat: float, start_lon: float, end_lat: float, end_lon: float
    ) -> dict[str, Any]:
        """
        Find optimal fuel stops to minimize cost while respecting range constraint.

        Args:
            start_lat: Starting latitude
            start_lon: Starting longitude
            end_lat: Ending latitude
            end_lon: Ending longitude

        Returns:
            Dictionary with:
            {
                'route': {distance_miles, duration_hours, geometry},
                'fuel_stops': [{station_info, distance_from_start}, ...],
                'total_cost': float,
                'total_distance_miles': float
            }

        Raises:
            RouteNotFoundError: If route cannot be found
            InsufficientStationsError: If no stations available within range
        """
        # Step 1: Get route from ORS
        route = self.ors_client.get_directions(start_lat, start_lon, end_lat, end_lon)
        total_distance = route["distance_miles"]

        # Step 2: Check if we even need fuel stops
        if total_distance <= self.max_range:
            # No stops needed, calculate cost with arbitrary avg price
            avg_price = self._get_average_fuel_price()
            return {
                "route": route,
                "fuel_stops": [],
                "total_cost": float((total_distance / self.mpg) * float(avg_price)),
                "total_distance_miles": total_distance,
            }

        # Step 3: Find fuel stops using Greedy algorithm
        fuel_stops = self._find_fuel_stops(
            start_lat, start_lon, end_lat, end_lon, route
        )

        # Step 4: Calculate total cost
        if fuel_stops:
            avg_price = sum(stop["price"] for stop in fuel_stops) / len(fuel_stops)
        else:
            avg_price = self._get_average_fuel_price()

        total_cost = (total_distance / self.mpg) * float(avg_price)

        return {
            "route": route,
            "fuel_stops": fuel_stops,
            "total_cost": total_cost,
            "total_distance_miles": total_distance,
        }

    def _find_fuel_stops(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        route: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Find fuel stops along route using Greedy algorithm.

        Returns list of fuel stop dictionaries with station info.
        """
        fuel_stops = []
        current_lat, current_lon = start_lat, start_lon
        remaining_range = self.max_range
        distance_traveled = 0.0

        # Simplified: check at regular intervals along route
        # In a more sophisticated implementation, we'd follow the exact geometry
        while True:
            # Calculate distance to destination
            distance_to_end = haversine(current_lat, current_lon, end_lat, end_lon)

            # Can we reach destination?
            if distance_to_end <= remaining_range:
                # Success! We can reach the end
                break

            # We need a fuel stop
            # Find the best station within current range
            station = self._find_best_station(
                current_lat, current_lon, remaining_range, end_lat, end_lon
            )

            if not station:
                raise InsufficientStationsError(
                    f"No fuel stations found within {self.max_range} miles of "
                    f"({current_lat}, {current_lon}). Route may be impossible."
                )

            # Calculate how far we've traveled to get to this station
            distance_to_station = haversine(
                current_lat,
                current_lon,
                float(station.latitude),
                float(station.longitude),
            )

            distance_traveled += distance_to_station

            # Add station to stops
            fuel_stops.append(
                {
                    "name": station.truckstop_name,
                    "address": f"{station.address}, {station.city}, {station.state}",
                    "lat": float(station.latitude),
                    "lon": float(station.longitude),
                    "price": float(station.retail_price),
                    "distance_from_start": distance_traveled,
                }
            )

            # Update position and range
            current_lat, current_lon = float(station.latitude), float(station.longitude)
            remaining_range = self.max_range  # Full tank

        return fuel_stops

    def _find_best_station(
        self,
        lat: float,
        lon: float,
        max_distance: float,
        dest_lat: float,
        dest_lon: float,
    ) -> FuelStation | None:
        """
        Find cheapest fuel station within range that allows reaching destination.

        Uses bounding box pre-filter + Haversine refinement for performance.

        Args:
            lat: Current latitude
            lon: Current longitude
            max_distance: Maximum search radius (remaining range)
            dest_lat: Destination latitude
            dest_lon: Destination longitude

        Returns:
            Best FuelStation or None if no stations found
        """
        # Step 1: Bounding box pre-filter (fast, uses indexes)
        bbox = get_bounding_box(lat, lon, max_distance)

        candidates = FuelStation.objects.filter(
            latitude__gte=bbox["lat_min"],
            latitude__lte=bbox["lat_max"],
            longitude__gte=bbox["lon_min"],
            longitude__lte=bbox["lon_max"],
        ).order_by("retail_price")[:100]  # Top 100 cheapest

        # Step 2: Haversine refinement + Greedy selection
        for station in candidates:
            distance_to_station = haversine(
                lat, lon, float(station.latitude), float(station.longitude)
            )

            # Is station within range?
            if distance_to_station > max_distance:
                continue

            # Can we reach destination from this station?
            distance_from_station_to_dest = haversine(
                float(station.latitude),
                float(station.longitude),
                dest_lat,
                dest_lon,
            )

            # Greedy: pick first (cheapest) viable station
            if distance_from_station_to_dest <= self.max_range:
                return station

        return None

    def _get_average_fuel_price(self) -> Decimal:
        """
        Get average fuel price from database.

        Returns:
            Average price or default value if no stations exist
        """
        from django.db.models import Avg

        avg_price = FuelStation.objects.aggregate(Avg("retail_price"))[
            "retail_price__avg"
        ]
        return avg_price if avg_price else Decimal("3.50")  # Default fallback
