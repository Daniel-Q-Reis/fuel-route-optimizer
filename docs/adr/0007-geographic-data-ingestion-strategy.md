# ADR-004: Geographic Data Ingestion Strategy via Expanded Greedy Cost-Optimal Sampling (n=30)

## Status
Accepted

## Context
The project relies on a dataset of 8,151 fuel stations (`fuel-prices-for-be-assessment.csv`) which contains physical addresses but lacks geospatial coordinates (Latitude/Longitude).
The current routing engine (OpenRouteService - ORS) requires precise coordinates to calculate route deviation and optimization.

**Constraint:** The public ORS Geocoding API has a strict rate limit of 2,000 requests per day. Geocoding the full dataset would take approximately 4 days or require a paid enterprise license/local infrastructure, which is out of scope for the current MVP phase.

## Decision
We will adopt an **"Expanded Greedy Cost-Optimal Stratified Sampling"** strategy for data ingestion. Instead of loading the entire dataset, we will ingest the **top 30 cheapest fuel stations per state**.

This reduces the geocoding load from **8,151** to **~1,535 requests**, allowing the entire database to be populated in a single run (~50 minutes with safety delays) while consuming approximately **76%** of the daily API quota.

## Statistical Validation Method
To ensure this expanded sampling method improves geographic coverage without compromising the routing algorithm's cost efficiency, we performed a statistical analysis on the source data:

1.  **Sampling Method:** Stratified sampling grouped by `State`, sorted by `Retail Price` (ascending), limiting $k=30$.
2.  **Metric A - City Diversity Index (CDI):**
    * **Formula:** $CDI = \frac{\text{Unique Cities in Sample}}{\text{Total Stations in Sample}}$
    * **Result:** The global average CDI is **0.62**.
    * **Interpretation:** For every 30 stations selected, they are distributed across approximately **19 unique cities**. This represents a significant improvement in geographic spread compared to smaller samples ($k=14$), effectively eliminating "routing holes" in major US states (e.g., Texas achieved a perfect CDI of 1.0).
3.  **Metric B - Economic Relevance:**
    * The selected sample has an average retail price **6.65% lower** than the state mean.
    * **Conclusion:** While slightly less aggressive than the top-14 strategy, this sample still prioritizes the most economically relevant nodes. Stations excluded (the most expensive 75%) remain statistically irrelevant for a cost-minimization algorithm.

## Consequences

### Positive
* **Coverage Reliability:** Increasing the sample size to 30 doubles the density of available stops, drastically reducing the risk of "Out of Fuel" exceptions in rural areas.
* **Performance:** Data ingestion volume reduced by **81%** compared to the full dataset.
* **Compliance:** Fits within the OpenRouteService public tier limits (daily cap).

### Negative / Risks
* **Quota Saturation:** Consuming 76% of the daily limit leaves a slim margin for error. Multiple runs in a single day will trigger a 403 Forbidden error.
* **Geographic Clustering (Edge Cases):** Analysis still identifies 5 specific regions (QC, NS, SK, MB, YT) where the CDI remains low ($< 0.25$) due to sparse source data.

### Mitigation: Smart Idempotency & Circuit Breaker
To mitigate the risk of quota exhaustion during development or re-runs, the ingestion script **MUST** implement an idempotency check and an automatic circuit breaker.

**Implementation Standard:**
The following logic is mandatory in the ingestion loop to prevent API waste:

```python
# PREVENTIVE MECHANISM: Check local DB before calling API.
# This ensures previously loaded data DOES NOT consume API requests.
if FuelStation.objects.filter(
    truckstop_name=truckstop_name, city=city, state=state
).exists():
    print(f"⏩ Skipping existing: {truckstop_name}")
    skipped += 1
    continue  # Skip to next iteration

# API CALL EXECUTION
try:
    # ... geocoding logic ...
    
    # Rate limit: 40 req/min = 1.5s/req. Safe margin: 2.0s
    time.sleep(2.0) 

except Exception as e:
    print(f"Failed to geocode {full_address}: {e}")
    
    # AUTOMATIC BREAK: Stop if API limit (403) or Rate limit (429) hit
    error_str = str(e).lower()
    if "403" in error_str or "forbidden" in error_str or "429" in error_str:
        print("\n🛑 STOPPING: API Quota exhausted or Rate Limit hit. Please check your ORS Key.")
        break
```