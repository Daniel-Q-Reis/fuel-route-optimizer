"""Django management command to load fuel stations from CSV with geocoding."""

import csv
import time
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from tqdm import tqdm

from fuel_stations.clients.openrouteservice import GeocodingError, ORSClient
from fuel_stations.models import FuelStation


class Command(BaseCommand):
    """
    Load fuel stations from CSV and geocode addresses using OpenRouteService API.

    This command:
    1. Reads fuel-prices-for-be-assessment.csv
    2. Geocodes each address (skips existing stations for idempotency)
    3. Rate limits to 200 requests/minute (0.3s sleep between requests)
    4. Shows progress bar with tqdm
    5. Logs failures but continues processing

    Expected duration: ~50 minutes for 8153 stations

    Usage:
        python manage.py load_fuel_stations
    """

    help = "Load fuel stations from CSV and geocode addresses"

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the management command."""
        csv_path = Path("fuel-prices-for-be-assessment.csv")

        if not csv_path.exists():
            self.stdout.write(
                self.style.ERROR(f"CSV file not found: {csv_path.absolute()}")
            )
            return

        self.stdout.write(self.style.SUCCESS(f"Reading CSV file: {csv_path}"))

        # Read CSV file
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            stations = list(reader)

        total_stations = len(stations)
        self.stdout.write(self.style.SUCCESS(f"Found {total_stations} stations in CSV"))

        # Initialize OpenRouteService client
        client = ORSClient()

        # Counters for statistics
        created_count = 0
        skipped_count = 0
        failed_count = 0

        # Process each station with progress bar
        for row in tqdm(stations, desc="Geocoding stations", unit="station"):
            truckstop_name = row["Truckstop Name"]
            city = row["City"]
            state = row["State"]
            address = row["Address"]
            retail_price = row["Retail Price"]

            # Check if station already exists (idempotency)
            if FuelStation.objects.filter(
                truckstop_name=truckstop_name, city=city, state=state
            ).exists():
                skipped_count += 1
                continue

            # Construct full address for geocoding
            full_address = f"{address}, {city}, {state}"

            try:
                # Geocode address
                lat, lon = client.geocode(full_address)

                # Create fuel station record
                FuelStation.objects.create(
                    truckstop_name=truckstop_name,
                    address=address,
                    city=city,
                    state=state,
                    retail_price=float(retail_price),
                    latitude=lat,
                    longitude=lon,
                )
                created_count += 1

            except GeocodingError as e:
                self.stdout.write(
                    self.style.WARNING(f"Failed to geocode: {full_address} - {e}")
                )
                failed_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Unexpected error for {full_address}: {e}")
                )
                failed_count += 1

            # Rate limiting: 200 requests/minute = 0.3 seconds between requests
            time.sleep(0.3)

        # Display final statistics
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("FUEL STATION LOADING COMPLETE"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"Total stations in CSV:  {total_stations}")
        self.stdout.write(
            self.style.SUCCESS(f"Successfully created:   {created_count}")
        )
        self.stdout.write(
            self.style.WARNING(f"Skipped (already exist): {skipped_count}")
        )
        self.stdout.write(self.style.ERROR(f"Failed (geocoding):     {failed_count}"))
        self.stdout.write(f"Final database count:   {FuelStation.objects.count()}")
        self.stdout.write(self.style.SUCCESS("=" * 60))
