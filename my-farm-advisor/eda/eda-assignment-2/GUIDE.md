---
name: eda-assignment-2
description: Field-level EDA comparing Illinois, Iowa, and Nebraska growers on field boundaries, CDL/cropland data, and weather. Designed for Assignment 2 dataset analysis.
version: 1.0.2
author: Assignment 2
tags: [eda, comparison, boundaries, cdl, weather, illinois, iowa, nebraska]
---

# Workflow: eda-assignment-2

## Central argument

Although Illinois, Iowa, and Nebraska all lie within the U.S. Corn Belt, the data show meaningful differences in field characteristics, weather patterns, and cropping practices across the sampled growers.

Every visualization below contributes evidence toward this argument. Figures that do not support cross-grower comparison or answer a specific analytical question have been excluded.

## Data sources

- **Field boundaries**: `growers/<grower>/farms/<farm>/boundary/field_boundaries.geojson`
- **CDL composition**: `growers/<grower>/farms/<farm>/derived/tables/<farm>_cdl_2021_2025_full_composition.csv`
- **Weather**: `growers/<grower>/farms/<farm>/derived/tables/<farm>_weather_2021_2025.csv`
- **State boundaries**: `shared/geoadmin/l1_states/states_usa.geojson`

## Quick Start

```bash
export DATA_PIPELINE_DATA_ROOT=$HOME/my-farm-advisor-runtime
export DATA_PIPELINE_VENV_DIR="${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv"

cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_VENV_DIR}/bin/python" \
  /home/coder/.config/opencode/skills/my-farm-advisor/eda/eda-assignment-2/scripts/eda_assignment2.py
```

Output: `${DATA_PIPELINE_DATA_ROOT}/data-pipeline/eda/eda-assignment-2/output/*.png`

---

## Category 1: Field boundaries

### Figure 1 — Field size distribution by grower

**File:** `field_size_distribution_by_grower.png`

**Question:** How do field sizes compare across the three Corn Belt regions?

**Evidence:** Boxplot showing the distribution of `area_acres` for all 10 fields in each state. Individual points are overlaid (jittered) to show every field.

**Conclusion:** Iowa has the largest fields (median ~118 ac, up to 307 ac), consistent with the prairie pothole region's flat glacial till plains and large farm operations. Nebraska fields cluster in a moderate range (median ~30 ac, max 133 ac), reflecting the characteristic size of center-pivot irrigation circles. Illinois shows the widest spread including very small fields (~3 ac), which may reflect more fragmented land ownership or smaller farming operations. Only Iowa has fields exceeding 200 acres.

**Limitations:** The sample size is small (10 fields per state). Field boundaries come from OpenStreetMap and may not perfectly align with official property lines. The `area_acres` column was pre-computed by the pipeline in a projected CRS.

---

### Figure 2 — Field compactness by grower

**File:** `field_compactness_by_grower.png`

**Question:** Are Nebraska center-pivot fields more compact (circular) than irregular Illinois and Iowa fields?

**Evidence:** Histogram of the perimeter-to-area ratio (m / m²). Lower values indicate more compact shapes (a circle minimizes perimeter for a given area).

**Conclusion:** Nebraska fields are the most compact (tightest peak at the lowest values), consistent with circular center-pivot irrigation. Iowa and Illinois fields have higher and more variable perimeter-to-area ratios, reflecting irregular, rectilinear field boundaries typical of row-crop agriculture without circular irrigation infrastructure.

**Limitations:** The perimeter/area ratio depends on field size (small fields naturally have higher ratios), which is partially confounded with shape. A shape index normalized for area (e.g., the Pattyn or SHAPE index) would provide a size-independent comparison but involves more complex computation.

---

### Figure 3 — Field size vs. latitude

**File:** `field_size_vs_latitude.png`

**Question:** Is there a geographic (north-south) pattern in field sizes across the sampled growers?

**Evidence:** Scatter plot of field area (acres) against centroid latitude (°N), with points colored by grower.

**Conclusion:** A clear latitudinal separation exists: Iowa fields (43.1–43.3°N) are distinctly further north than Illinois and Nebraska fields (both ~40.5–41.0°N). Iowa's northern fields are also the largest, while Illinois and Nebraska occupy similar latitudes but differ markedly in field size. Latitude alone does not explain the Illinois–Nebraska difference — other factors (irrigation infrastructure, land use history, soil type) must be involved.

