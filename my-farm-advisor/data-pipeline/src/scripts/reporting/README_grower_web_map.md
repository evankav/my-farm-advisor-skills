# Grower Web-Map Subskill

## Purpose

Generate a lightweight, interactive HTML map for each grower in the My Farm Advisor data pipeline. The map displays every field polygon for every farm belonging to the grower, rendered on an ESRI World Imagery satellite basemap with click-to-inspect popups and a sidebar field list.

## Requirements

- Python 3.10+
- Standard library only (no extra pip packages)
- Internet connection for Leaflet.js CDN and satellite tile loading
- `DATA_PIPELINE_DATA_ROOT` exported and pointing to a valid runtime tree

## Usage

### From the runtime source copy

```bash
export DATA_PIPELINE_DATA_ROOT=/absolute/path/to/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/reporting/generate_grower_web_map.py \
  --grower-slug northern-illinois-grower
```

Or rely on the `AG_GROWER_SLUG` environment variable:

```bash
export AG_GROWER_SLUG=northern-iowa-grower
export DATA_PIPELINE_DATA_ROOT=/absolute/path/to/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/reporting/generate_grower_web_map.py
```

### Output

The script writes a single self-contained HTML file to:

```
${DATA_PIPELINE_DATA_ROOT}/data-pipeline/growers/<grower>/derived/reports/<grower>_web_map.html
```

Example:
- `growers/northern-illinois-grower/derived/reports/northern-illinois-grower_web_map.html`

## Map Features

- **ESRI World Imagery satellite basemap** — high-resolution aerial imagery, free, no API key required.
- **All field polygons** — one layer per field, color-coded for visual distinction.
- **Click popup** — shows grower, farm, field name, field ID, and area (acres) when available in the GeoJSON properties.
- **Sidebar field list** — scrollable list of all fields with a **Zoom** button to fly to each field.
- **Auto-fit bounds** — the map initially zooms to show all fields.
- **Responsive** — sidebar collapses on narrow/mobile viewports.

## Data Sources

- Field boundaries: `growers/<grower>/farms/<farm>/fields/<field>/boundary/field_boundary.geojson`
- Field metadata: `growers/<grower>/farms/<farm>/fields/<field>/field.json`

## Keeping HTML Small

The output embeds only the vector GeoJSON coordinates and metadata. No raster imagery, no base64-encoded posters, and no external JavaScript bundles are included. Typical output size is 5–30 KB per grower.
