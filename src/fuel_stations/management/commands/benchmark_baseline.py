"""Baseline performance benchmark management command."""

import time
from typing import Any

import requests  # type: ignore
from django.core.management.base import BaseCommand
from tqdm import tqdm


class Command(BaseCommand):
    """Run baseline performance benchmarks against API."""

    help = "Measure API response times with public ORS (baseline)"

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute benchmark."""
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(
            self.style.SUCCESS("🚀 BASELINE PERFORMANCE BENCHMARK - Public ORS API")
        )
        self.stdout.write("=" * 70 + "\n")

        test_routes: list[dict[str, Any]] = [
            {
                "name": "LA → Las Vegas (~270 miles)",
                "start_lat": 34.0522,
                "start_lon": -118.2437,
                "end_lat": 36.1699,
                "end_lon": -115.1398,
            },
            {
                "name": "NY → Miami (~1,280 miles)",
                "start_lat": 40.7128,
                "start_lon": -74.0060,
                "end_lat": 25.7617,
                "end_lon": -80.1918,
            },
            {
                "name": "Chicago → Houston (~1,080)",
                "start_lat": 41.8781,
                "start_lon": -87.6298,
                "end_lat": 29.7604,
                "end_lon": -95.3698,
            },
        ]

        url = "http://localhost:8000/api/v1/optimize-route/"
        results: list[dict[str, Any]] = []

        # Warmup
        self.stdout.write("🔥 Warmup request...")
        requests.post(url, json=test_routes[0], timeout=30)

        # Benchmarks
        for route in tqdm(test_routes, desc="Running benchmarks"):
            times: list[float] = []

            for _ in range(3):  # 3 iterations
                start = time.time()
                response = requests.post(url, json=route, timeout=30)
                elapsed = (time.time() - start) * 1000  # ms

                if response.status_code == 200:
                    times.append(elapsed)
                else:
                    self.stdout.write(f"❌ Error: {response.status_code}")

            if times:
                results.append(
                    {
                        "route": route["name"],
                        "avg": sum(times) / len(times),
                        "min": min(times),
                        "max": max(times),
                    }
                )

        # Display
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("📊 RESULTS"))
        self.stdout.write("=" * 70)
        self.stdout.write(
            f"{'Route':<35} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12}"
        )
        self.stdout.write("-" * 70)

        total_avg = 0.0
        for r in results:
            self.stdout.write(
                f"{r['route']:<35} {r['avg']:>10.1f}   {r['min']:>10.1f}   {r['max']:>10.1f}"
            )
            total_avg += r["avg"]

        overall_avg = total_avg / len(results) if results else 0
        self.stdout.write("-" * 70)
        self.stdout.write(f"{'OVERALL AVERAGE':<35} {overall_avg:>10.1f} ms")
        self.stdout.write("=" * 70)

        self.stdout.write("\n📈 ESTIMATED BREAKDOWN:")
        self.stdout.write("  • Network (BR→DE):     ~200-250ms  (20-25%)")
        self.stdout.write("  • ORS processing:      ~700-750ms  (70-75%)")
        self.stdout.write("  • Django:              ~30-50ms    (3-5%)")
        self.stdout.write("  • Database:            ~5-10ms     (~1%)\n")

        self.stdout.write(self.style.SUCCESS("✅ Baseline complete!\n"))
