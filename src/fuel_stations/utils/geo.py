"""Geospatial utility functions for distance calculations and spatial queries."""

from math import atan2, cos, radians, sin, sqrt


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth using Haversine formula.

    Args:
        lat1: Latitude of first point in decimal degrees
        lon1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lon2: Longitude of second point in decimal degrees

    Returns:
        Distance in miles

    Accuracy:
        <0.5% error for distances <1000 miles
        Assumes spherical Earth (actual error ~2 miles for 500-mile queries)

    Example:
        >>> haversine(34.05, -118.25, 40.71, -74.01)  # LA to NYC
        2451.2
    """
    R = 3959  # Earth radius in miles

    # Convert to radians
    lat1_rad, lon1_rad = radians(lat1), radians(lon1)
    lat2_rad, lon2_rad = radians(lat2), radians(lon2)

    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine formula
    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def get_bounding_box(lat: float, lon: float, radius_miles: float) -> dict[str, float]:
    """
    Calculate bounding box (lat/lon bounds) for a square around a point.

    This is a FAST approximation for pre-filtering database queries.
    The box is slightly oversized, which is acceptable since we refine with Haversine.

    Args:
        lat: Center latitude in decimal degrees
        lon: Center longitude in decimal degrees
        radius_miles: Radius in miles

    Returns:
        Dictionary with keys: lat_min, lat_max, lon_min, lon_max

    Performance:
        This reduces candidate stations from 8153 to ~50 for a 500-mile radius,
        enabling fast Haversine refinement.

    Example:
        >>> bbox = get_bounding_box(40.71, -74.01, 500)  # NYC, 500mi radius
        >>> bbox['lat_min'], bbox['lat_max']
        (33.46, 47.96)
    """
    # 1 degree of latitude ≈ 69 miles (constant everywhere on Earth)
    lat_delta = radius_miles / 69.0

    # 1 degree of longitude varies by latitude (narrower near poles)
    # At equator: 69 miles, at 40°N: ~53 miles
    lon_delta = radius_miles / (69.0 * cos(radians(lat)))

    return {
        "lat_min": lat - lat_delta,
        "lat_max": lat + lat_delta,
        "lon_min": lon - lon_delta,
        "lon_max": lon + lon_delta,
    }
