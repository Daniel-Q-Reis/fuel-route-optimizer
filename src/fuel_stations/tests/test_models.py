"""Unit tests for FuelStation model."""

from decimal import Decimal

from django.test import TestCase

from fuel_stations.models import FuelStation


class FuelStationModelTest(TestCase):
    """Test cases for the FuelStation model."""

    def setUp(self) -> None:
        """Set up test data."""
        self.station_data = {
            "truckstop_name": "Test Truck Stop",
            "address": "123 Highway Rd",
            "city": "Springfield",
            "state": "IL",
            "retail_price": Decimal("3.459"),
            "latitude": Decimal("39.781721"),
            "longitude": Decimal("-89.650148"),
        }

    def test_create_fuel_station(self) -> None:
        """Test creating a fuel station."""
        station = FuelStation.objects.create(**self.station_data)

        self.assertEqual(station.truckstop_name, "Test Truck Stop")
        self.assertEqual(station.city, "Springfield")
        self.assertEqual(station.state, "IL")
        self.assertEqual(station.retail_price, Decimal("3.459"))
        self.assertIsNotNone(station.created_at)

    def test_fuel_station_str_representation(self) -> None:
        """Test string representation of fuel station."""
        station = FuelStation.objects.create(**self.station_data)
        expected_str = "Test Truck Stop - Springfield, IL"
        self.assertEqual(str(station), expected_str)

    def test_fuel_station_indexes_exist(self) -> None:
        """Test that database indexes are created."""
        # Get model meta
        indexes = [index.name for index in FuelStation._meta.indexes]

        # Check for composite location index
        self.assertIn("idx_location", indexes)

        # Check for price index
        self.assertIn("idx_price", indexes)

    def test_state_field_is_indexed(self) -> None:
        """Test that state field has db_index=True."""
        state_field = FuelStation._meta.get_field("state")
        self.assertTrue(state_field.db_index)

    def test_retail_price_field_is_indexed(self) -> None:
        """Test that retail_price field has db_index=True."""
        price_field = FuelStation._meta.get_field("retail_price")
        self.assertTrue(price_field.db_index)

    def test_latitude_field_is_indexed(self) -> None:
        """Test that latitude field has db_index=True."""
        lat_field = FuelStation._meta.get_field("latitude")
        self.assertTrue(lat_field.db_index)

    def test_longitude_field_is_indexed(self) -> None:
        """Test that longitude field has db_index=True."""
        lon_field = FuelStation._meta.get_field("longitude")
        self.assertTrue(lon_field.db_index)

    def test_query_by_state(self) -> None:
        """Test filtering stations by state."""
        FuelStation.objects.create(**self.station_data)

        # Create another station in different state
        other_station_data = self.station_data.copy()
        other_station_data["state"] = "CA"
        other_station_data["city"] = "Los Angeles"
        FuelStation.objects.create(**other_station_data)

        # Query by state
        il_stations = FuelStation.objects.filter(state="IL")
        self.assertEqual(il_stations.count(), 1)
        self.assertEqual(il_stations.first().city, "Springfield")

    def test_query_by_price_range(self) -> None:
        """Test filtering stations by price range."""
        FuelStation.objects.create(**self.station_data)

        # Create cheaper station
        cheap_station_data = self.station_data.copy()
        cheap_station_data["retail_price"] = Decimal("2.99")
        cheap_station_data["truckstop_name"] = "Cheap Gas"
        FuelStation.objects.create(**cheap_station_data)

        # Query stations under $3.50
        cheap_stations = FuelStation.objects.filter(retail_price__lt=Decimal("3.50"))
        self.assertEqual(cheap_stations.count(), 2)

        # Query stations under $3.00
        very_cheap = FuelStation.objects.filter(retail_price__lt=Decimal("3.00"))
        self.assertEqual(very_cheap.count(), 1)
        self.assertEqual(very_cheap.first().truckstop_name, "Cheap Gas")
