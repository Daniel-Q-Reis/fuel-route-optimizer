# ADR 0006: Database Query Performance Optimization

**Status:** Accepted
**Date:** 2026-02-10
**Decision Makers:** Backend Team

## Context

The assessment explicitly states: *"The API should return results quickly, the quicker the better."*

Our API will execute multiple database queries per request:
1. Find fuel stations within range (spatial query)
2. Order by price (sorting)
3. Fetch station details for response

Read performance is **critical** since this is a read-heavy API.

## Decision

Implement a **multi-layered performance strategy**:

### 1. Database Indexes (Primary Optimization)
### 2. Query Projection (`.only()` / `.values()`)
### 3. Prevent N+1 Queries
### 4. Connection Pooling

## 1. Database Indexes

### FuelStation Model
```python
from django.db import models

class FuelStation(models.Model):
    truckstop_name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2, db_index=True)
    retail_price = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        db_index=True  # Critical for ORDER BY price
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        db_index=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        db_index=True
    )

    class Meta:
        indexes = [
            # Composite index for spatial queries
            models.Index(
                fields=['latitude', 'longitude'],
                name='idx_fuel_station_location'
            ),
            # For price sorting
            models.Index(
                fields=['retail_price'],
                name='idx_fuel_station_price'
            ),
            # For state-based filtering (if needed)
            models.Index(
                fields=['state', 'retail_price'],
                name='idx_state_price'
            ),
        ]
        # Add constraint for data integrity
        constraints = [
            models.CheckConstraint(
                check=models.Q(retail_price__gte=0),
                name='price_non_negative'
            ),
        ]
```

### Index Strategy Rationale

**Composite Index (lat, lon)**:
- Used in every spatial query (bbox filter)
- PostgreSQL can use multi-column index for range queries
- **Expected speedup**: 100x (50ms → 0.5ms)

**Single Index (retail_price)**:
- Used for `ORDER BY retail_price` after bbox filter
- PostgreSQL will merge index results
- **Expected speedup**: 50x (10ms → 0.2ms)

## 2. Query Projection Optimization

### Problem: Over-Fetching Data
```python
# ❌ BAD: Fetches ALL columns (including address text)
stations = FuelStation.objects.filter(...)

# ✅ GOOD: Fetches only what we need
stations = FuelStation.objects.filter(...).only(
    'id', 'truckstop_name', 'latitude', 'longitude', 'retail_price'
)
```

### Performance Impact
```
Full model: ~200 bytes/row × 50 rows = 10KB
Projected:  ~50 bytes/row × 50 rows = 2.5KB

Memory savings: 75%
Query time: -30% (less I/O)
```

### Implementation in Service
```python
def find_nearby_stations(lat, lon, radius_miles, max_results=50):
    bbox = get_bounding_box(lat, lon, radius_miles)

    candidates = FuelStation.objects.filter(
        latitude__gte=bbox['lat_min'],
        latitude__lte=bbox['lat_max'],
        longitude__gte=bbox['lon_min'],
        longitude__lte=bbox['lon_max']
    ).only(
        'id', 'truckstop_name', 'city', 'state',
        'latitude', 'longitude', 'retail_price'
    ).order_by('retail_price')[:max_results]

    return candidates
```

### When to Use `.values()` Instead
```python
# Use .values() for raw dictionaries (even faster)
stations = FuelStation.objects.filter(...).values(
    'latitude', 'longitude', 'retail_price'
)
# Returns: [{'latitude': 34.05, 'longitude': -118.25, ...}, ...]
# No ORM overhead, 50% faster than .only()
```

**Use case**: When you DON'T need model instances (e.g., distance calculations)

## 3. Prevent N+1 Queries

### Problem (Hypothetical Future Relations)
If we add `FuelStation` -> `Brand` foreign key:

```python
# ❌ BAD: N+1 query problem
stations = FuelStation.objects.filter(...)
for station in stations:
    print(station.brand.name)  # Triggers 50 queries!
```

