# AI Usage Documentation

## Tools Used

| Tool | Purpose |
|------|---------|
| **opencode** (Claude-based AI coding assistant) | Code generation, planning, documentation authoring, and repository exploration |
| **Plotly.js** (JavaScript charting library, v2.27.0) | Interactive dashboard visualisations (not AI-generated; used as a standard library) |

## Purpose of AI Assistance

AI assistance was used throughout this project for the following tasks:

1. **Planning and design** — The `final_dashboard_plan.md` was authored collaboratively, with AI proposing the dashboard architecture, component inventory, data model, and implementation roadmap. The instructor's six-step framework was used as the controlling specification.

2. **Repository exploration** — AI agents conducted thorough searches of the existing codebase to understand the pipeline conventions, path structures, data schemas, and available datasets from Assignments 1-3.

3. **Code module creation** — The following modules were generated with AI assistance:
   - `lib/dashboard_config.py` — Shared configuration constants
   - `lib/dashboard_data.py` — Reusable data-loading and validation functions
   - `lib/dashboard_kpis.py` — KPI computation from summary CSVs
   - `lib/dashboard_plots.py` — Plotly figure builders
   - `lib/dashboard_layout.py` — HTML/CSS/JS dashboard template
   - `scripts/reporting/prepare_dashboard_data.py` — Phase A data preparation orchestrator
   - `scripts/reporting/generate_final_dashboard.py` — Phase B dashboard generation orchestrator

4. **Documentation authoring** — `DASHBOARD_INFO.md`, `AI_USAGE.md`, `final_dashboard_plan.md`, and README updates were drafted with AI assistance.

5. **Verification and testing** — AI generated synthetic test data and ran end-to-end validation of the dashboard generation pipeline.

## Human Verification Steps

All AI-generated code and documentation underwent the following verification:

| Step | Description | Outcome |
|------|-------------|---------|
| **Import verification** | All Python modules were imported and tested in the project environment | Pass — all modules resolve without import errors |
| **Path audit** | Data paths were verified against the existing `lib/paths.py` conventions and `eda_assignment2.py` hard-coded path patterns | Pass — all path constructions match the pipeline runtime conventions |
| **Schema audit** | CSV column names were verified against the pipeline source code (`lib/nasa_power.py`, `cdl_reporting.py`, `paths.py`) | Pass — all column references match the canonical schemas |
| **Empty-data resilience** | Every Plotly figure builder was tested with empty DataFrames to ensure graceful fallback | Pass — all 11 figures produce sensible placeholders with no data |
| **End-to-end test** | Synthetic summary CSV data was created and the full `generate_final_dashboard.py` pipeline was executed | Pass — 3.7 MB HTML dashboard generated with all 6 tabs, 11 figures, 8 stat cards |
| **Repository validation** | `./scripts/validate.sh` was run after every batch of changes | Pass — 44 pass, 0 warn, 0 fail throughout |
| **No existing file modification** | Git was checked to ensure only new files were created; no existing pipeline code was altered | Pass — zero modifications to tracked files |
| **Plan compliance** | The final dashboard was verified against all six instructor requirements (exploratory visuals, geospatial map, weather visualisation, soil metric, KPI section, interpretation) | Pass — all six requirements met |

## AI-Generated Content Audit

| File | Lines | AI Involvement | Verification |
|------|-------|---------------|--------------|
| `dashboard_config.py` | 117 | Fully generated | Import test, constant audit |
| `dashboard_data.py` | 443 | Fully generated | Path audit, schema audit, import test |
| `dashboard_kpis.py` | 188 | Fully generated | Integration test with synthetic data |
| `dashboard_plots.py` | 383 | Fully generated | Empty-data test, synthetic data test |
| `dashboard_layout.py` | 231 | Fully generated | HTML structure validation, JS syntax check |
| `prepare_dashboard_data.py` | 130 | Fully generated | Error-path test, import test |
| `generate_final_dashboard.py` | 215 | Fully generated | End-to-end smoke test with synthetic data |
| `final_dashboard_plan.md` | ~800 | Collaborative | Instructor requirement verification |
| `DASHBOARD_INFO.md` | ~200 | Fully generated | Content review |
| `AI_USAGE.md` | ~100 | Fully generated | Self-documenting |
| README update | ~40 | Fully generated | Command syntax verification |

## Known Limitations of AI-Generated Code

1. **Plotly.js bundle download** — The `generate_final_dashboard.py` script downloads Plotly.js directly via HTTP rather than using the existing `lib/dashboard_assets.py` module. This was a deliberate choice to avoid the runtime dependency chain (`paths.py` requires `DATA_PIPELINE_DATA_ROOT`). Both modules download from the same CDN URL and use identical caching patterns.

2. **GDD chart requires runtime** — The cumulative GDD chart reads per-field daily weather CSV from the pipeline runtime, which is not available when running from synthetic summary CSVs alone. The chart gracefully shows a placeholder in that scenario. This is documented in the dashboard's NDVI coverage note.

3. **Field map uses centroids** — The interactive field map renders field centroids as markers rather than full polygon outlines. This was chosen for simplicity with Plotly scattermapbox. The existing `generate_grower_web_map.py` provides full-polygon rendering via Leaflet and can be integrated in a future iteration.

4. **Grower checkboxes are informational** — The header grower filter checkboxes do not yet implement cross-filtering across dashboard tabs. They are included in the UI for future implementation. All data is shown for all three growers by default.
