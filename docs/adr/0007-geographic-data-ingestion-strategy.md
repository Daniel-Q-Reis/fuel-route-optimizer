# ADR-007: Geographic Data Ingestion Strategy via Greedy Cost-Optimal Sampling

## Status
Accepted

## Context
The project relies on a dataset of 8,151 fuel stations (`fuel-prices-for-be-assessment.csv`) which contains physical addresses but lacks geospatial coordinates (Latitude/Longitude). The current routing engine (OpenRouteService - ORS) requires precise coordinates to calculate route deviation and optimization.

**Constraint:** The public ORS Geocoding API has a strict rate limit of 2,000 requests per day. Geocoding the full dataset would take approximately 4 days or require a paid enterprise license/local infrastructure which is out of scope for the current MVP phase.

## Decision
We will adopt a **"Greedy Cost-Optimal Stratified Sampling"** strategy for data ingestion. Instead of loading the entire dataset, we will ingest only the **top 14 cheapest fuel stations per state**.

This reduces the geocoding load from 8,151 to ~754 requests, allowing the entire database to be populated in a single run (~12 minutes) while consuming less than 40% of the daily API quota.

## Statistical Validation Method
To ensure this sampling method does not compromise the routing algorithm's ability to find viable stops, we performed a statistical analysis on the source data:

**Sampling Method:** Stratified sampling grouped by State, sorted by Retail Price (ascending), limiting k=14.

### Metric A - City Diversity Index (CDI):

Formula:
$$
CDI = \frac{\text{Unique Cities in Sample}}{\text{Total Stations in Sample}}
$$

**Result:** The global average CDI is **0.66**.

**Interpretation:** For every 14 stations selected, they are distributed across approximately 9 unique cities. This confirms that low-price stations are not hyper-concentrated in a single location, maintaining acceptable geographic spread for highway routing.

### Metric B - Economic Relevance:
The selected sample has an average retail price **8.72% lower** than the state mean.

Since the core objective function of the algorithm is cost minimization, stations excluded by this filter (the most expensive 90%) are statistically irrelevant as they would be rejected by the algorithm in favor of cheaper alternatives regardless of location.

## Consequences

### Positive
*   **Performance:** Data ingestion time reduced by 91%.
*   **Compliance:** Fully compliant with OpenRouteService public tier limits.
*   **Relevance:** The database is populated exclusively with high-value nodes (lowest cost), improving the "signal-to-noise" ratio for the optimization engine.

### Negative / Risks
*   **Geographic Clustering Risk:** Analysis identified 5 regions (specifically NY, QC, NS, MB, SK) where the CDI is low (< 0.25), meaning cheap stations are clustered in fewer than 3 cities.

*   **Mitigation:** For the MVP, this risk is accepted. If "Out of Fuel" errors occur in these specific regions during E2E testing, we will implement a "Hybrid Sampling" fallback (Top 10 Cheapest + 4 Random Spatial) for those specific states.
