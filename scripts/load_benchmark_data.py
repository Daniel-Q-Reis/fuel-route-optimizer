import csv
import os
import sys
import time
from pathlib import Path

import django

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "src"))
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "fuel-route-optimizer.settings.development"
)
django.setup()

from fuel_stations.clients.openrouteservice import ORSClient  # noqa: E402
from fuel_stations.models import FuelStation  # noqa: E402


def load_benchmark_data() -> None:
    csv_path = Path("fuel-prices-for-be-assessment.csv")
    if not csv_path.exists():
        print(f"CSV not found at {csv_path.absolute()}")
        return

    # Load ALL states to ensure no geographic gaps (Global Strategy)
    # Strategy: Top 30 cheapest stations per state (Enhanced density)
    # ~50 states * 30 = ~1500 requests (well within 2000/day limit)
    stations_by_state: dict[str, list[dict[str, str]]] = {}

    print("Reading CSV...")
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            state = row["State"]
            if state not in stations_by_state:
                stations_by_state[state] = []
            stations_by_state[state].append(row)

    # Sort by price and take top 30 cheapest per state (Greedy Cost-Optimal Sampling)
    to_geocode = []
    for _, stations in stations_by_state.items():
        sorted_stations = sorted(stations, key=lambda x: float(x["Retail Price"]))[:30]
        to_geocode.extend(sorted_stations)

    print(
        f"Found {len(to_geocode)} target stations (Top 30 cheapest per state, Global)."
    )

    client = ORSClient()
    count = 0
    skipped = 0

    for row in to_geocode:
        truckstop_name = row["Truckstop Name"]
        city = row["City"]
        state = row["State"]
        address = row["Address"]
        retail_price = float(row["Retail Price"])

        # PREVENTIVE MECHANISM: Check local DB before calling API.
        # This ensuring skipped data DOES NOT consume API requests.
        if FuelStation.objects.filter(
            truckstop_name=truckstop_name, city=city, state=state
        ).exists():
            skipped += 1
            continue

        full_address = f"{address}, {city}, {state}"
        try:
            # print(f"Geocoding [{state}] {truckstop_name} ({city})...")
            lat, lon = client.geocode(full_address)
            FuelStation.objects.create(
                truckstop_name=truckstop_name,
                address=address,
                city=city,
                state=state,
                retail_price=retail_price,
                latitude=lat,
                longitude=lon,
            )
            count += 1
            print(f"[{count}/{len(to_geocode)}] Added: {truckstop_name}, {state}")
            time.sleep(2.0)  # Rate limit: 40 req/min = 1.5s/req. Safe margin: 2.0s
        except Exception as e:
            print(f"Failed to geocode {full_address}: {e}")

            # AUTOMATIC BREAK: Stop if API limit (403) or Rate limit (429) hit
            error_str = str(e).lower()
            if "403" in error_str or "forbidden" in error_str or "429" in error_str:
                print(
                    "\n🛑 STOPPING: API Quota exhausted or Rate Limit hit. Please check your ORS Key."
                )
                break

    print(f"\n✅ Load complete! Added {count} stations. Skipped {skipped} existing.")


if __name__ == "__main__":
    load_benchmark_data()
