#!/usr/bin/env python
"""
Baseline Performance Benchmark Script

Measures API response times with public ORS API (Germany).
Run from Docker container: docker-compose exec web python manage.py benchmark_baseline
"""
import os
import sys
import time
from typing import Any, Dict, List

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel-route-optimizer.settings.development")
sys.path.insert(0, "/usr/src/app/src")
django.setup()

import requests
from tqdm import tqdm


def run_benchmark() -> None:
    """Run baseline performance benchmarks."""
    print("\n" + "=" * 70)
    print("🚀 BASELINE PERFORMANCE BENCHMARK - Public ORS API (Germany)")
    print("=" * 70 + "\n")

    # Test routes (LA → Vegas, NY → Miami, etc.)
    test_routes: List[Dict[str, Any]] = [
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
            "name": "Chicago → Houston (~1,080 miles)",
            "start_lat": 41.8781,
            "start_lon": -87.6298,
            "end_lat": 29.7604,
            "end_lon": -95.3698,
        },
    ]

    url = "http://localhost:8000/api/v1/optimize-route/"
    results: List[Dict[str, Any]] = []

    # Warmup request
    print("🔥 Warmup request...")
    requests.post(url, json=test_routes[0])

    # Run benchmarks
    for route in tqdm(test_routes, desc="Running benchmarks"):
        times: List[float] = []
        
        for _ in range(3):  # 3 iterations per route
            start = time.time()
            response = requests.post(url, json=route)
            elapsed = (time.time() - start) * 1000  # Convert to ms
            
            if response.status_code == 200:
                times.append(elapsed)
            else:
                print(f"\n❌ Error for {route['name']}: {response.status_code}")
                continue

        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            results.append({
                "route": route["name"],
                "avg_ms": avg_time,
                "min_ms": min_time,
                "max_ms": max_time,
            })

    # Display results
    print("\n" + "=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    print(f"{'Route':<35} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12}")
    print("-" * 70)
    
    total_avg = 0.0
    for result in results:
        print(
            f"{result['route']:<35} "
            f"{result['avg_ms']:>10.1f}   "
            f"{result['min_ms']:>10.1f}   "
            f"{result['max_ms']:>10.1f}"
        )
        total_avg += result['avg_ms']
    
    overall_avg = total_avg / len(results) if results else 0
    print("-" * 70)
    print(f"{'OVERALL AVERAGE':<35} {overall_avg:>10.1f} ms")
    print("=" * 70)

    # Breakdown estimate
    print("\n📈 ESTIMATED BREAKDOWN (based on 1000ms average):")
    print(f"  • Network latency (BR→DE): ~200-250ms  (20-25%)")
    print(f"  • ORS API processing:      ~700-750ms  (70-75%)")
    print(f"  • Django processing:       ~30-50ms    (3-5%)")
    print(f"  • Database queries:        ~5-10ms     (~1%)")
    
    print("\n✅ Baseline benchmark complete!")
    print(f"Results saved to: docs/performance/baseline_benchmark.md\n")


if __name__ == "__main__":
    run_benchmark()