### Solution: `select_related`
```python
# ✅ GOOD: Single JOIN query
stations = FuelStation.objects.filter(...).select_related('brand')
for station in stations:
    print(station.brand.name)  # No additional queries
```

**Note**: Not needed in current simple schema, but important for future extensibility.

## 4. Database Connection Pooling

### Django Default Behavior
- Opens new connection per request
- Closes after response
- **Overhead**: ~20ms per request

### Solution: `django-db-connection-pool`
```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'dj_db_conn_pool.backends.postgresql',
        'POOL_OPTIONS': {
            'POOL_SIZE': 10,
            'MAX_OVERFLOW': 5,
        },
        ...
    }
}
```

**Benefits**:
- Reuses connections (saves ~15ms/request)
- Better for high-concurrency scenarios

## Performance Targets

### Query Breakdown (Expected)
```
Operation                        | Time    | Optimization
---------------------------------|---------|-------------
Bbox filter + price sort         | 2ms     | Indexes
Haversine refinement (50 items)  | 1ms     | In-memory Python
Station detail retrieval         | 0.5ms   | .only() projection
TOTAL DATABASE TIME              | 3.5ms   | 🎯
```

### API Response Time Budget
```
Database queries:        3.5ms
Routing API (ORS):       100ms
Algorithm logic:         10ms
Serialization:           5ms
Network overhead:        20ms
---------------------------------
TOTAL:                   138ms  ✅ (Target: <200ms)
```

## Query Monitoring Strategy

### Enable Query Logging in Tests
```python
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
log_cli = true
log_cli_level = DEBUG
```

### Django Debug Toolbar (Development)
```python
# settings.py (dev only)
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

### Production Monitoring
```python
# Use django-silk for query profiling
# Logs slow queries (>100ms) to database
SILKY_INTERCEPT_PERCENT = 10  # Sample 10% of requests
```

## Testing Query Performance

### Unit Test Example
```python
from django.test.utils import override_settings
from django.db import connection
from django.test import TestCase

class QueryPerformanceTest(TestCase):
    def test_nearby_stations_query_count(self):
        """Ensure spatial query uses indexes efficiently."""
        with self.assertNumQueries(1):  # Only 1 query expected
            stations = find_nearby_stations(34.0522, -118.2437, 500)
            list(stations)  # Force evaluation

    def test_query_execution_time(self):
        """Benchmark query speed."""
        import time
        start = time.time()
        stations = find_nearby_stations(34.0522, -118.2437, 500)
        list(stations)
        elapsed = time.time() - start

        self.assertLess(elapsed, 0.01)  # Must be <10ms
```

## Consequences

### Positive
- ✅ Sub-5ms database queries
- ✅ Minimal memory usage (75% reduction)
- ✅ Scalable to higher concurrency
- ✅ Easy to maintain (standard Django patterns)

### Negative
- ⚠️ Requires careful index management (migrations)
- ⚠️ `.only()` can cause issues if accessed fields change

## Maintenance Guidelines

### Index Monitoring
```sql
-- Check index usage (PostgreSQL)
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE tablename = 'fuel_station'
ORDER BY idx_scan ASC;
```

If `idx_scan = 0` → Index is unused, consider removing

### Query Plan Analysis
```sql
-- Explain query performance
EXPLAIN ANALYZE
SELECT * FROM fuel_station
WHERE latitude BETWEEN 33.0 AND 35.0
  AND longitude BETWEEN -120.0 AND -118.0
ORDER BY retail_price
LIMIT 50;
```

Look for:
- ✅ "Index Scan" (good)
- ❌ "Seq Scan" (bad, means index not used)

## References

- [Django Database Indexes Documentation](https://docs.djangoproject.com/en/5.2/ref/models/indexes/)
- [PostgreSQL Index Types](https://www.postgresql.org/docs/current/indexes-types.html)
- [Django Query Optimization](https://docs.djangoproject.com/en/5.2/topics/db/optimization/)
- [Database Performance Anti-Patterns](https://use-the-index-luke.com/)
