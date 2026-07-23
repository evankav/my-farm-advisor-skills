# Supplementary Dashboard Information

## Project Overview

The Integrated Field Intelligence Dashboard provides a unified, interactive comparison of three demonstration growers across the U.S. Corn Belt: northern Illinois (Iroquois County), northern Iowa (Kossuth County), and central Nebraska (York County). The dashboard synthesizes data from Assignments 1-3 into six tabs covering field locations, weather, crop distribution, vegetation health, and evidence-based interpretation.

**Core narrative**: Although Illinois, Iowa, and Nebraska all lie within the U.S. Corn Belt, the data show meaningful differences in field characteristics, weather patterns, cropping practices, soil drainage, and vegetation timing. These differences form a west-to-east gradient: moving west across the Corn Belt, fields become more compact (center-pivot irrigation), precipitation decreases while temperature increases, and crop rotations diversify.

The dashboard is generated as a single self-contained HTML file with Plotly interactive charts. It has zero runtime external dependencies — all JavaScript is inlined, no CDN calls are made.

## Dataset Description

All data is sourced from the pipeline runtime tree under `${DATA_PIPELINE_DATA_ROOT}/data-pipeline`. Seven summary CSV files are pre-computed by `prepare_dashboard_data.py` (Phase A) and consumed by `generate_final_dashboard.py` (Phase B).

### Summary CSV Files

| File | Rows | Key Columns | Source |
|------|------|-------------|--------|
| `dashboard_field_summary.csv` | 30 (10 per grower) | `grower, field_id, centroid_lat, centroid_lon, area_acres, compactness` | Field boundary GeoJSON from OpenStreetMap/Overpass |
| `dashboard_weather_summary.csv` | 36 (3 growers x 12 months) | `grower, month, mean_temp_c, mean_precip_mm_day, field_count` | NASA POWER daily weather aggregated by month |
| `dashboard_crop_summary.csv` | ~12-15 (crop entries) | `grower, crop_name, pct_total, is_dominant` | USDA CDL 2021-2025 full composition |
| `dashboard_rotation_summary.csv` | ~8-15 (transition pairs) | `grower, from_crop, to_crop, probability` | CDL composition, computed from consecutive-year dominant crops |
| `dashboard_vegetation_summary.csv` | ~9 (NDVI observations) | `grower, field_id, date, ndvi_mean` | Sentinel-2 NDVI rasters (field mean) via Planetary Computer STAC API |
| `dashboard_data_coverage.csv` | 3 (one per grower) | `grower, total_fields, weather_fields, cdl_years, ndvi_fields, soil_fields` | Counted from pipeline runtime |
| `dashboard_soil_summary.csv` | ~30 (per-field SSURGO) | `grower, field_id, drainage_class, avg_ph, avg_om_pct, dominant_soil` | USDA NRCS SSURGO via SDA API |

### Data Sources

| Source | Product | Resolution | Period |
|--------|---------|------------|--------|
| OpenStreetMap / Overpass API | Field boundaries | Vector polygons | Static (downloaded once) |
| USDA NASS Cropland Data Layer (CDL) | Crop classification | 30 m raster | 2021-2025 |
| NASA POWER | Daily weather (temperature, precipitation) | 0.5 x 0.625 grid | 2021-2025 |
| Sentinel-2 via Planetary Computer | NDVI (Normalised Difference Vegetation Index) | 10 m raster | 2025 (confirmed fields) |
| USDA NRCS SSURGO via SDA | Soil map units, drainage, pH, organic matter | 1:12,000-1:24,000 | Static |

## Dashboard Explanation

### Navigation

The dashboard has six tabs accessed via the top navigation bar. Click a tab to switch views. The grower filter checkboxes (Illinois, Iowa, Nebraska) are displayed in the header for future cross-filtering; currently all three growers are shown.

### Tab 1 — Overview

- **Stat cards**: Eight summary cards showing grower count, total fields, total acreage, crop type count, years covered, weather field count, NDVI field count, and soil field count.
- **Grower comparison table**: Per-grower metrics including median and total acreage, dominant crop, weather field coverage, mean temperature, mean precipitation, average soil pH, and average organic matter.
- **Field size distribution**: Boxplot comparing field acreage distributions across the three growers.
- **Field compactness**: Overlaid histograms showing perimeter-to-area ratios. Lower values indicate more compact (circular) fields.
- **Soil drainage**: Grouped bar chart showing SSURGO drainage class distribution per grower.

### Tab 2 — Field Locations

- **Interactive map**: All 30 field centroids on an OpenStreetMap basemap, colored by grower and sized by acreage. Hover over any marker to see field ID and area. Zoom and pan with mouse or touch.

### Tab 3 — Weather and Environmental Conditions

- **Monthly temperature cycle**: Multi-line chart with 10 C reference line. Shows the growing season window for each region.
- **Monthly precipitation**: Grouped bar chart comparing mean daily precipitation by month. Nebraska is consistently driest; Illinois wettest.
- **Climate space**: Scatter plot of monthly mean temperature vs. precipitation. Reveals the agro-climatic gradient of the western Corn Belt.

### Tab 4 — Crop Distribution

- **Crop composition**: Stacked 100% bar chart showing CDL-derived crop mix for each grower. All three are corn-soybean dominant but differ in their third crops.
- **Crop rotation transitions**: Faceted heatmaps showing the probability of transitioning from one crop to another between consecutive years. Iowa's continuous-corn signal is visible.

### Tab 5 — Vegetation Health

- **NDVI time series**: Sentinel-2 field-mean NDVI for the confirmed field-year with peak annotation. This chart will show a placeholder message if no NDVI summary data is available.
- **Cumulative Growing Degree Days**: GDD progression with crop-specific growth-stage milestones (soybean or corn). The GDD chart requires per-field daily weather CSV data; if unavailable, it shows a placeholder.

