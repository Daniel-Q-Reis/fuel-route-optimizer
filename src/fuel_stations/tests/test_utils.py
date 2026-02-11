"""Unit tests for geospatial utility functions."""

from django.test import TestCase

from fuel_stations.utils.geo import get_bounding_box, haversine


class HaversineTest(TestCase):
    """Test cases for Haversine distance calculation."""

    def test_haversine_known_distance(self) -> None:
        """Test Haversine with known distance (LA to NYC)."""
        # Los Angeles to New York City
        lat1, lon1 = 34.0522, -118.2437  # LA
        lat2, lon2 = 40.7128, -74.0060  # NYC

        distance = haversine(lat1, lon1, lat2, lon2)

        # Actual distance is approximately 2451 miles
        self.assertAlmostEqual(distance, 2451, delta=10)

    def test_haversine_same_point(self) -> None:
        """Test Haversine with same start and end point."""
        lat, lon = 40.7128, -74.0060

        distance = haversine(lat, lon, lat, lon)

        self.assertAlmostEqual(distance, 0.0, places=2)

    def test_haversine_chicago_to_dallas(self) -> None:
        """Test Haversine with another known distance."""
        # Chicago to Dallas
        lat1, lon1 = 41.8781, -87.6298  # Chicago
        lat2, lon2 = 32.7767, -96.7970  # Dallas

        distance = haversine(lat1, lon1, lat2, lon2)

        # Actual distance is approximately 801 miles
        self.assertAlmostEqual(distance, 801, delta=10)

    def test_haversine_short_distance(self) -> None:
        """Test Haversine for short distance (high accuracy)."""
        # Two nearby points in San Francisco
        lat1, lon1 = 37.7749, -122.4194
        lat2, lon2 = 37.8044, -122.2712  # Oakland

        distance = haversine(lat1, lon1, lat2, lon2)

        # Approximately 8 miles
        self.assertAlmostEqual(distance, 8, delta=1)


class BoundingBoxTest(TestCase):
    """Test cases for bounding box calculation."""

    def test_bounding_box_basic(self) -> None:
        """Test bounding box calculation for NYC with 500-mile radius."""
        lat, lon = 40.7128, -74.0060  # NYC
        radius = 500

        bbox = get_bounding_box(lat, lon, radius)

        # Check structure
        self.assertIn("lat_min", bbox)
        self.assertIn("lat_max", bbox)
        self.assertIn("lon_min", bbox)
        self.assertIn("lon_max", bbox)

        # Check that center is within bounds
        self.assertLess(bbox["lat_min"], lat)
        self.assertGreater(bbox["lat_max"], lat)
        self.assertLess(bbox["lon_min"], lon)
        self.assertGreater(bbox["lon_max"], lon)

        # Check approximate delta (500 miles / 69 ≈ 7.25 degrees)
        lat_delta = bbox["lat_max"] - bbox["lat_min"]
        self.assertAlmostEqual(lat_delta, 14.5, delta=0.5)  # Both sides

    def test_bounding_box_includes_known_point(self) -> None:
        """Test that bbox includes a point at known distance."""
        center_lat, center_lon = 40.0, -100.0
        radius = 100

        bbox = get_bounding_box(center_lat, center_lon, radius)

        # Point approximately 70 miles north
        test_lat = center_lat + 1.0  # ~69 miles north
        test_lon = center_lon

        # Should be inside the bounding box
        self.assertGreater(test_lat, bbox["lat_min"])
        self.assertLess(test_lat, bbox["lat_max"])
        self.assertGreater(test_lon, bbox["lon_min"])
        self.assertLess(test_lon, bbox["lon_max"])

    def test_bounding_box_symmetry(self) -> None:
        """Test that bounding box is symmetric around center."""
        lat, lon = 30.0, -90.0
        radius = 200

        bbox = get_bounding_box(lat, lon, radius)

        # Check lat symmetry
        lat_delta_min = lat - bbox["lat_min"]
        lat_delta_max = bbox["lat_max"] - lat
        self.assertAlmostEqual(lat_delta_min, lat_delta_max, places=5)

        # Check lon symmetry
        lon_delta_min = lon - bbox["lon_min"]
        lon_delta_max = bbox["lon_max"] - lon
        self.assertAlmostEqual(lon_delta_min, lon_delta_max, places=5)

    def test_bounding_box_equator(self) -> None:
        """Test bounding box calculation near equator."""
        lat, lon = 0.0, 0.0  # Equator
        radius = 100

        bbox = get_bounding_box(lat, lon, radius)

        # At equator, lat and lon deltas should be similar
        lat_delta = (bbox["lat_max"] - bbox["lat_min"]) / 2
        lon_delta = (bbox["lon_max"] - bbox["lon_min"]) / 2

        # Should be approximately equal (within 10%)
        self.assertAlmostEqual(lat_delta, lon_delta, delta=lat_delta * 0.1)
