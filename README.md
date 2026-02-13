# Fuel Route Optimizer

[![CI](https://github.com/Daniel-Q-Reis/fuel-route-optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/Daniel-Q-Reis/fuel-route-optimizer/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Django 5.2](https://img.shields.io/badge/django-5.2-green.svg)](https://docs.djangoproject.com/en/5.2/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)]()
[![Type Checked](https://img.shields.io/badge/mypy-strict-blue.svg)](https://mypy.readthedocs.io/)

A Django-based REST API that optimizes fuel stops for long-distance routes in the USA. The system minimizes fuel costs by selecting optimal refueling points while ensuring the vehicle's range is never exceeded.

## ✨ Key Features

- 🛣️ **Route Optimization** - Greedy algorithm finds near-optimal fuel stops
- 💰 **Cost Minimization** - Selects cheapest viable stations using real-time pricing
- 📍 **Spatial Queries** - Efficient bounding box + Haversine distance calculations
- 🗺️ **OpenRouteService Integration** - Real route geometry and distances
- ⚙️ **Configurable Safety Margins** - Production-ready safety buffer settings
- 📊 **95% Test Coverage** - Comprehensive unit, integration, and E2E tests
- 🔒 **Type-Safe** - Full mypy strict compliance

> [!IMPORTANT]
> **Critical Safety Findings & Implementation (ADR-003)**
> During requirements analysis, we identified **two safety-critical issues**:
> 1. **Driver Fatigue Risk**: 500-mile segments require 8.3 hours continuous driving, violating US DOT regulations.
> 2. **Range Accuracy Risk**: Line-of-sight estimates (Haversine) miss road geometry, risking fuel depletion in winding terrain.
>
> **Our Solution**:
> - **Geometry-Aware Optimizer**: Iterates through road coordinates for 100% distance accuracy.
> - **Safety Insights Engine**: Recommends rest stops between 220-260 miles (~4h), providing price comparisons between "Safe" and "Optimal Cost" stops.
>
> See [ADR-003](docs/adr/0003-driver-safety-vs-range-optimization.md) for the full engineering analysis.

---

## 🚀 Performance

**Benchmarks (Phase 6):**
- **Cached Latency:** **~24ms** (98.6% faster than baseline)
- **Cold Latency:** ~500ms (dominated by external API and the developer region that is over 5000 miles distance, impacting in around 300ms just by the distance — 150ms RTT).
- **Optimization Strategy:**
  - **Redis Caching:** 1-hour TTL for processed routes.
  - **Tuples Optimization:** Reduced memory footprint by converting dictionary geometry to tuples.
  - **Algorithm Skip:** Skips first 200 miles of geometry iteration (mathematically safe) for 40% CPU reduction.

---

## � Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenRouteService API Key ([get one free](https://openrouteservice.org/dev/#/signup))

### Setup

1. **Clone and start:**
   ```bash
   git clone https://github.com/Daniel-Q-Reis/fuel-route-optimizer.git
   cd fuel-route-optimizer
   make setup
   ```

2. **Configure API key:**
   Add your OpenRouteService API key to `.env`:
   ```bash
   OPENROUTESERVICE_API_KEY=your_key_here
   ```

3. **Load fuel station data:**
   ```bash
   make shell
   # In Django shell:
   python manage.py load_fuel_stations
   ```

4. **Access the API:**
   - **Swagger UI:** http://localhost:8000/api/docs/
   - **ReDoc:** http://localhost:8000/api/redoc/
   - **Health Check:** http://localhost:8000/health/

---

## � API Usage

### Optimize Route Endpoint

**POST** `/api/v1/optimize-route/`

**Request:**
```json
{
  "start_lat": 34.0522,
  "start_lon": -118.2437,
  "end_lat": 36.1699,
  "end_lon": -115.1398
}
```

**Response (200 OK):**
```json
{
  "route": {
    "distance_miles": 270.5,
    "duration_hours": 4.2,
    "geometry": [
      {"lat": 34.0522, "lon": -118.2437},
      {"lat": 34.8958, "lon": -117.0228},
      {"lat": 36.1699, "lon": -115.1398}
    ]
  },
  "fuel_stops": [
    {
      "name": "Barstow Travel Center",
      "address": "2500 E Main St",
      "city": "Barstow",
      "state": "CA",
      "lat": 34.8958,
      "lon": -117.0228,
      "price": "3.85",
      "distance_from_start": 135.2
    }
  ],
  "total_cost": 94.65,
  "total_distance_miles": 270.5
}
```

**Error Responses:**
- `400 Bad Request` - Invalid coordinates or same start/end
- `404 Not Found` - Route unreachable
- `500 Internal Server Error` - Insufficient fuel stations

### Try it with cURL

```bash
curl -X POST http://localhost:8000/api/v1/optimize-route/ \
  -H "Content-Type: application/json" \
  -d '{
    "start_lat": 34.0522,
    "start_lon": -118.2437,
    "end_lat": 36.1699,
    "end_lon": -115.1398
  }'
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENROUTESERVICE_API_KEY` | ORS API key for route data | - | ✅ |
| `MAX_VEHICLE_RANGE_MILES` | Maximum vehicle range | `500` | ❌ |
| `SAFETY_MARGIN_PERCENTAGE` | Safety buffer (0.0-1.0) | `0.0` | ❌ |
| `MPG` | Fuel economy (miles per gallon) | `10` | ❌ |

**Example `.env`:**
```bash
OPENROUTESERVICE_API_KEY=5b3ce3597851110001cf6248...
MAX_VEHICLE_RANGE_MILES=500
SAFETY_MARGIN_PERCENTAGE=0.06  # 6% safety margin (production)
MPG=10
```

---

## 🏗️ Architecture

### Algorithm: Greedy with Look-Ahead

The route optimizer uses a **Greedy algorithm** that selects the cheapest viable fuel station at each decision point:

1. **Get Route Geometry** - Fetch route from OpenRouteService Directions API
2. **Check Range** - If route ≤ effective range, return direct route (no stops)
3. **Find Fuel Stops** - Iterate through route geometry:
   - When remaining range < distance to next segment
   - Query stations within bounding box (spatial pre-filter)
   - Refine with Haversine distance calculation
   - Select cheapest station that can reach destination or next viable stop
4. **Calculate Cost** - `(total_distance / MPG) × average_fuel_price`

**Performance:**
- **Time Complexity:** O(n × m) where n = route points, m = candidate stations
- **Space Complexity:** O(n)
- **Optimization:** Bounding box reduces 8153 stations → ~50 candidates

### Tech Stack

| Component | Technology | Purpose |
|-----------|------------|------------|
| **Framework** | Django 5.2 | Web Framework |
| **API** | Django REST Framework + drf-spectacular | REST API & OpenAPI Docs |
| **Database** | PostgreSQL 15+ | Fuel station data, geospatial queries |
| **Cache** | Redis 7+ | Caching & Celery broker |
| **Tasks** | Celery 5.5 | Background ETL jobs |
| **Testing** | Pytest + Django TestCase | Unit, integration, E2E tests |
| **Type Safety** | MyPy (strict) | Static type checking |
| **Code Quality** | Ruff + Pre-commit | Linting, formatting |

---

## 🧪 Testing & Quality

### Run Tests

```bash
# All tests
make test

# Specific test file
docker-compose exec web python manage.py test fuel_stations.tests.test_api

# With coverage report
docker-compose exec web coverage run --source='.' manage.py test
docker-compose exec web coverage report
```

### Quality Checks

```bash
# All checks (tests + lint + types)
make quality

# Individual checks
docker-compose exec web mypy --strict .
docker-compose exec web ruff check .
docker-compose exec web ruff format --check .
```

### Test Metrics

- ✅ **124 tests passing** (50 unit + 8 API integration + 5 E2E + 61 others)
- ✅ **95.44% code coverage** (target: 75%)
- ✅ **MyPy strict mode** - 0 errors across 56 files
- ✅ **Pre-commit hooks** - ruff, formatting, YAML validation

---

## 🏎️ Benchmarking & Verification

### 1. Run Performance Benchmark
We provided a script to benchmark the geocoding and data ingestion process. This script loads a dataset of fuel prices and measures the throughput.

```bash
# Enter the container shell
make shell

# Run the benchmark script
python scripts/load_benchmark_data.py
```
*Tip: Watch the logs to see the "Sieve" optimization in action skipping irrelevant stations.*

### 2. Postman Collection
A complete Postman collection is included in the root directory: `fuel_route_optimizer.postman_collection.json`.

**How to use:**
1. Open Postman.
2. Click **Import** -> **File** -> Select `fuel_route_optimizer.postman_collection.json`.
3. You will see 4 pre-configured requests:
    - **Long Trip (NY -> LA):** Full demonstration of fuel stops & cost logic.
    - **Medium Trip (Dallas -> Chicago):** Classic multi-state route.
    - **Short Trip (Charlotte -> Atlanta):** Demonstrates **Sieve Optimization** (skips fuel search) + **Safety Insight**.

---

## 🗂️ Project Structure

```
src/
├── fuel_stations/          # Main app - route optimization
│   ├── clients/            # External API clients (ORS)
│   ├── services/           # Business logic (RouteOptimizationService)
│   ├── utils/              # Utilities (Haversine, bounding box)
│   ├── serializers.py      # DRF request/response serializers
│   ├── views.py            # API endpoints
│   ├── models.py           # FuelStation model
│   └── tests/              # Comprehensive test suite
├── apps/core/              # Core functionality (health checks)
└── fuel-route-optimizer/  # Project settings & configuration
```

---

## 📚 Development Commands

| Command | Description |
|---------|-------------|
| `make setup` | 🚀 Initial setup (build, migrate, superuser) |
| `make up` | ⬆️ Start all services |
| `make down` | ⬇️ Stop all services |
| `make test` | 🧪 Run test suite with coverage |
| `make quality` | ✅ Run all quality checks |
| `make shell` | 🐚 Open Django shell |
| `make logs` | 📋 Tail service logs |

---

## 🚀 Production Deployment

**Recommended Configuration:**
```bash
# .env.production
SAFETY_MARGIN_PERCENTAGE=0.06  # 6% buffer
DJANGO_SETTINGS_MODULE=fuel-route-optimizer.settings.production
DEBUG=False
ALLOWED_HOSTS=yourdomain.com

# Add authentication (JWT/Token)
# Add rate limiting/throttling
# Enable API key validation
```

**Deploy with Docker Compose:**
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 📖 Documentation

- **API Docs:** `/api/docs/` (Swagger UI), `/api/redoc/` (ReDoc)
- **Architecture Decisions:** [`docs/adr/`](docs/adr/)
  - [ADR-003: Driver Safety vs Range Optimization](docs/adr/0003-driver-safety-vs-range-optimization.md)
  - [ADR-004: Route Optimization Algorithm Selection](docs/adr/0004-route-optimization-algorithm-selection.md)
  - [ADR-005: Spatial Query Strategy](docs/adr/0005-spatial-query-strategy-without-postgis.md)
- **Execution Roadmap:** [`ROADMAP-EXEC.md`](ROADMAP-EXEC.md)

---

## ⚖️ License

Licensed under the **MIT License**.

---

## 👨‍💻 Author

**Daniel Q. Reis**
[GitHub](https://github.com/Daniel-Q-Reis) | [LinkedIn](#) | [Portfolio](#)
