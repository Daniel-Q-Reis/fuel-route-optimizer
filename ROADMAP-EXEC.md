# Fuel Route Optimizer - Execution Roadmap

## Overview

This roadmap provides a **step-by-step execution plan** divided into 6 phases. Each phase includes:
- ✅ **Clear objectives**
- 📋 **Specific tasks**
- 🤖 **Copy-paste prompts for AI coding assistants**

---

## 🎯 Phase 1: Docker Setup, Linting & Type Checking

### Objectives
- Configure development environment with Docker
- Set up code quality tools (Ruff, Black, Mypy)
- Ensure reproducible builds

### Tasks
1. ✅ Update `Dockerfile` to use Python 3.12
2. ✅ Configure `docker-compose.yml` (Django, PostgreSQL, Redis)
3. ✅ Set up Ruff + Black for linting/formatting
4. ✅ Configure Mypy in strict mode
5. ✅ Create comprehensive `.env.example`
6. ✅ Test Docker environment (health checks)

### 🤖 AI Prompt for Phase 1

```
# PHASE 1: Docker Setup & Development Environment

## Context
I'm building a Django 5.2 API using Python 3.12. I need a production-ready Docker setup.

## Requirements
1. Update Dockerfile to use `python:3.12-slim` base image
2. Configure docker-compose.yml with:
   - Django web service (port 8000)
   - PostgreSQL 16 (port 5432)
   - Health checks for all services
3. Set up Ruff + Black:
   - pyproject.toml with Ruff config (line-length=100, Django-safe rules)
   - Black config (line-length=100)
4. Configure Mypy in strict mode:
   - mypy.ini with strict=True
   - Ignore missing imports for third-party packages
   - Enable incremental mode
5. Create .env.example with:
   - DATABASE_URL
   - SECRET_KEY (placeholder)
   - DEBUG
   - ALLOWED_HOSTS
   - OPENROUTESERVICE_API_KEY (placeholder)
   - MAX_VEHICLE_RANGE_MILES=500
   - SAFETY_MARGIN_PERCENTAGE=0.0 (with comment explaining production recommendation)

## Files to Create/Modify
- Dockerfile
- docker-compose.yml
- pyproject.toml
- mypy.ini
- .env.example

## Verification
Run these commands to verify:
```bash
docker-compose build
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py check
```

All services should start without errors.
```

---

## 🎯 Phase 2: Models & Geocoding ETL

### Objectives
- Design `FuelStation` model with proper indexes
- Implement geocoding management command
- Load all 8153 stations with rate limiting

### Tasks
1. Create `FuelStation` model (see ADR 0006 for indexes)
2. Write management command `load_fuel_stations`
3. Implement OpenRouteService geocoding client
4. Add rate limiting (`time.sleep(0.3)` between requests)
5. Add progress tracking (`tqdm` library)
6. Handle geocoding errors gracefully
7. Write unit tests for data ingestion
8. Run migrations and test ETL process

### 🤖 AI Prompt for Phase 2

```
# PHASE 2: FuelStation Model & Geocoding ETL

## Context
I have a CSV file `fuel-prices-for-be-assessment.csv` with 8153 fuel stations (headers: OPIS Truckstop ID, Truckstop Name, Address, City, State, Rack ID, Retail Price). The CSV is MISSING lat/lon coordinates. I need to geocode all addresses using OpenRouteService API (free tier: 2000 req/day).

## Requirements

### 1. Create FuelStation Model
File: `src/fuel_stations/models.py`

```python
from django.db import models

class FuelStation(models.Model):
    truckstop_name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2, db_index=True)
    retail_price = models.DecimalField(max_digits=5, decimal_places=2, db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, db_index=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['latitude', 'longitude'], name='idx_location'),
            models.Index(fields=['retail_price'], name='idx_price'),
        ]
