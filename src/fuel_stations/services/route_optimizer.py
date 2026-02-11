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
        Includes Safety Insights for driver fatigue.
        """
        # Step 1: Get route from ORS
        route = self.ors_client.get_directions(start_lat, start_lon, end_lat, end_lon)
        total_distance = route["distance_miles"]
        geometry = route["geometry"]

        # Step 2: Check if we even need fuel stops
        if total_distance <= self.max_range:
            avg_price = self._get_average_fuel_price()
            return {
                "route": route,
                "fuel_stops": [],
                "safety_insights": self._generate_initial_safety_insights(
                    total_distance
                ),
                "total_cost": float((total_distance / self.mpg) * float(avg_price)),
                "total_distance_miles": total_distance,
            }

        # Step 3: Find fuel stops using Geometry-Aware Greedy algorithm
        fuel_stops, safety_insights = self._find_fuel_stops_with_geometry(
            start_lat, start_lon, end_lat, end_lon, geometry
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
            "safety_insights": safety_insights,
            "total_cost": total_cost,
            "total_distance_miles": total_distance,
        }

    def _find_fuel_stops_with_geometry(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        geometry: list[dict[str, float]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Find fuel stops by walking the actual geometry for precise distance.
        Also identifies Safety Insights for segments > 4 hours.
        """
        fuel_stops: list[dict[str, Any]] = []
        safety_insights: list[dict[str, Any]] = []

        current_lat, current_lon = start_lat, start_lon
        current_geo_idx = 0
        total_distance_traveled = 0.0

        while current_geo_idx < len(geometry) - 1:
            # How far can we still go?
            distance_to_end = self._calculate_geometry_distance(
                geometry, current_geo_idx
            )

            if distance_to_end <= self.max_range:
                break

            # Find the best station within range
            station = self._find_best_station(
                current_lat, current_lon, self.max_range, end_lat, end_lon
            )

            if not station:
                raise InsufficientStationsError(
                    f"No fuel stations found within {self.max_range} miles of "
                    f"({current_lat}, {current_lon})."
                )

            # Move to the station
            dist_to_station = haversine(
                current_lat,
                current_lon,
                float(station.latitude),
                float(station.longitude),
            )
            total_distance_traveled += dist_to_station

            # Identify Safety Insights before adding the stop
            insight = self._identify_safety_insight(
                current_lat, current_lon, station, dist_to_station
            )
            if insight:
                safety_insights.append(insight)

            fuel_stops.append(
                {
                    "name": station.truckstop_name,
                    "address": f"{station.address}, {station.city}, {station.state}",
                    "lat": float(station.latitude),
                    "lon": float(station.longitude),
                    "price": float(station.retail_price),
                    "distance_from_start": round(total_distance_traveled, 2),
                }
            )

            # Update state
            current_lat = float(station.latitude)
            current_lon = float(station.longitude)
            # Find the closest point in geometry to this station to resume walking
            current_geo_idx = self._find_closest_point_idx(
                geometry, current_lat, current_lon
            )

        return fuel_stops, safety_insights

    def _calculate_geometry_distance(
        self, geometry: list[dict[str, float]], start_idx: int
    ) -> float:
        """Sum exact road distance from a point in geometry to the end."""
        total = 0.0
        for i in range(start_idx, len(geometry) - 1):
            total += haversine(
                geometry[i]["lat"],
                geometry[i]["lon"],
                geometry[i + 1]["lat"],
                geometry[i + 1]["lon"],
            )
        return total

    def _find_closest_point_idx(
        self, geometry: list[dict[str, float]], lat: float, lon: float
    ) -> int:
        """Find the index of the geometry point closest to given coordinates."""
        min_dist = float("inf")
        closest_idx = 0
        for i, point in enumerate(geometry):
            dist = haversine(lat, lon, point["lat"], point["lon"])
            if dist < min_dist:
                min_dist = dist
                closest_idx = i
        return closest_idx

    def _identify_safety_insight(
        self,
        current_lat: float,
        current_lon: float,
        optimal_station: FuelStation,
        distance_to_optimal: float,
    ) -> dict[str, Any] | None:
        """
        Check if the segment violates the 4-hour safety rule (approx 240 miles).
        If so, recommend a 'Safety Stop' between 220-260 miles.
        """
        if distance_to_optimal < 220:
            return None

        # Find the cheapest station in the 220-260 mile safety window
        bbox = get_bounding_box(current_lat, current_lon, 260)
        safety_candidates = FuelStation.objects.filter(
            latitude__gte=bbox["lat_min"],
            latitude__lte=bbox["lat_max"],
            longitude__gte=bbox["lon_min"],
            longitude__lte=bbox["lon_max"],
        )

        best_safety_stop = None
        min_price = float("inf")

        for station in safety_candidates:
            dist = haversine(
                current_lat,
                current_lon,
                float(station.latitude),
                float(station.longitude),
            )
            if 220 <= dist <= 260:
                if float(station.retail_price) < min_price:
                    min_price = float(station.retail_price)
                    best_safety_stop = station

        if best_safety_stop is None:
            return None

        if best_safety_stop.pk == optimal_station.pk:
            return None

        # Calculate price delta
        optimal_price = float(optimal_station.retail_price)
        safety_price = float(best_safety_stop.retail_price)
        price_delta_pct = float(((safety_price - optimal_price) / optimal_price) * 100)

        # Estimate travel time to the optimal stop (the one we are comparing against)
        travel_time_h = float(distance_to_optimal / 60.0)

        # Narrow type for Mypy/Pyre
        stop_name = str(best_safety_stop.truckstop_name)
        stop_city = str(best_safety_stop.city)
        stop_state = str(best_safety_stop.state)
        stop_lat = float(best_safety_stop.latitude)
        stop_lon = float(best_safety_stop.longitude)
        stop_price = float(best_safety_stop.retail_price)

        return {
            "type": "DRIVER_FATIGUE_WARNING",
            "message": (
                f"Driver Fatigue Warning: Continuous driving will reach {travel_time_h:.1f}h. "
                f"We suggest a stop near {stop_city}, {stop_state} to respect safety guidelines. "
                f"The cheapest station in this 220-260mi window is {abs(price_delta_pct):.1f}% "
                f"{'more' if price_delta_pct > 0 else 'less'} expensive than the cost-optimal station "
                f"found at {float(distance_to_optimal):.1f} miles."
            ),
            "safety_stop": {
                "name": stop_name,
                "city": stop_city,
                "price": stop_price,
                "distance_miles": float(
                    f"{float(haversine(current_lat, current_lon, stop_lat, stop_lon)):.1f}"
                ),
            },
        }

    def _generate_initial_safety_insights(
        self, distance: float
    ) -> list[dict[str, Any]]:
        """Generate static warnings for routes that don't need fuel stops but are long."""
        if distance > 240:
            time_h = float(distance / 60.0)
            return [
                {
                    "type": "DRIVER_FATIGUE_WARNING",
                    "message": (
                        f"Warning: This segment is {float(distance):.1f} miles long (~{time_h:.1f}h). "
                        "Although no fuel stops are required, we recommend a rest break after 4 hours."
                    ),
                }
            ]
        return []

    def _find_best_station(
        self,
        lat: float,
        lon: float,
        max_distance: float,
        dest_lat: float,
        dest_lon: float,
    ) -> FuelStation | None:
        """
        Find cheapest fuel station within range.
        Greedy choice: pick the cheapest station that is within our reach.
        """
        bbox = get_bounding_box(lat, lon, max_distance)

        candidates = FuelStation.objects.filter(
            latitude__gte=bbox["lat_min"],
            latitude__lte=bbox["lat_max"],
            longitude__gte=bbox["lon_min"],
            longitude__lte=bbox["lon_max"],
        ).order_by("retail_price")[:100]

        current_dist_to_dest = haversine(lat, lon, dest_lat, dest_lon)

        for station in candidates:
            dist_to_station = haversine(
                lat, lon, float(station.latitude), float(station.longitude)
            )

            if dist_to_station <= max_distance:
                # Progress check: Is this station closer to destination than we are?
                # (Or at least not too far back if it's extremely cheap)
                dist_from_station_to_dest = haversine(
                    float(station.latitude),
                    float(station.longitude),
                    dest_lat,
                    dest_lon,
                )

                if dist_from_station_to_dest < current_dist_to_dest:
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
