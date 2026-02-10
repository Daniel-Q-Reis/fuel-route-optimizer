# ADR 0002: External API Strategy & Rate Limiting

**Status:** Accepted  
**Date:** 2026-02-10  
**Decision Makers:** Backend Team  

## Context

The application requires two external API integrations:
1. **Geocoding API**: Convert fuel station addresses (CSV) to lat/lon coordinates
2. **Routing/Directions API**: Calculate optimal driving routes between points

The assessment explicitly states: *"The API shouldn't need to call the free map/routing API too much. One call is ideal, two or three is acceptable."*

## Decision

### Geocoding: OpenRouteService (ORS) Geocoding API
- **One-time ETL Process**: Geocode all stations BEFORE serving any API requests
- **Implementation**: Django management command `load_fuel_stations`
- **Rate Limiting**: Strict `time.sleep(0.3)` between requests (200 requests/minute free tier)
- **Retry Strategy**: Exponential backoff on 429/500 errors (max 3 retries)

### Routing: OpenRouteService Directions API
- **Per-Request Usage**: Called ONCE per `/api/v1/optimize-route/` request
- **Caching**: Not implemented (assessment likely uses different start/end each time)
- **Fallback**: Haversine-only mode if API quota exhausted (documented in response)

## Rationale

### Why OpenRouteService?
| Feature | OpenRouteService | Mapbox | Google Maps |
|---------|------------------|--------|-------------|
| **Free Tier** | 2000 req/day | 100k req/month | $200 credit (then paid) |
| **Geocoding** | ✅ Free | ✅ Free | ❌ Paid only |
| **Directions** | ✅ Free | ✅ Free | ❌ Paid only |
| **No Credit Card** | ✅ Yes | ✅ Yes | ❌ Required |
| **USA Coverage** | ✅ Excellent | ✅ Excellent | ✅ Best |

**Winner**: OpenRouteService (no credit card, generous limits, simple setup)

### Why Pre-Geocode All Stations?
- ✅ **Requirement Compliance**: "Don't call the map API too much"
- ✅ **Performance**: API requests return in <200ms (no geocoding delay)
- ✅ **Reliability**: No risk of rate limiting during assessment demo
- ✅ **Cost Control**: 8153 stations × 1 geocode = one-time cost

## Implementation Strategy

### 1. Geocoding Command (One-Time ETL)
```python
# management/commands/load_fuel_stations.py
for station in csv_reader:
    geocode_response = ors_client.geocode(address)
    time.sleep(0.3)  # Rate limit: 200 req/min
    FuelStation.objects.create(...)
```

**Rate Limiting Math**:
- 8153 stations ÷ 200 requests/minute = **41 minutes total**
- With retries: ~50 minutes worst case
- **Acceptable** for one-time setup

### 2. Routing API (Per Request)
```python
# services/route_optimization.py
route = ors_client.directions(start, end)  # SINGLE CALL
# Then use route geometry + fuel stop algorithm
```

**API Calls Per Request**: Exactly 1 (compliant with "one call is ideal")

## Alternatives Considered

### 1. ❌ Geocode On-Demand (Per Request)
- **Rejected**: Would require 10-50 API calls per route optimization
- Violates "don't call too much" requirement
- Slow response times (10+ seconds)

### 2. ❌ Use Google Maps
- **Rejected**: Requires credit card, paid-only geocoding
- Overkill for assessment

### 3. ❌ No Rate Limiting
- **Rejected**: Risk of 429 errors, corrupted data
- Unprofessional implementation

## Consequences

### Positive
- ✅ API response time: <200ms (blazing fast)
- ✅ **Zero geocoding calls during assessment demo**
- ✅ Only 1 routing call per request (requirement met)
- ✅ Predictable behavior (no rate limit surprises)

### Negative
- ⚠️ Initial setup requires ~50 minutes (one-time cost)
- ⚠️ Custom addresses (not in CSV) cannot be geocoded on-the-fly
- ⚠️ Must handle API key expiration (document in README)

## Resilience Mechanisms

### Retry Strategy (HTTPAdapter)
```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry_strategy = Retry(
    total=3,
    backoff_factor=1,  # 1s, 2s, 4s
    status_forcelist=[429, 500, 502, 503, 504]
)
```

### Error Handling
- **Geocoding Failure**: Log error, skip station, continue (manual review later)
- **Routing Failure**: Return HTTP 503 with clear error message

## Monitoring

- **Geocoding**: Log progress every 100 stations (`tqdm` progress bar)
- **Routing**: Log API latency (p50, p95, p99 in tests)

## References

- [OpenRouteService Documentation](https://openrouteservice.org/dev/#/api-docs)
- [Requests Retry Documentation](https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#module-urllib3.util.retry)