```

### 2. Create Geocoding Client
File: `src/fuel_stations/clients/openrouteservice.py`

Implement:
- `geocode(address: str) -> tuple[float, float]`  # Returns (lat, lon)
- Use requests library with HTTPAdapter + Retry strategy
- Retry on 429/500/502/503 errors (max 3 retries, exponential backoff)
- Raise custom exception if geocoding fails after retries

### 3. Create Management Command
File: `src/fuel_stations/management/commands/load_fuel_stations.py`

Implement:
```python
import csv
import time
from tqdm import tqdm
from django.core.management.base import BaseCommand
from fuel_stations.models import FuelStation
from fuel_stations.clients.openrouteservice import ORS_Client

class Command(BaseCommand):
    help = "Load fuel stations from CSV and geocode addresses"
    
    def handle(self, *args, **options):
        client = ORS_Client()
        with open('fuel-prices-for-be-assessment.csv', 'r') as f:
            reader = csv.DictReader(f)
            stations = list(reader)
        
        for row in tqdm(stations, desc="Geocoding stations"):
            # Check if already exists (idempotency)
            if FuelStation.objects.filter(
                truckstop_name=row['Truckstop Name'],
                city=row['City']
            ).exists():
                continue
            
            # Geocode address
            full_address = f"{row['Address']}, {row['City']}, {row['State']}"
            try:
                lat, lon = client.geocode(full_address)
                FuelStation.objects.create(
                    truckstop_name=row['Truckstop Name'],
                    address=row['Address'],
                    city=row['City'],
                    state=row['State'],
                    retail_price=float(row['Retail Price']),
                    latitude=lat,
                    longitude=lon
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to geocode: {full_address} - {e}"))
            
            # Rate limiting: 200 requests/minute
            time.sleep(0.3)
```

**CRITICAL**: Implement strict rate limiting (`time.sleep(0.3)`) to respect OpenRouteService free tier limits.

### 4. Create Tests
File: `src/fuel_stations/tests/test_commands.py`

Test:
- Command runs without errors (with mock geocoding)
- Idempotency (running twice doesn't duplicate)
- Error handling (skips failed geocodes)

## Environment Variable
Add to .env:
```
OPENROUTESERVICE_API_KEY=your_key_here
```

## Verification
```bash
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py load_fuel_stations
# Should complete in ~50 minutes with progress bar
```

Check database:
```bash
docker-compose exec web python manage.py shell
```
```python
>>> from fuel_stations.models import FuelStation
>>> FuelStation.objects.count()
8153  # (or close, accounting for geocoding failures)
```
```

---

## 🎯 Phase 3: Routing Logic & Optimization Service

### Objectives
- Implement Greedy fuel stop optimization algorithm
- Create OpenRouteService Directions API client
- Write comprehensive unit tests

### Tasks
1. Create `RouteOptimizationService` class
2. Implement Haversine distance formula
3. Implement bounding box calculation
4. Create OpenRouteService Directions client
5. Implement Greedy algorithm (see ADR 0004)
6. Add fuel cost calculation logic
7. Handle edge cases (no stations, unreachable)
8. Write unit tests (mock external API)

### 🤖 AI Prompt for Phase 3

```
# PHASE 3: Routing Logic & Optimization Service

## Context
I need to implement the core optimization logic: given a start/end location, find the optimal fuel stops to minimize cost while respecting a 500-mile max range.

## Algorithm (Greedy with Look-Ahead)
See ADR 0004 for full details. Summary:
1. Get route from OpenRouteService Directions API (1 call)
2. Divide route into 500-mile segments
3. For each segment, find cheapest station within range that allows reaching next segment
4. Calculate total cost (distance ÷ 10 MPG × fuel price)

## Requirements

### 0. Configuration (CRITICAL for Safety Margin)
File: `src/config/settings.py`

Add these settings (see ADR 0003 for rationale):
```python
import os

# Vehicle range configuration
MAX_VEHICLE_RANGE_MILES = 500  # Theoretical maximum

# Safety margin for fuel reserve (0.0 = no margin, 0.06 = 6% reserve)
# Default: 0.0 for assessment (minimize cost)
# Production: 0.06 recommended (30-mile buffer for real-world conditions)
SAFETY_MARGIN_PERCENTAGE = float(os.getenv('SAFETY_MARGIN_PERCENTAGE', '0.0'))

# Effective operating range (used by optimization algorithm)
EFFECTIVE_RANGE_MILES = MAX_VEHICLE_RANGE_MILES * (1 - SAFETY_MARGIN_PERCENTAGE)
# Examples:
#   margin=0.0  -> 500 miles (assessment mode, max cost savings)
#   margin=0.06 -> 470 miles (production mode, safety buffer)

# Fuel consumption rate
MPG = 10  # Miles per gallon
```

### 1. Haversine Distance Function
File: `src/fuel_stations/utils/geo.py`

```python
from math import radians, sin, cos, sqrt, atan2

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in miles between two points."""
    R = 3959  # Earth radius in miles
    # Implement formula (see ADR 0005)
    ...
    return distance_miles

def get_bounding_box(lat: float, lon: float, radius_miles: float) -> dict:
    """Calculate bounding box for spatial queries."""
    lat_delta = radius_miles / 69.0  # 1° lat ≈ 69 miles
    lon_delta = radius_miles / (69.0 * cos(radians(lat)))
    return {
        'lat_min': lat - lat_delta,
        'lat_max': lat + lat_delta,
        'lon_min': lon - lon_delta,
        'lon_max': lon + lon_delta
    }
```

### 2. OpenRouteService Directions Client
File: `src/fuel_stations/clients/openrouteservice.py`

Add method:
```python
def get_directions(self, start: str, end: str) -> dict:
    """
    Get route from ORS Directions API.
    
    Returns:
    {
        'distance_miles': 380.5,
        'duration_hours': 6.2,
        'geometry': [
            {'lat': 34.05, 'lon': -118.25},
            ...
        ]
    }
    """
    # Implement using ORS Directions API
    # Convert start/end to coordinates (geocode if needed)
    # Parse response and return normalized data
```

### 3. Route Optimization Service
File: `src/fuel_stations/services/route_optimizer.py`

```python
from typing import List, Dict
from fuel_stations.models import FuelStation
from fuel_stations.clients.openrouteservice import ORS_Client
from fuel_stations.utils.geo import haversine, get_bounding_box

MAX_RANGE_MILES = 500
from django.conf import settings # Added this import

# MAX_RANGE_MILES = 500 # This line will be removed
MPG = 10

class RouteOptimizationService:
    def __init__(self):
        self.ors_client = ORS_Client()
        # Use EFFECTIVE range (accounts for safety margin)
        self.max_range = settings.EFFECTIVE_RANGE_MILES
    
    def optimize_route(self, start: str, end: str) -> Dict:
        """
        Find optimal fuel stops for a route.
        
        Returns:
        {
            'route': {...},
            'fuel_stops': [
                {'name': 'TA Travel Center', 'lat': 34.0, 'lon': -118.0, 'price': 3.45},
                ...
            ],
            'total_cost': 123.45,
            'total_distance_miles': 380.5
        }
        """
        # 1. Get route from ORS
        route = self.ors_client.get_directions(start, end)
        
        # 2. Initialize
        current_position = route['geometry'][0]  # start
        remaining_range = self.max_range  # EFFECTIVE range (e.g., 470 if margin=0.06)
        fuel_stops = []
        
        # 3. Iterate along route
        for i, point in enumerate(route['geometry']):
            # Calculate distance to next point
            segment_distance = haversine(...) if i > 0 else 0
            
            # Check if we need fuel
            if remaining_range < segment_distance:
                # Find nearby stations
                station = self._find_best_station(
                    current_position, 
                    remaining_range, 
                    next_segment_distance
                )
                fuel_stops.append(station)
                remaining_range = self.max_range  # Refuel to EFFECTIVE range
                current_position = {'lat': station.latitude, 'lon': station.longitude}
            
            remaining_range -= segment_distance
        
        # 4. Calculate total cost
        total_cost = (route['distance_miles'] / MPG) * self._get_avg_fuel_price(fuel_stops)
        
        return {
            'route': route,
            'fuel_stops': fuel_stops,
            'total_cost': total_cost,
            'total_distance_miles': route['distance_miles']
        }
    
    def _find_best_station(self, position, max_distance, next_segment_distance):
        """Find cheapest station within range that allows reaching next segment."""
        bbox = get_bounding_box(position['lat'], position['lon'], max_distance)
        
        # Query with bounding box + price ordering
        candidates = FuelStation.objects.filter(
            latitude__gte=bbox['lat_min'],
            latitude__lte=bbox['lat_max'],
            longitude__gte=bbox['lon_min'],
            longitude__lte=bbox['lon_max']
        ).order_by('retail_price')[:50]  # Top 50 cheapest
        
        # Refine with Haversine
        for station in candidates:
            distance_to_station = haversine(
                position['lat'], position['lon'], 
                station.latitude, station.longitude
            )
            distance_after_refuel = self.max_range - distance_to_station  # Use EFFECTIVE range
            
            if distance_after_refuel >= next_segment_distance:
                return station
        
        raise InsufficientStationsError("No viable station found")
```

### 4. Unit Tests
File: `src/fuel_stations/tests/test_services.py`

Test cases:
- Simple route (LA → SF, should find 1-2 stops)
- Long route (LA → NYC, should find multiple stops)
- Edge case: route < 500 miles (no stops needed)
- Edge case: no stations in range (should raise error)
- Haversine accuracy (compare with known distances)

Use `pytest` with mocked ORS API responses.

## Verification
```bash
docker-compose exec web python manage.py shell
```
```python
from fuel_stations.services.route_optimizer import RouteOptimizationService
service = RouteOptimizationService()
result = service.optimize_route("Los Angeles, CA", "San Francisco, CA")
print(result['total_cost'])  # Should be reasonable ($50-100)
print(len(result['fuel_stops']))  # Should be 1-2
```
```

---

## 🎯 Phase 4: API Views, Serializers & Endpoint

### Objectives
- Create DRF serializers for input/output
- Implement API endpoint
- Add throttling and validation
- Write API integration tests

### Tasks
1. Create `RouteOptimizationSerializer` (input)
2. Create `RouteOptimizationResponseSerializer` (output)
3. Implement `POST /api/v1/optimize-route/` view
4. Add throttling (10 requests/min for anonymous users)
5. Add input validation (US addresses only)
6. Generate OpenAPI schema
7. Write API integration tests

### 🤖 AI Prompt for Phase 4

```
# PHASE 4: API Views, Serializers & Endpoint

## Context
I need to expose the RouteOptimizationService as a REST API endpoint using Django REST Framework.

## Requirements

### 1. Input Serializer
File: `src/fuel_stations/serializers.py`

```python
from rest_framework import serializers

class RouteOptimizationSerializer(serializers.Serializer):
    start = serializers.CharField(
        max_length=255,
        help_text="Start location (address or 'lat,lon')"
    )
    end = serializers.CharField(
        max_length=255,
        help_text="End location (address or 'lat,lon')"
    )
    
    def validate(self, data):
        """Ensure start != end."""
        if data['start'] == data['end']:
            raise serializers.ValidationError("Start and end must be different")
        return data
```

### 2. Output Serializer
```python
class FuelStopSerializer(serializers.Serializer):
    name = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    price = serializers.DecimalField(max_digits=5, decimal_places=2)

class RouteOptimizationResponseSerializer(serializers.Serializer):
    route = serializers.JSONField()  # GeoJSON from ORS
    fuel_stops = FuelStopSerializer(many=True)
    total_cost = serializers.DecimalField(max_digits=8, decimal_places=2)
    total_distance_miles = serializers.FloatField()
```

### 3. API View
File: `src/fuel_stations/views.py`

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework import status
from drf_spectacular.utils import extend_schema

from .serializers import RouteOptimizationSerializer, RouteOptimizationResponseSerializer
from .services.route_optimizer import RouteOptimizationService

class RouteOptimizationView(APIView):
    throttle_classes = [AnonRateThrottle]
    
    @extend_schema(
        request=RouteOptimizationSerializer,
        responses={200: RouteOptimizationResponseSerializer},
        description="Calculate optimal fuel stops for a route"
    )
    def post(self, request):
        serializer = RouteOptimizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            service = RouteOptimizationService()
            result = service.optimize_route(
                start=serializer.validated_data['start'],
                end=serializer.validated_data['end']
            )
            
            response_serializer = RouteOptimizationResponseSerializer(result)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        except InsufficientStationsError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
```

### 4. URL Configuration
File: `src/fuel_stations/urls.py`

```python
from django.urls import path
from .views import RouteOptimizationView

urlpatterns = [
    path('optimize-route/', RouteOptimizationView.as_view(), name='optimize-route'),
]
```

File: `src/config/urls.py`

```python
from django.urls import path, include

urlpatterns = [
    path('api/v1/', include('fuel_stations.urls')),
    # ... other paths
]
```

### 5. Throttling Configuration
File: `src/config/settings.py`

```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/minute',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

### 6. Integration Tests
File: `src/fuel_stations/tests/test_api.py`

```python
import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
class TestRouteOptimizationAPI:
    def test_optimize_route_success(self, mock_ors_client):
        client = APIClient()
        response = client.post('/api/v1/optimize-route/', {
            'start': 'Los Angeles, CA',
            'end': 'San Francisco, CA'
        })
        assert response.status_code == 200
        assert 'fuel_stops' in response.data
        assert response.data['total_cost'] > 0
    
    def test_same_start_end_error(self):
        client = APIClient()
        response = client.post('/api/v1/optimize-route/', {
            'start': 'Los Angeles, CA',
            'end': 'Los Angeles, CA'
        })
        assert response.status_code == 400
    
    def test_throttling(self):
        client = APIClient()
        # Make 11 requests (limit is 10/min)
        for i in range(11):
            response = client.post('/api/v1/optimize-route/', {...})
        assert response.status_code == 429  # Too Many Requests
```

## Verification
```bash
docker-compose exec web python manage.py spectacular --file schema.yml
# Should generate OpenAPI schema

# Test API (from host machine or another terminal)
curl -X POST http://localhost:8000/api/v1/optimize-route/ \
  -H "Content-Type: application/json" \
  -d '{"start": "Los Angeles, CA", "end": "San Francisco, CA"}'
```
```

---

## 🎯 Phase 5: End-to-End Testing & Coverage

### Objectives
- Write comprehensive E2E tests
- Achieve 94%+ test coverage
- Fix any failing tests
- Document test strategy

### Tasks
1. Write E2E test: Simple route (LA → SF)
2. Write E2E test: Long route (LA → NYC)
3. Write E2E test: Edge cases
4. Run pytest with coverage report
5. Fix coverage gaps
6. Document test strategy

### 🤖 AI Prompt for Phase 5

```
# PHASE 5: End-to-End Testing & Coverage

## Context
I need comprehensive test coverage (target: 94%+) to ensure the API works correctly.

## Requirements

### 1. E2E Test Suite
File: `src/fuel_stations/tests/test_e2e.py`

```python
import pytest
from rest_framework.test import APIClient
from fuel_stations.models import FuelStation

@pytest.mark.django_db
class TestEndToEnd:
    @pytest.fixture(autouse=True)
    def setup_data(self, db):
        """Create test fuel stations."""
        FuelStation.objects.bulk_create([
            FuelStation(
                truckstop_name="Station A",
                address="123 Main St",
                city="Los Angeles",
                state="CA",
                retail_price=3.50,
                latitude=34.0522,
                longitude=-118.2437
            ),
            # Add more test stations along LA → SF route
            ...
        ])
    
    def test_simple_route(self, mock_ors_directions):
        """Test LA → SF (should find 1-2 stops)."""
        client = APIClient()
        response = client.post('/api/v1/optimize-route/', {
            'start': 'Los Angeles, CA',
            'end': 'San Francisco, CA'
        })
        assert response.status_code == 200
        assert len(response.data['fuel_stops']) <= 2
        assert response.data['total_distance_miles'] > 300
    
    def test_long_route(self, mock_ors_directions):
        """Test LA → NYC (should find multiple stops)."""
        # Implement with mock data
        ...
    
    def test_no_stations_in_range(self):
        """Test route with no nearby stations (should error)."""
        # Clear test data
        FuelStation.objects.all().delete()
        client = APIClient()
        response = client.post('/api/v1/optimize-route/', {...})
        assert response.status_code == 400
        assert 'error' in response.data
```

### 2. Coverage Configuration
File: `pytest.ini`

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
python_files = tests.py test_*.py *_tests.py
addopts = 
    --cov=src/fuel_stations
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=94
```

### 3. Run Tests
```bash
docker-compose exec web pytest --cov --cov-report=html
# Open htmlcov/index.html to see coverage details

# Target: 94%+ coverage
```

### 4. Coverage Gaps to Fill
Common gaps:
- Error handling branches (try/except)
- Edge cases (empty results, invalid inputs)
- Management command error paths
- Client retry logic

Add tests for ALL uncovered lines.

## Verification
```bash
docker-compose exec web pytest --cov
# Should show coverage ≥ 94%
# All tests should pass
```
```

---

## 🎯 Phase 6: Documentation & Deliverables

### Objectives
- Update README.md (preserve Cookiecutter style)
- Create Postman collection
- Generate OpenAPI docs
- Record Loom video

### Tasks
1. Update README.md (add ETL step, link ADRs)
2. Create Postman collection for API testing
3. Generate Swagger/OpenAPI docs
4. Record Loom video (5 min max)
5. Final code review & cleanup
6. Submit to assessment

### 🤖 AI Prompt for Phase 6

```
# PHASE 6: Documentation & Deliverables

## Context
I need to finalize all documentation and prepare the Loom video for submission.

## Requirements

### 1. Update README.md
File: `README.md`

**IMPORTANT**: Preserve existing Cookiecutter style (badges, tech stack table, health check section).

**ADD** these sections:

#### Solution Strategy Section
```markdown
## 🧠 Solution Strategy

This API uses a **Greedy algorithm with look-ahead** to optimize fuel stops:
- Minimizes total fuel cost
- Ensures vehicle never runs out of fuel (500-mile max range)
- Response time: <200ms

For detailed architecture decisions, see:
- [ADR 0003: Driver Safety vs. Range](docs/adr/0003-driver-safety-vs-range-optimization.md)
- [ADR 0004: Route Optimization Algorithm](docs/adr/0004-route-optimization-algorithm.md)
- [Full Architecture Documentation](ARCHITECTURE.md)
```

#### Update Quick Start Section
```markdown
## 🚀 Quick Start

1. Clone the repository
```bash
git clone <repo-url>
cd fuel-route-optimizer
```

2. Copy environment file
```bash
cp .env.example .env
# Edit .env and add your OPENROUTESERVICE_API_KEY
```

3. Build and start containers
```bash
docker-compose up -d --build
```

4. Run migrations
```bash
docker-compose exec web python manage.py migrate
```

5. **CRITICAL**: Load fuel stations (one-time ETL, ~50 minutes)
```bash
docker-compose exec web python manage.py load_fuel_stations
```

6. Test the API
```bash
curl -X POST http://localhost:8000/api/v1/optimize-route/ \
  -H "Content-Type: application/json" \
  -d '{"start": "Los Angeles, CA", "end": "San Francisco, CA"}'
```

7. View API docs: http://localhost:8000/api/schema/swagger-ui/
```

### 2. Create Postman Collection
File: `fuel-route-optimizer.postman_collection.json`

Create collection with:
- POST /api/v1/optimize-route/ (with example requests)
- Environment variables (BASE_URL)
- Pre-request scripts (if needed)

Export as JSON.

### 3. Generate OpenAPI Docs
```bash
docker-compose exec web python manage.py spectacular --file schema.yml
```

Ensure Swagger UI is accessible at `/api/schema/swagger-ui/`

### 4. Loom Video Script (5 min max)

**Structure**:

**[0:00-0:30] Introduction**
- "Hi, I'm [Name]. This is my Fuel Route Optimizer API for the Backend Django Engineer assessment."

**[0:30-2:00] Postman Demo**
- Open Postman
- Show POST request to /api/v1/optimize-route/
- Example: LA → SF
- Explain response: route, fuel stops, total cost
- Show another example (longer route)

**[2:00-3:30] Code Walkthrough**
- Show project structure (models, services, views)
- Highlight FuelStation model with indexes
- Explain RouteOptimizationService (Greedy algorithm)
- Show ADR 0003 (Driver Safety concern) - **THIS SETS YOU APART**

**[3:30-4:30] Testing & Quality**
- Show pytest coverage report (94%+)
- Explain test strategy (unit, integration, E2E)
- Show Mypy strict mode output (no errors)

**[4:30-5:00] Wrap-Up**
- "All ADRs are documented in docs/adr/"
- "ETL process took 50 minutes, now API responds in <200ms"
- "Thank you for reviewing my work!"

**KEY POINTS TO EMPHASIZE**:
- ✅ Only 1 API call per request (meets requirement)
- ✅ Pre-geocoded all stations (smart ETL strategy)
- ✅ High test coverage (94%+)
- ✅ **Documented safety concern** (ADR 0003) - shows senior thinking

## Verification
- README.md updated (preserves style + adds ETL step)
- Postman collection works
- Loom video recorded (<5 min)
- All ADRs linked in README
```

---

## 📊 Success Criteria Checklist

Before submission, verify:

- [ ] ✅ All 6 phases completed
- [ ] ✅ Docker environment working (`docker-compose up`)
- [ ] ✅ All migrations applied
- [ ] ✅ Fuel stations loaded (8153 in database)
- [ ] ✅ API responds correctly (Postman tests pass)
- [ ] ✅ Test coverage ≥ 94%
- [ ] ✅ Mypy strict mode passes (no errors)
- [ ] ✅ All ADRs documented
- [ ] ✅ README.md updated with ETL step
- [ ] ✅ Loom video recorded (<5 min)
- [ ] ✅ Code committed to Git with clear messages

---

## 🎯 Time Allocation (3-Day Assessment)

| Phase | Estimated Time | Priority |
|-------|----------------|----------|
| Phase 1 | 2 hours | HIGH |
| Phase 2 | 4 hours (+ 50 min ETL) | HIGH |
| Phase 3 | 6 hours | CRITICAL |
| Phase 4 | 4 hours | CRITICAL |
| Phase 5 | 4 hours | HIGH |
| Phase 6 | 3 hours | MEDIUM |
| **Total** | **23 hours** | |

**Buffer**: 1 hour for debugging/refinement

---

## 🚨 Critical Reminders

1. **Rate Limiting**: ALWAYS implement `time.sleep(0.3)` in geocoding command
2. **ADR 0003**: Mention driver safety concern in Loom video (differentiator!)
3. **One API Call**: Ensure routing API called ONCE per request
4. **Test Coverage**: Don't submit with <94% coverage
5. **README ETL Step**: Users MUST run `load_fuel_stations` before using API

---

## 🎉 Final Checklist

Before hitting "Submit":
- [ ] Run full test suite: `docker-compose exec web pytest --cov`
- [ ] Check Docker build: `docker-compose up --build`
- [ ] Test API in Postman
- [ ] Review Loom video (clear audio, <5 min)
- [ ] Verify all ADRs committed
- [ ] Push to GitHub

**Good luck! You've got this! 🚀**
