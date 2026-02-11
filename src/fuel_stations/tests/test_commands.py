"""Unit tests for load_fuel_stations management command."""

import io
from decimal import Decimal
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase

from fuel_stations.clients.openrouteservice import GeocodingError
from fuel_stations.models import FuelStation


class LoadFuelStationsCommandTest(TestCase):
    """Test cases for the load_fuel_stations management command."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.csv_content = """OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price
1,TEST TRUCK STOP,"I-55, EXIT 100",Springfield,IL,280,3.45
2,ANOTHER STOP,"I-70, EXIT 200",Indianapolis,IN,375,3.29"""

    @patch("fuel_stations.management.commands.load_fuel_stations.Path.exists")
    @patch("fuel_stations.management.commands.load_fuel_stations.open")
    @patch("fuel_stations.management.commands.load_fuel_stations.ORSClient")
    @patch("fuel_stations.management.commands.load_fuel_stations.time.sleep")
    def test_command_loads_stations_successfully(
        self,
        mock_sleep: Mock,
        mock_ors_client: Mock,
        mock_open: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test command successfully loads stations from CSV."""
        # Mock CSV file
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value = io.StringIO(self.csv_content)

        # Mock geocoding responses
        mock_client_instance = Mock()
        mock_client_instance.geocode.side_effect = [
            (39.781721, -89.650148),  # Springfield, IL
            (39.768403, -86.158068),  # Indianapolis, IN
        ]
        mock_ors_client.return_value = mock_client_instance

        # Run command
        out = io.StringIO()
        call_command("load_fuel_stations", stdout=out)

        # Verify stations were created
        self.assertEqual(FuelStation.objects.count(), 2)

        # Verify first station
        station1 = FuelStation.objects.get(truckstop_name="TEST TRUCK STOP")
        self.assertEqual(station1.city, "Springfield")
        self.assertEqual(station1.state, "IL")
        self.assertEqual(station1.retail_price, Decimal("3.45"))
        self.assertAlmostEqual(float(station1.latitude), 39.781721, places=6)

        # Verify second station
        station2 = FuelStation.objects.get(truckstop_name="ANOTHER STOP")
        self.assertEqual(station2.city, "Indianapolis")
        self.assertEqual(station2.state, "IN")

        # Verify rate limiting was applied (0.3s sleep between requests)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(0.3)

    @patch("fuel_stations.management.commands.load_fuel_stations.Path.exists")
    @patch("fuel_stations.management.commands.load_fuel_stations.open")
    @patch("fuel_stations.management.commands.load_fuel_stations.ORSClient")
    @patch("fuel_stations.management.commands.load_fuel_stations.time.sleep")
    def test_command_idempotency(
        self,
        mock_sleep: Mock,
        mock_ors_client: Mock,
        mock_open: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test command skips existing stations (idempotency)."""
        # Create existing station
        FuelStation.objects.create(
            truckstop_name="TEST TRUCK STOP",
            address="I-55, EXIT 100",
            city="Springfield",
            state="IL",
            retail_price=Decimal("3.45"),
            latitude=Decimal("39.781721"),
            longitude=Decimal("-89.650148"),
        )

        # Mock CSV file
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value = io.StringIO(self.csv_content)

        # Mock geocoding for second station only
        mock_client_instance = Mock()
        mock_client_instance.geocode.return_value = (39.768403, -86.158068)
        mock_ors_client.return_value = mock_client_instance

        # Run command
        out = io.StringIO()
        call_command("load_fuel_stations", stdout=out)

        # Should still be 2 stations total (1 existing + 1 new)
        self.assertEqual(FuelStation.objects.count(), 2)

        # Geocoding should only be called once (for the new station)
        self.assertEqual(mock_client_instance.geocode.call_count, 1)

    @patch("fuel_stations.management.commands.load_fuel_stations.Path.exists")
    @patch("fuel_stations.management.commands.load_fuel_stations.open")
    @patch("fuel_stations.management.commands.load_fuel_stations.ORSClient")
    @patch("fuel_stations.management.commands.load_fuel_stations.time.sleep")
    def test_command_handles_geocoding_errors(
        self,
        mock_sleep: Mock,
        mock_ors_client: Mock,
        mock_open: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test command continues on geocoding errors."""
        # Mock CSV file
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value = io.StringIO(self.csv_content)

        # Mock geocoding: first fails, second succeeds
        mock_client_instance = Mock()
        mock_client_instance.geocode.side_effect = [
            GeocodingError("No results found"),  # Fail for first station
            (39.768403, -86.158068),  # Success for second station
        ]
        mock_ors_client.return_value = mock_client_instance

        # Run command
        out = io.StringIO()
        call_command("load_fuel_stations", stdout=out)

        # Should have created only 1 station (second one)
        self.assertEqual(FuelStation.objects.count(), 1)
        station = FuelStation.objects.first()
        self.assertEqual(station.truckstop_name, "ANOTHER STOP")

        # Error message should be in output
        output = out.getvalue()
        self.assertIn("Failed to geocode", output)

    @patch("fuel_stations.management.commands.load_fuel_stations.Path.exists")
    def test_command_handles_missing_csv(self, mock_exists: Mock) -> None:
        """Test command handles missing CSV file gracefully."""
        # Mock missing CSV
        mock_exists.return_value = False

        # Run command
        out = io.StringIO()
        call_command("load_fuel_stations", stdout=out)

        # Should output error message
        output = out.getvalue()
        self.assertIn("CSV file not found", output)

        # No stations should be created
        self.assertEqual(FuelStation.objects.count(), 0)