**Limitations:** The geographic extent is limited to three counties. Within-state latitude variation is small, so the plot primarily separates states rather than showing a continuous gradient.

---

## Category 2: CDL / Cropland data layer

### Figure 4 — Crop composition by grower

**File:** `crop_composition_by_grower.png`

**Question:** How does the crop mix differ across Illinois, Iowa, and Nebraska?

**Evidence:** Stacked 100% bar chart of total CDL pixel counts aggregated over all 10 fields and all 5 years (2021–2025), grouped by grower.

**Conclusion:** All three growers are dominated by corn and soybeans (>85% of pixels in each state), confirming their Corn Belt identity. However, each state has a distinctive "signature" third crop: Iowa includes alfalfa (code 28, visible as ~2% of pixels), Nebraska includes winter wheat (code 24), and Illinois includes forest patches (code 36). Nebraska also has notable Fallow/Idle pixels, consistent with a drier climate requiring occasional fallow periods.

**Limitations:** The CDL is satellite-derived at 30 m resolution, so very small features may be aliased. Pixel counts aggregate across fields and years, which may obscure year-to-year rotation variation. The "Other" category aggregates minor crop codes not in the crop-specific list.

---

### Figure 5 — Field-level crop purity by grower

**File:** `crop_purity_by_grower.png`

**Question:** Are fields in some regions more homogeneous (planted to a single crop) than others?

**Evidence:** Boxplot of the `pct` column for the dominant crop in each field-year observation (50 observations per grower: 10 fields × 5 years). Values near 100% indicate a pure, single-crop field.

**Conclusion:** All three growers show high median purity (>90%), indicating that fields are predominantly managed as single-crop units. Iowa shows slightly higher purity (median ~96%), while Nebraska shows a wider spread with some fields falling below 80%. The Nebraska outliers may reflect field edge effects from circular pivot boundaries intersecting 30 m CDL pixels, or more heterogeneous management within pivot circles.

**Limitations:** The dominant-crop percentage is computed from CDL raster pixels, not ground-truth observations. Edge pixels (mixed at field boundaries) artificially lower purity for irregularly shaped fields.

---

### Figure 6 — Crop rotation transition probabilities

**File:** `crop_transition_heatmap.png`

**Question:** Do rotation strategies differ by state?

**Evidence:** Three-panel heatmap showing, for each state, the probability of transitioning from a crop in year _t_ to a crop in year _t+1_. Computed from consecutive-year crop pairs for each field across 2021–2025.

**Conclusion:** The dominant pattern in all three states is alternating corn-soybean rotation (P(corn → soy) ≈ 0.5 and P(soy → corn) ≈ 0.5). Iowa shows a notable deviation: a continuous-corn transition P(corn → corn) ≈ 0.25, indicating at least one field of continuous corn. Iowa also has alfalfa appearing as a rotation entry. Illinois has a forest transition that does not cycle back to cropland (likely a permanent patch). Nebraska has a weak fallow → fallow signal.

**Limitations:** Only 4 transitions per field (2021→2022 through 2024→2025), so transition counts are small. A single continuous-corn field in Iowa heavily influences the Iowa transition matrix. The 5-year window is too short to fully characterize rotation cycles.

---

## Category 3: Weather

### Figure 7 — Monthly temperature cycle

**File:** `monthly_temperature_cycle.png`

**Question:** How does the growing season window differ across the three locations?

**Evidence:** Mean monthly temperature (2021–2025 average) for each grower, with a 10°C reference line commonly used as a threshold for corn growth.

**Conclusion:** Nebraska is consistently the warmest producer (mean T2M ~12°C, growing season roughly April–October above 10°C). Iowa is the coldest (mean T2M ~9.4°C, growing season roughly May–September). Illinois is intermediate. The 10°C threshold line shows Iowa crosses it latest in spring and earliest in fall, giving it the shortest potential growing season.

**Limitations:** Weather data covers only 3 of 10 fields for Illinois and Iowa (vs. 10 of 10 for Nebraska), as noted in the figure annotation. These 3 fields may not be fully representative of the entire county. Temperature is from NASA POWER, a gridded product (0.5° × 0.625°), not from on-farm weather stations.

---

### Figure 8 — Monthly precipitation by grower

**File:** `monthly_precipitation_by_grower.png`

**Question:** How does water availability vary across the three regions?

**Evidence:** Grouped bar chart of mean daily precipitation (mm/day) by month, averaged over 2021–2025.