### Tab 6 — Interpretation

- **Key observations**: Evidence-based bullet points summarising the most important cross-grower comparisons.
- **Limitations**: Clear disclosure of data coverage gaps, source resolution limitations, and analytical constraints. All conclusions are observational; no causal claims are made.

## Analytical Interpretation

The following observations are drawn directly from the pipeline data and are embedded in the dashboard's Interpretation tab:

### Field Characteristics
- **Iowa** fields are the largest (median ~118 ac, up to 307 ac), consistent with the flat glacial till plains of the prairie pothole region and large farm operations.
- **Nebraska** fields cluster in a moderate range (median ~30 ac), reflecting center-pivot irrigation circle sizes.
- **Illinois** shows the widest spread including very small fields (< 5 ac), suggesting more fragmented land ownership or smaller farming operations.
- Nebraska fields are distinctly more compact (lowest perimeter/area ratio), consistent with circular center-pivot irrigation. Illinois and Iowa have higher ratios, reflecting irregular rectilinear boundaries typical of rain-fed row-crop agriculture.

### Climate and Environment
- Nebraska is consistently the warmest and driest grower. This precipitation deficit explains why center-pivot irrigation is common — natural rainfall alone is insufficient to meet corn water requirements during peak summer months.
- Illinois is cool-wet with the highest precipitation in every month.
- Iowa is the coldest location with moderate precipitation. The 10 C growing-season threshold is crossed latest in spring and earliest in fall, giving Iowa the shortest potential growing season.
- The three growers occupy distinct but overlapping regions of climate space, forming a clear west-to-east agro-climatic gradient.

### Crop Management
- All three growers are corn-soybean dominant (>85% of CDL pixels), confirming their Corn Belt identity.
- Each state has a distinctive third crop: alfalfa in Iowa, winter wheat in Nebraska, forest patches in Illinois.
- Nebraska has notable fallow/idle pixels, consistent with a drier climate requiring occasional fallow periods.
- Corn-soybean alternation dominates rotations in all three states. Iowa shows evidence of continuous corn (P(corn to corn) ~0.25), not observed in Illinois or Nebraska.
- Nebraska shows weak fallow-to-fallow persistence. Illinois forest patches do not cycle back to cropland, suggesting permanent non-crop areas.

### Soil Drainage
- SSURGO drainage class distributions reflect underlying parent materials: Iowa fields on the Des Moines Lobe tend toward somewhat poorly to poorly drained soils, consistent with the need for tile drainage in this region.
- Nebraska loess uplands are predominantly well-drained, suitable for irrigated row crops.
- Illinois shows a mix of moderately well-drained to somewhat poorly drained soils on glacial till parent material.

### Vegetation Health
- NDVI data is confirmed only for a single field-year (osm-1499474531, northern Illinois, Soybeans 2025). The NDVI curve shows the expected soybean seasonal pattern: rapid green-up in June-July, peak in late July/August, and gradual decline through September-October consistent with senescence.
- This single-field observation is adequate for demonstrating the NDVI monitoring capability but does not support cross-grower vegetation comparisons.

## Limitations

### Data Coverage
- **Weather asymmetry**: Illinois and Iowa have daily weather data for only 3 of 10 fields each, while Nebraska covers all 10. Temperature and precipitation comparisons should be interpreted with this uneven sampling in mind.
- **NDVI scope**: Only one field-year is confirmed with aligned NDVI observations (osm-1499474531, Illinois, Soybeans 2025). The Vegetation Health tab visualisation is not a cross-grower comparison.
- **Temporal window**: Five years (2021-2025) is informative but does not represent long-term climate norms or full rotation cycles.

### Data Sources
- **Field boundaries**: Sourced from OpenStreetMap, which is volunteer-contributed data and may not align precisely with surveyed property lines or official parcel records.
- **CDL classification**: USDA Cropland Data Layer is satellite-derived at 30 m resolution. Classification accuracy varies by crop and region. Field-edge pixels may be aliased or misclassified.
- **Weather data**: NASA POWER is a gridded reanalysis product (0.5 x 0.625), not on-farm weather station measurements. It may underrepresent spatially localized convective summer storms.
- **SSURGO soil data**: Map unit scale is 1:12,000 to 1:24,000. Soil properties are assigned per map unit component, not measured at individual field locations. Only the top 30 cm is queried. Some components may have null values for certain properties.
- **NDVI**: Sentinel-2 observations are limited by cloud cover and the 5-day revisit cycle. Gaps between scenes are genuine satellite constraints, not data errors.

### Analytical Constraints
- All conclusions are **observational comparisons**, not causal statements. The data does not support claims about why differences exist.
- Sample size is small (10 fields per grower, in single counties). Results may not generalise to the broader state or region.
- Weather data from 3 fields may not be representative of the entire 10-field set within a grower.
- Rotation transition counts are small (4 transitions per field over 5 years). A single continuous-corn field in Iowa heavily influences the Iowa transition matrix.

## Regeneration

The dashboard is fully reproducible from the pipeline runtime. Ensure `DATA_PIPELINE_DATA_ROOT` is exported and points to a populated runtime, then run:

```bash
export DATA_PIPELINE_DATA_ROOT=/absolute/path/to/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/reporting/prepare_dashboard_data.py
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/reporting/generate_final_dashboard.py
```

Output: `${DATA_PIPELINE_DATA_ROOT}/data-pipeline/shared/dashboard/integrated_field_intelligence_dashboard.html`

The dashboard can also be generated directly from a pre-existing summary directory:

```bash
python scripts/reporting/generate_final_dashboard.py \
  --summary-dir /path/to/summary_csvs \
  --output ~/Desktop/dashboard.html
```
