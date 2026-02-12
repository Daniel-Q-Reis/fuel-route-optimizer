"""Performance benchmark with Redis caching."""

import time
from typing import Any

import requests  # type: ignore
from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Benchmark API with Redis caching enabled."""

    help = "Measure improvement with Redis caching"

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute cached benchmark."""
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("⚡ CACHED PERFORMANCE BENCHMARK"))
        self.stdout.write("=" * 70 + "\n")

        test_routes: list[dict[str, Any]] = [
            {
                "name": "LA → Vegas",
                "start_lat": 34.0522,
                "start_lon": -118.2437,
                "end_lat": 36.1699,
                "end_lon": -115.1398,
            },
        ]

        url = "http://localhost:8000/api/v1/optimize-route/"

        # Clear cache
        self.stdout.write("🧹 Clearing Redis cache...")
        cache.clear()

        # Test 1: Cache MISS (first request)
        self.stdout.write("\n📤 Test 1: Cache MISS (first request)")
        times_miss: list[float] = []
        for _ in range(3):
            cache.clear()  # Force miss
            start = time.time()
            response = requests.post(url, json=test_routes[0], timeout=30)
            elapsed = (time.time() - start) * 1000
            if response.status_code == 200:
                times_miss.append(elapsed)

        # Test 2: Cache HIT (repeated requests)
        self.stdout.write("\n💨 Test 2: Cache HIT (repeated requests)")
        times_hit: list[float] = []
        for _ in range(10):  # 10 iterations
            start = time.time()
            response = requests.post(url, json=test_routes[0], timeout=30)
            elapsed = (time.time() - start) * 1000
            if response.status_code == 200:
                times_hit.append(elapsed)

        # Results
        avg_miss = sum(times_miss) / len(times_miss) if times_miss else 0.0
        avg_hit = sum(times_hit) / len(times_hit) if times_hit else 0.0

        if avg_miss > 0:
            improvement = ((avg_miss - avg_hit) / avg_miss) * 100
        else:
            improvement = 0.0

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("📊 RESULTS"))
        self.stdout.write("=" * 70)
        self.stdout.write(f"Cache MISS (avg):     {avg_miss:>10.1f} ms")
        self.stdout.write(f"Cache HIT (avg):      {avg_hit:>10.1f} ms")
        self.stdout.write(f"Improvement:          {improvement:>10.1f}%")
        self.stdout.write("=" * 70)

        self.stdout.write(
            f"\n🎯 Cache reduced latency by {avg_miss - avg_hit:.1f}ms!\n"
        )
        self.stdout.write(self.style.SUCCESS("✅ Cached benchmark complete!\n"))
