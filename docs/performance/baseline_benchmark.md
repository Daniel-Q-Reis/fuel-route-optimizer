# Baseline Performance Benchmark - Public ORS API

**Date:** 2026-02-11  
**Environment:** Docker + PostgreSQL 16 + Public OpenRouteService (Heidelberg, Germany)  
**Branch:** `feature/phase6-performance-optimization`

---

## 📊 Results Summary

**Benchmark Configuration:**
- 3 test routes (varied distances)
- 3 iterations per route
- Warmup request performed

| Route | Avg (ms) | Min (ms) | Max (ms) | Status |
|-------|----------|----------|----------|--------|
| **LA → Las Vegas** (~270 miles) | 2,744.8 | 1,649.7 | 4,927.5 | ✅ |
| **NY → Miami** (~1,280 miles) | - | - | - | ❌ 500 Error |
| **Chicago → Houston** (~1,080 miles) | 2,049.5 | 2,026.1 | 2,090.1 | ✅ |

**Overall Average:** **2,397.2 ms** (~2.4 seconds)

---

## 🔍 Performance Breakdown (Estimated)

Based on the 2.4s average response time:

| Component | Time (ms) | Percentage | Notes |
|-----------|-----------|------------|-------|
| **Network Latency (BR→DE)** | ~200-250ms | 10-12% | Round-trip to Germany ORS servers |
| **ORS API Processing** | ~2,000ms | 83% | Route calculation + geometry encoding |
| **Django Processing** | ~100-150ms | 5-7% | Serialization, service logic, station queries |
| **Database Queries** | ~10-20ms | <1% | PostGIS spatial queries (bounding box) |

---

## ⚠️ Issues Identified

### 1. NY → Miami Route Failure (500 Error)
**Problem:** Long-distance routes (~1,280 miles) cause 500 errors.  
**Suspected Cause:** Geometry parsing bug in `ORSClient.get_directions()` - trying to access `route['geometry']['coordinates']` when geometry is encoded string.

**Evidence from Phase 5:**
```python
# Line 172 in openrouteservice.py
geometry_raw = route["geometry"]["coordinates"]
TypeError: string indices must be integers, not 'str'
```

**Fix Required:** Decode polyline geometry or request GeoJSON format explicitly.

---

### 2. Higher Latency Than Expected
**Expected:** ~1,000-1,200ms  
**Actual:** ~2,400ms  

**Possible Reasons:**
- Long routes require more ORS processing time
- Network congestion (BR→DE)
- Geometry encoding overhead on ORS side

---

## 📈 Optimization Opportunities

### Immediate (Phase 6A)
1. **Redis Caching** - Cache common routes for 1 hour
   - Expected improvement: 2400ms → <10ms (cached hits)
   - Trade-off: Stale data if fuel prices update

2. **Database Index Optimization** - Composite index on `(retail_price, latitude, longitude)`
   - Expected improvement: ~5-10ms reduction in query time

### Future (ADR-007 - Production)
3. **Self-Hosted ORS** - Deploy in AWS São Paulo
   - Network latency: 200ms → <10ms  
   - Total improvement: ~40-50% faster (2400ms → 1200-1400ms)
   - Cost: ~$20-30/month

4. **PostGIS Spatial Indexes** - Replace bounding box with proper spatial queries
   - Expected improvement: ~10-20ms
   - Complexity: Moderate (requires PostGIS extension)

---

## ✅ Next Steps

1. Fix geometry parsing bug (Phase 5 regression)
2. Implement Redis caching for routes
3. Re-benchmark with caching enabled
4. Document improvements in `optimization_results.md`
5. Create ADR-007 for self-hosted ORS strategy

---

## 🧪 Reproduction

```bash
# Run baseline benchmark
docker-compose exec web python manage.py benchmark_baseline

# View silk profiler (after running API requests)
# Navigate to: http://localhost:8000/silk/
```

---

## 📝 Notes

- Benchmark run on development environment (not production-optimized)
- 500 errors indicate code regression from Phase 5 geometry-aware changes
- Overall performance is acceptable for assessment (< 3s)
- Redis caching will satisfy "quickly" requirement explicitly