**Conclusion:** Illinois receives the most precipitation in every month, especially during the growing season (May–August mean ~3.5–4.5 mm/day). Nebraska is the driest grower year-round (growing season mean ~2–3 mm/day). This precipitation deficit explains why center-pivot irrigation is common in Nebraska — natural rainfall alone is insufficient to meet corn water requirements during peak summer months. Iowa falls between the two.

**Limitations:** Same field-coverage limitation as Figure 7. Precipitation is total daily (liquid equivalent), not snowfall-adjusted. NASA POWER may underrepresent convective summer storms that are spatially localized.

---

### Figure 9 — Climate space by grower

**File:** `climate_space_by_grower.png`

**Question:** How do the three regions occupy different climate spaces when temperature and precipitation are considered together?

**Evidence:** Scatter plot of monthly mean temperature vs. monthly mean precipitation. Each point represents one calendar month averaged over 2021–2025, colored by grower.

**Conclusion:** The three growers occupy distinct but overlapping regions of climate space. Illinois occupies the cool-wet region (high precipitation, moderate temperatures). Nebraska occupies the warm-dry region (lower precipitation, higher temperatures). Iowa occupies the cold-intermediate region (coldest temperatures, moderate precipitation). This single plot summarizes the agro-climatic gradient of the western Corn Belt: moving west across the Corn Belt, temperatures increase while precipitation decreases.

**Limitations:** Monthly averages smooth out within-month variability. The number of points per grower is 12 (one per month), with IL and IA representing fewer underlying field observations.

---

## Category 4: Geospatial context

### Figure 10 — Field location map

**File:** `field_location_map.png`

**Question:** Where are the sampled fields located in geographic context?

**Evidence:** Map of Illinois, Iowa, and Nebraska state boundaries with all 30 field polygons overlaid, colored by grower. State abbreviations are shown at state centroids.

**Conclusion:** The fields are concentrated in three distinct counties: Iroquois County in eastern Illinois (~40.8°N, 87.7°W), Kossuth County in northern Iowa (~43.3°N, 94.2°W), and York County in southeastern Nebraska (~40.9°N, 97.6°W). The Iowa fields are distinctly separated (~2.5° latitude north of the others). The Illinois and Nebraska fields are at similar latitudes but separated by ~10° longitude. This geographic spread corresponds to meaningful differences in climate (continental gradient), soil parent material (glacial till vs. loess), and agricultural infrastructure (irrigation prevalence).

**Limitations:** The map shows field polygons at coarse scale — individual field shapes are visible but field boundaries are simplified by the map scale. The state-level boundary file is from Census TIGER 2025 at approximately 1:500k resolution.

---

## Output file summary

| # | File | Category | Type | Size |
|---|------|----------|------|------|
| 1 | `field_size_distribution_by_grower.png` | Boundaries | stat-viz | ~131 KB |
| 2 | `field_compactness_by_grower.png` | Boundaries | stat-viz | ~132 KB |
| 3 | `field_size_vs_latitude.png` | Boundaries | comparison | ~124 KB |
| 4 | `crop_composition_by_grower.png` | CDL | stat-viz | ~121 KB |
| 5 | `crop_purity_by_grower.png` | CDL | stat-viz | ~211 KB |
| 6 | `crop_transition_heatmap.png` | CDL | comparison | ~299 KB |
| 7 | `monthly_temperature_cycle.png` | Weather | stat-viz | ~245 KB |
| 8 | `monthly_precipitation_by_grower.png` | Weather | stat-viz | ~133 KB |
| 9 | `climate_space_by_grower.png` | Weather | comparison | ~161 KB |
| 10 | `field_location_map.png` | Geospatial | map | variable |

## Key limitations

- **Weather coverage**: Illinois and Iowa weather data represent 3 of 10 fields each (the Assignment 1 core) while Nebraska covers 10 of 10. Monthly aggregation reduces per-field noise, but sample sizes are uneven.
- **CDL resolution**: 30 m pixels may alias small fields and field-edge pixels. The cropland data layer is satellite-derived, not ground-truthed at the field level.
- **Field boundary source**: OpenStreetMap/Overpass data is volunteer-contributed and may not match surveyed property lines.
- **Time window**: 5 years (2021–2025) provides a useful but limited view of rotation patterns and climate norms.
- **Causality**: All conclusions are observational comparisons. The data does not support causal claims about why differences exist.
