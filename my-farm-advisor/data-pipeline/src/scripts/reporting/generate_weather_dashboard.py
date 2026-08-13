#!/usr/bin/env python3
"""Generate an offline, self-contained Grower Field Weather Dashboard.

This script reads existing pipeline outputs (boundaries, field metadata, and
per-field weather CSVs) and produces a single HTML file with no runtime
external dependencies.

Usage:
    python generate_weather_dashboard.py --farm-dir <path>
    python generate_weather_dashboard.py --farm-dir <path> --output <path>
    python generate_weather_dashboard.py --farm-dir <path> --no-basemap
    python generate_weather_dashboard.py  # auto-discover
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPTS_DIR / "lib"))
sys.path.insert(0, str(_SCRIPTS_DIR))

from dashboard_assets import fetch_satellite_basemap, get_plotly_bundle
from farm_discovery import (
    DiscoveryError,
    discover_farm_dir,
    extract_grower_and_farm_slugs,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("weather_dashboard")

_COLOR_PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]

_GDD_BASE_C = 10.0
_MM_TO_INCH = 0.0393701
_EARTH_RADIUS = 6378137.0


def _field_color(index: int) -> str:
    return _COLOR_PALETTE[index % len(_COLOR_PALETTE)]


def _lonlat_to_mercator(lon: float, lat: float) -> tuple[float, float]:
    x = math.radians(lon) * _EARTH_RADIUS
    y = math.log(math.tan(math.pi / 4.0 + math.radians(lat) / 2.0)) * _EARTH_RADIUS
    return (x, y)


def _project_coords_to_mercator(
    coords: list | tuple,
) -> list[list[list[float]]]:
    """Convert GeoJSON Polygon or MultiPolygon coordinates to Mercator rings.

    GeoJSON Polygon coords: [outer_ring, ...] where each ring is [[x,y], ...]
    Returns: list of rings, each ring is [[mx, my], ...]
    """

    def _is_num(v):
        return isinstance(v, (int, float))

    def _project_ring(ring) -> list[list[float]]:
        result: list[list[float]] = []
        for pt in ring:
            if len(pt) >= 2 and _is_num(pt[0]) and _is_num(pt[1]):
                mx, my = _lonlat_to_mercator(float(pt[0]), float(pt[1]))
                result.append([mx, my])
        return result

    def _is_ring(candidate) -> bool:
        if not isinstance(candidate, (list, tuple)):
            return False
        if len(candidate) == 0:
            return False
        first = candidate[0]
        return isinstance(first, (list, tuple)) and len(first) >= 2 and _is_num(first[0])

    def _find_rings(items) -> list:
        if not isinstance(items, (list, tuple)):
            return []
        if len(items) == 0:
            return []
        if _is_ring(items):
            return [_project_ring(items)]
        rings: list = []
        for item in items:
            if _is_ring(item):
                rings.append(_project_ring(item))
            elif isinstance(item, (list, tuple)):
                inner = _find_rings(item)
                rings.extend(inner)
        return rings

    return _find_rings(coords)


def _load_farm_boundary(farm_dir: Path) -> gpd.GeoDataFrame:
    boundary_path = farm_dir / "boundary" / "field_boundaries.geojson"
    if not boundary_path.exists():
        raise DiscoveryError(f"Missing boundary file: {boundary_path}")
    gdf = gpd.read_file(boundary_path)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    else:
        gdf = gdf.to_crs("EPSG:4326")
    return gdf


def _load_field_metadata(field_dir: Path) -> dict[str, Any]:
    field_json = field_dir / "field.json"
    if not field_json.exists():
        return {}
    try:
        return json.loads(field_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _load_field_weather(field_dir: Path) -> pd.DataFrame:
    weather_csv = field_dir / "weather" / "daily_weather.csv"
    if not weather_csv.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(weather_csv)
        if df.empty or len(df.columns) == 0 or len(df) == 0:
            return pd.DataFrame()
        return df
    except (OSError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def _compute_last_frost_date(
    daily_df: pd.DataFrame, year: int
) -> tuple[date, int]:
    year_df = daily_df[daily_df["date"].dt.year == year].copy()
    if year_df.empty:
        jan1 = date(year, 1, 1)
        return (jan1, jan1.timetuple().tm_yday)

    cutoff = pd.Timestamp(year=year, month=7, day=1)
    before_summer = year_df[year_df["date"] < cutoff]
    if before_summer.empty:
        jan1 = date(year, 1, 1)
        return (jan1, jan1.timetuple().tm_yday)

    frosts = before_summer[before_summer["T2M_MIN"] <= 0.0]
    if frosts.empty:
        jan1 = date(year, 1, 1)
        return (jan1, jan1.timetuple().tm_yday)

    last_frost_row = frosts.loc[frosts["date"].idxmax()]
    frost_date: date = last_frost_row["date"].date()
    doy = frost_date.timetuple().tm_yday
    return (frost_date, doy)


def _process_weather_for_field(
    field_id: str, weather_df: pd.DataFrame
) -> list[dict[str, Any]]:
    if weather_df.empty or "date" not in weather_df.columns:
        return []

    weather_df = weather_df.copy()
    weather_df["date"] = pd.to_datetime(weather_df["date"], errors="coerce")
    weather_df = weather_df.dropna(subset=["date"])
    if weather_df.empty:
        return []

    required = {"T2M_MIN", "T2M_MAX", "PRECTOTCORR"}
    if not required.issubset(set(weather_df.columns)):
        return []

    for col in ["T2M_MIN", "T2M_MAX", "PRECTOTCORR"]:
        weather_df[col] = pd.to_numeric(weather_df[col], errors="coerce")
    weather_df = weather_df.dropna(subset=["T2M_MIN", "T2M_MAX", "PRECTOTCORR"])
    if weather_df.empty:
        return []

    years = sorted(weather_df["date"].dt.year.unique())
    results: list[dict[str, Any]] = []

    for year in years:
        frost_date, frost_doy = _compute_last_frost_date(weather_df, year)
        year_df = weather_df[weather_df["date"].dt.year == year].copy()
        year_df = year_df.sort_values("date").reset_index(drop=True)
        year_df = year_df[year_df["date"] >= pd.Timestamp(frost_date)]
        if year_df.empty:
            continue

        daily_records: list[dict[str, Any]] = []
        cum_gdd = 0.0
        cum_rain = 0.0
        for _, row in year_df.iterrows():
            tmin = float(row["T2M_MIN"])
            tmax = float(row["T2M_MAX"])
            precip = float(row["PRECTOTCORR"])
            daily_gdd = max((tmax + tmin) / 2.0 - _GDD_BASE_C, 0.0)
            daily_rain_in = precip * _MM_TO_INCH
            cum_gdd += daily_gdd
            cum_rain += daily_rain_in
            d: date = row["date"].date()
            daily_records.append(
                {
                    "date": d.isoformat(),
                    "dayOfYear": d.timetuple().tm_yday,
                    "dailyGdd": round(daily_gdd, 2),
                    "cumulativeGdd": round(cum_gdd, 2),
                    "dailyRainfallIn": round(daily_rain_in, 2),
                    "cumulativeRainfallIn": round(cum_rain, 2),
                }
            )

        if daily_records:
            results.append(
                {
                    "fieldId": str(field_id),
                    "year": int(year),
                    "lastFrostDate": frost_date.isoformat(),
                    "lastFrostDoy": int(frost_doy),
                    "daily": daily_records,
                }
            )

    return results


def _extract_field_data(
    farm_dir: Path, boundary_gdf: gpd.GeoDataFrame
) -> list[dict[str, Any]]:
    fields_dir = farm_dir / "fields"
    fields: list[dict[str, Any]] = []
    boundary_map: dict[str, Any] = {}

    boundary_path = farm_dir / "boundary" / "field_boundaries.geojson"
    try:
        raw_bnd = json.loads(boundary_path.read_text(encoding="utf-8"))
        if isinstance(raw_bnd, dict) and "features" in raw_bnd:
            for idx, feat in enumerate(raw_bnd["features"]):
                props = feat.get("properties", {}) if isinstance(feat, dict) else {}
                raw_fid = str(props.get("field_id", "")).strip()
                if raw_fid and idx < len(boundary_gdf):
                    boundary_map[raw_fid] = boundary_gdf.iloc[idx]
    except (OSError, json.JSONDecodeError, KeyError):
        pass

    if not boundary_map:
        for _, row in boundary_gdf.iterrows():
            fid = str(row.get("field_id", "")).strip()
            if fid:
                boundary_map[fid] = row

    if fields_dir.exists():
        field_entries = sorted(fields_dir.iterdir())
    else:
        field_entries = []

    for idx, field_path in enumerate(field_entries):
        if not field_path.is_dir():
            continue

        field_slug = field_path.name
        meta = _load_field_metadata(field_path)
        field_id = str(meta.get("field_id", field_slug))
        display_name = str(meta.get("display_name", field_id))

        row_data = None
        for key in (field_id, field_id.lower(), field_id.upper(), field_slug):
            if key in boundary_map:
                row_data = boundary_map[key]
                break
        if row_data is None:
            logger.warning(
                "No boundary geometry found for field %s; skipping map trace.", field_id
            )
            continue

        geometry = row_data.geometry
        geojson_geom = geometry.__geo_interface__
        mercator_polygons: list[list[list[float]]] = []
        geom_type = geojson_geom.get("type", "")
        coords = geojson_geom.get("coordinates", [])

        if geom_type == "Polygon":
            mercator_polygons = _project_coords_to_mercator(coords)
        elif geom_type == "MultiPolygon":
            mercator_polygons = _project_coords_to_mercator(coords)
        else:
            logger.warning(
                "Unsupported geometry type %s for field %s; skipping.",
                geom_type,
                field_id,
            )
            continue

        acres = None
        try:
            acres_val = row_data.get("area_acres")
            if acres_val is not None and not (
                isinstance(acres_val, float) and pd.isna(acres_val)
            ):
                acres = float(acres_val)
        except (TypeError, ValueError):
            pass

        weather_df = _load_field_weather(field_path)
        has_weather = not weather_df.empty and len(weather_df) > 0
        weather_by_year = _process_weather_for_field(field_id, weather_df)
        available_years = sorted({w["year"] for w in weather_by_year})

        fields.append(
            {
                "fieldId": field_id,
                "fieldName": display_name,
                "acres": acres,
                "color": _field_color(len(fields)),
                "mercatorPolygons": mercator_polygons,
                "hasWeatherData": has_weather,
                "availableYears": available_years,
                "weatherByYear": weather_by_year,
            }
        )

    return fields


def _default_year(years: list[int]) -> int | None:
    if not years:
        return None
    if 2025 in years:
        return 2025
    return max(years)


def _compute_farm_bounds_wgs84(
    fields: list[dict[str, Any]],
) -> tuple[float, float, float, float]:
    all_lons: list[float] = []
    all_lats: list[float] = []
    for f in fields:
        for ring in f["mercatorPolygons"]:
            for x, y in ring:
                lon = math.degrees(x / _EARTH_RADIUS)
                lat = math.degrees(
                    2.0 * math.atan(math.exp(y / _EARTH_RADIUS)) - math.pi / 2.0
                )
                all_lons.append(lon)
                all_lats.append(lat)
    if not all_lons:
        return (-98.0, 39.0, -90.0, 44.0)
    return (min(all_lons), min(all_lats), max(all_lons), max(all_lats))


def _compute_mercator_extent(
    fields: list[dict[str, Any]],
) -> tuple[float, float, float, float]:
    all_x: list[float] = []
    all_y: list[float] = []
    for f in fields:
        for ring in f["mercatorPolygons"]:
            for x, y in ring:
                all_x.append(x)
                all_y.append(y)
    if not all_x:
        w2 = 20037508.342789244
        return (-w2, -w2, w2, w2)
    dx = (max(all_x) - min(all_x)) * 0.2
    dy = (max(all_y) - min(all_y)) * 0.2
    return (
        min(all_x) - dx,
        min(all_y) - dy,
        max(all_x) + dx,
        max(all_y) + dy,
    )


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Grower Field Weather Dashboard &mdash; {farm_name}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #f4f5f7; color: #1e293b; line-height: 1.5;
  }}
  header {{
    background: #fff; border-bottom: 1px solid #e2e8f0;
    padding: 1rem 1.5rem;
    display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between;
  }}
  .header-left {{ display: flex; flex-direction: column; gap: 0.25rem; }}
  h1 {{ margin: 0; font-size: 1.35rem; font-weight: 700; color: #0f172a; }}
  .subtitle {{ margin: 0; font-size: 0.9rem; color: #64748b; }}
  .controls {{ display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; }}
  .dropdown-container {{ position: relative; }}
  .dropdown-btn {{
    background: #fff; border: 1px solid #cbd5e1; border-radius: 6px;
    padding: 0.4rem 0.8rem; font-size: 0.85rem; cursor: pointer;
    display: flex; align-items: center; gap: 0.4rem; min-width: 120px;
    color: #1e293b;
  }}
  .dropdown-btn:hover {{ border-color: #94a3b8; }}
  .dropdown-btn:focus {{ outline: 2px solid #2563eb; outline-offset: 1px; }}
  .dropdown-panel {{
    display: none; position: absolute; top: 100%; left: 0; margin-top: 4px;
    background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    min-width: 220px; max-height: 320px; overflow-y: auto; z-index: 100;
    padding: 0.5rem;
  }}
  .dropdown-panel.open {{ display: block; }}
  .dropdown-item {{
    display: flex; align-items: center; gap: 0.4rem;
    padding: 0.35rem 0.3rem; font-size: 0.85rem; cursor: pointer;
    border-radius: 4px; user-select: none;
  }}
  .dropdown-item:hover {{ background: #f1f5f9; }}
  .dropdown-item input[type="checkbox"] {{ cursor: pointer; accent-color: #2563eb; width: 16px; height: 16px; }}
  .dropdown-actions {{
    display: flex; gap: 0.5rem; padding: 0.3rem 0 0.5rem;
    border-bottom: 1px solid #e2e8f0; margin-bottom: 0.3rem;
  }}
  .dropdown-actions button {{
    background: none; border: none; color: #2563eb;
    font-size: 0.8rem; cursor: pointer; padding: 0.2rem 0.5rem; border-radius: 4px;
  }}
  .dropdown-actions button:hover {{ background: #eff6ff; }}
  .dropdown-actions button:focus {{ outline: 2px solid #2563eb; outline-offset: 1px; }}
  .nodata {{ color: #94a3b8; font-style: italic; margin-left: auto; font-size: 0.78rem; }}
  #reset-btn {{
    background: #0f172a; color: #fff; border: none; border-radius: 6px;
    padding: 0.4rem 1rem; font-size: 0.85rem; cursor: pointer;
  }}
  #reset-btn:hover {{ background: #334155; }}
  #reset-btn:focus {{ outline: 2px solid #2563eb; outline-offset: 1px; }}
  .summary {{ font-size: 0.85rem; color: #64748b; }}
  #main {{ display: flex; height: calc(100vh - 80px); }}
  #map-pane {{ flex: 1; min-width: 0; position: relative; }}
  #charts-pane {{ flex: 1; min-width: 0; display: flex; flex-direction: column; }}
  .chart-box {{ flex: 1; min-height: 0; position: relative; }}
  .basemap-note {{
    position: absolute; top: 8px; left: 8px;
    background: rgba(255,255,255,0.9); padding: 4px 10px; border-radius: 4px;
    font-size: 12px; color: #64748b; z-index: 10;
    border: 1px solid #e2e8f0;
  }}
  @media (max-width: 900px) {{
    #main {{ flex-direction: column; height: auto; }}
    #map-pane {{ height: 50vh; }}
    #charts-pane {{ height: auto; }}
    .chart-box {{ height: 400px; }}
    header {{ flex-direction: column; align-items: flex-start; }}
  }}
</style>
<script>
{plotly_js}
</script>
</head>
<body>
<header>
  <div class="header-left">
    <h1>Grower Field Weather Dashboard</h1>
    <div class="subtitle">{farm_name} &middot; {farm_id} &middot; Generated {generated_at}</div>
  </div>
  <div class="controls">
    <div class="dropdown-container" id="field-dropdown">
      <button class="dropdown-btn" id="field-dropdown-btn" aria-haspopup="true" aria-expanded="false">Fields &#9662;</button>
      <div class="dropdown-panel" id="field-dropdown-panel" role="menu">
        <div class="dropdown-actions">
          <button onclick="selectAllFields()">Select all</button>
          <button onclick="clearAllFields()">Clear all</button>
        </div>
        <div id="field-dropdown-items"></div>
      </div>
    </div>
    <div class="dropdown-container" id="year-dropdown">
      <button class="dropdown-btn" id="year-dropdown-btn" aria-haspopup="true" aria-expanded="false">Years &#9662;</button>
      <div class="dropdown-panel" id="year-dropdown-panel" role="menu">
        <div class="dropdown-actions">
          <button onclick="selectAllYears()">Select all</button>
          <button onclick="clearAllYears()">Clear all</button>
        </div>
        <div id="year-dropdown-items"></div>
      </div>
    </div>
    <button id="reset-btn" onclick="resetView()">Reset view</button>
    <div class="summary" id="selection-summary"></div>
  </div>
</header>
<div id="main">
  <div id="map-pane">{basemap_note}<div id="map" style="width:100%;height:100%;"></div></div>
  <div id="charts-pane">
    <div class="chart-box" id="gdd-chart"></div>
    <div class="chart-box" id="rain-chart"></div>
  </div>
</div>
<script>
(function() {{
  var DASHBOARD_DATA = {data_json};
  var ALL_FIELDS = DASHBOARD_DATA.fields;
  var WEATHER_DATA = DASHBOARD_DATA.weatherByFieldYear;
  var ALL_YEARS = [];
  WEATHER_DATA.forEach(function(w) {{
    if (ALL_YEARS.indexOf(w.year) === -1) ALL_YEARS.push(w.year);
  }});
  ALL_YEARS.sort(function(a,b){{return a-b;}});
  var DEFAULT_YEAR = {default_year_json};

  var selectedFields = ALL_FIELDS.map(function(f){{ return f.fieldId; }});
  var selectedYears = DEFAULT_YEAR !== null ? [DEFAULT_YEAR] : (ALL_YEARS.length ? [ALL_YEARS[ALL_YEARS.length-1]] : []);
  var sharedXRange = null;
  var syncingX = false;

  function setupDropdown(btnId, panelId) {{
    var btn = document.getElementById(btnId);
    var panel = document.getElementById(panelId);
    btn.addEventListener('click', function(e) {{
      e.stopPropagation();
      var wasOpen = panel.classList.contains('open');
      closeAllDropdowns();
      if (!wasOpen) panel.classList.add('open');
    }});
  }}

  function closeAllDropdowns() {{
    var panels = document.querySelectorAll('.dropdown-panel');
    panels.forEach(function(p) {{ p.classList.remove('open'); }});
  }}

  document.addEventListener('click', function() {{ closeAllDropdowns(); }});

  setupDropdown('field-dropdown-btn', 'field-dropdown-panel');
  setupDropdown('year-dropdown-btn', 'year-dropdown-panel');

  function buildFieldItems() {{
    var container = document.getElementById('field-dropdown-items');
    container.innerHTML = '';
    ALL_FIELDS.forEach(function(f) {{
      var div = document.createElement('div');
      div.className = 'dropdown-item';
      div.setAttribute('role', 'menuitemcheckbox');
      div.tabIndex = 0;
      var cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = selectedFields.indexOf(f.fieldId) !== -1;
      cb.tabIndex = -1;
      cb.onchange = function() {{
        if (cb.checked) {{
          if (selectedFields.indexOf(f.fieldId) === -1) selectedFields.push(f.fieldId);
        }} else {{
          selectedFields = selectedFields.filter(function(id){{ return id !== f.fieldId; }});
        }}
        updateAll();
      }};
      div.appendChild(cb);
      var span = document.createElement('span');
      span.textContent = f.fieldName;
      div.appendChild(span);
      if (!f.hasWeatherData) {{
        var nd = document.createElement('span');
        nd.className = 'nodata';
        nd.textContent = '(no data)';
        div.appendChild(nd);
      }}
      div.addEventListener('click', function(e) {{
        if (e.target === cb) return;
        cb.checked = !cb.checked;
        cb.onchange();
      }});
      div.addEventListener('keydown', function(e) {{
        if (e.key === ' ' || e.key === 'Enter') {{
          e.preventDefault();
          cb.checked = !cb.checked;
          cb.onchange();
        }}
      }});
      container.appendChild(div);
    }});
  }}

  function buildYearItems() {{
    var container = document.getElementById('year-dropdown-items');
    container.innerHTML = '';
    ALL_YEARS.forEach(function(y) {{
      var div = document.createElement('div');
      div.className = 'dropdown-item';
      div.setAttribute('role', 'menuitemcheckbox');
      div.tabIndex = 0;
      var cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = selectedYears.indexOf(y) !== -1;
      cb.tabIndex = -1;
      cb.onchange = function() {{
        if (cb.checked) {{
          if (selectedYears.indexOf(y) === -1) selectedYears.push(y);
        }} else {{
          selectedYears = selectedYears.filter(function(v){{ return v !== y; }});
        }}
        updateAll();
      }};
      div.appendChild(cb);
      var span = document.createElement('span');
      span.textContent = String(y);
      div.appendChild(span);
      div.addEventListener('click', function(e) {{
        if (e.target === cb) return;
        cb.checked = !cb.checked;
        cb.onchange();
      }});
      div.addEventListener('keydown', function(e) {{
        if (e.key === ' ' || e.key === 'Enter') {{
          e.preventDefault();
          cb.checked = !cb.checked;
          cb.onchange();
        }}
      }});
      container.appendChild(div);
    }});
  }}

  function getFilteredWeather() {{
    return WEATHER_DATA.filter(function(w) {{
      return selectedFields.indexOf(w.fieldId) !== -1 && selectedYears.indexOf(w.year) !== -1;
    }});
  }}

  function updateSummary() {{
    var fw = getFilteredWeather();
    var nCombos = fw.length;
    var nRecords = fw.reduce(function(s,w){{return s + w.daily.length;}}, 0);
    var text = selectedFields.length + ' field' + (selectedFields.length !== 1 ? 's' : '') +
      ', ' + selectedYears.length + ' year' + (selectedYears.length !== 1 ? 's' : '') +
      ', ' + nCombos + ' series, ' + nRecords + ' records';
    document.getElementById('selection-summary').textContent = text;
  }}

  function buildMap() {{
    var traces = [];
    ALL_FIELDS.forEach(function(f) {{
      var isSel = selectedFields.indexOf(f.fieldId) !== -1;
      f.mercatorPolygons.forEach(function(ring) {{
        var xs = ring.map(function(p){{return p[0];}});
        var ys = ring.map(function(p){{return p[1];}});
        if (xs.length && (Math.abs(xs[0]-xs[xs.length-1]) > 1e-6 || Math.abs(ys[0]-ys[ys.length-1]) > 1e-6)) {{
          xs.push(xs[0]); ys.push(ys[0]);
        }}
        traces.push({{
          x: xs, y: ys, mode: 'lines', fill: 'toself',
          line: {{color: f.color, width: isSel ? 2.5 : 1}},
          fillcolor: f.color + (isSel ? '99' : '22'),
          hoverinfo: 'text',
          text: f.fieldName + (f.acres !== null ? '<br>' + f.acres.toFixed(1) + ' ac' : ''),
          showlegend: false
        }});
      }});
    }});
    var layout = {{
      margin: {{l:0, r:0, t:0, b:0}},
      paper_bgcolor: '#eef2f6',
      plot_bgcolor: '#eef2f6',
      xaxis: {{visible: false, scaleanchor: 'y', scaleratio: 1, range: [{map_x_min},{map_x_max}]}},
      yaxis: {{visible: false, range: [{map_y_min},{map_y_max}]}},
      images: {images_js},
      dragmode: 'pan',
      showlegend: false
    }};
    var config = {{displayModeBar: false, responsive: true}};
    Plotly.newPlot('map', traces, layout, config);

    document.getElementById('map').on('plotly_click', function(data) {{
      if (!data.points || !data.points.length) return;
      var pt = data.points[0];
      var clickedField = null;
      for (var i = 0; i < ALL_FIELDS.length; i++) {{
        var f = ALL_FIELDS[i];
        for (var r = 0; r < f.mercatorPolygons.length; r++) {{
          var ring = f.mercatorPolygons[r];
          if (pointInPolygon(pt.x, pt.y, ring)) {{
            clickedField = f.fieldId;
            break;
          }}
        }}
        if (clickedField) break;
      }}
      if (!clickedField) return;
      var idx = selectedFields.indexOf(clickedField);
      if (idx !== -1) selectedFields.splice(idx, 1);
      else selectedFields.push(clickedField);
      updateAll();
    }});
  }}

  function pointInPolygon(x, y, ring) {{
    var inside = false;
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {{
      var xi = ring[i][0], yi = ring[i][1];
      var xj = ring[j][0], yj = ring[j][1];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) {{
        inside = !inside;
      }}
    }}
    return inside;
  }}

  function fitMapToSelection() {{
    if (selectedFields.length === 0) return;
    var xs = [], ys = [];
    ALL_FIELDS.forEach(function(f) {{
      if (selectedFields.indexOf(f.fieldId) === -1) return;
      f.mercatorPolygons.forEach(function(ring) {{
        ring.forEach(function(p){{xs.push(p[0]); ys.push(p[1]);}});
      }});
    }});
    if (!xs.length) return;
    var minx = Math.min.apply(null, xs), maxx = Math.max.apply(null, xs);
    var miny = Math.min.apply(null, ys), maxy = Math.max.apply(null, ys);
    var dx = (maxx - minx) * 0.2, dy = (maxy - miny) * 0.2;
    Plotly.relayout('map', {{'xaxis.range': [minx-dx, maxx+dx], 'yaxis.range': [miny-dy, maxy+dy]}});
  }}

  function buildGddChart() {{
    var fw = getFilteredWeather();
    var traces = [];
    var shapes = [];
    fw.forEach(function(w) {{
      var f = ALL_FIELDS.find(function(fld){{return fld.fieldId === w.fieldId;}});
      if (!f) return;
      var xs = w.daily.map(function(d){{return d.dayOfYear;}});
      var ys = w.daily.map(function(d){{return d.cumulativeGdd;}});
      var cd = w.daily.map(function(d){{return [d.date, d.dayOfYear, d.cumulativeGdd];}});
      traces.push({{
        x: xs, y: ys, mode: 'lines',
        line: {{color: f.color, width: 2}},
        name: f.fieldName + ' ' + w.year,
        customdata: cd,
        hovertemplate: '<b>%{{fullData.name}}</b><br>Date: %{{customdata[0]}}<br>DOY: %{{customdata[1]}}<br>Cumulative GDD: %{{y:.1f}}<extra></extra>'
      }});
      shapes.push({{
        type: 'line', x0: w.lastFrostDoy, x1: w.lastFrostDoy,
        y0: 0, y1: 1, yref: 'paper',
        line: {{color: f.color, width: 1, dash: 'dot'}},
        opacity: 0.6
      }});
    }});
    var layout = {{
      title: {{text: 'Growing Degree Days', font: {{size: 14, color: '#1e293b'}}}},
      margin: {{l: 60, r: 20, t: 40, b: 50}},
      paper_bgcolor: '#fff', plot_bgcolor: '#fff',
      xaxis: {{title: 'Day of Year', dtick: 30, range: [80, 320], color: '#1e293b'}},
      yaxis: {{title: 'Cumulative GDD (base 10' + String.fromCharCode(176) + 'C)', color: '#1e293b'}},
      shapes: shapes,
      legend: {{orientation: 'h', y: 1.15, x: 1, xanchor: 'right', font: {{size: 11}}}},
      hovermode: 'closest'
    }};
    if (sharedXRange) layout.xaxis.range = sharedXRange;
    if (traces.length === 0) {{
      layout.annotations = [{{
        text: 'No data for selected fields/years', showarrow: false,
        xref: 'paper', yref: 'paper', x: 0.5, y: 0.5,
        font: {{size: 14, color: '#94a3b8'}}
      }}];
    }}
    var config = {{displayModeBar: false, responsive: true}};
    Plotly.newPlot('gdd-chart', traces, layout, config);
    document.getElementById('gdd-chart').on('plotly_relayout', function(evt) {{
      if (syncingX) return;
      if (evt['xaxis.range[0]'] !== undefined && evt['xaxis.range[1]'] !== undefined) {{
        var rng = [evt['xaxis.range[0]'], evt['xaxis.range[1]']];
        sharedXRange = rng;
        syncingX = true;
        Plotly.relayout('rain-chart', {{'xaxis.range': rng}});
        syncingX = false;
      }}
    }});
  }}

  function buildRainChart() {{
    var fw = getFilteredWeather();
    var barTraces = [], lineTraces = [], shapes = [];
    fw.forEach(function(w) {{
      var f = ALL_FIELDS.find(function(fld){{return fld.fieldId === w.fieldId;}});
      if (!f) return;
      var xs = w.daily.map(function(d){{return d.dayOfYear;}});
      var dailyRain = w.daily.map(function(d){{return d.dailyRainfallIn;}});
      var cumRain = w.daily.map(function(d){{return d.cumulativeRainfallIn;}});
      var cd = w.daily.map(function(d){{return [d.date, d.dayOfYear, d.dailyRainfallIn, d.cumulativeRainfallIn];}});
      barTraces.push({{
        x: xs, y: dailyRain, type: 'bar',
        marker: {{color: f.color, opacity: 0.25}},
        name: f.fieldName + ' ' + w.year + ' daily',
        customdata: cd,
        hovertemplate: '<b>%{{fullData.name}}</b><br>Date: %{{customdata[0]}}<br>DOY: %{{customdata[1]}}<br>Daily rain: %{{customdata[2]:.2f}} in<extra></extra>',
        yaxis: 'y', showlegend: false
      }});
      lineTraces.push({{
        x: xs, y: cumRain, mode: 'lines',
        line: {{color: f.color, width: 2}},
        name: f.fieldName + ' ' + w.year + ' cumulative',
        customdata: cd,
        hovertemplate: '<b>%{{fullData.name}}</b><br>Date: %{{customdata[0]}}<br>DOY: %{{customdata[1]}}<br>Cumulative rain: %{{customdata[3]:.2f}} in<extra></extra>',
        yaxis: 'y2', showlegend: true
      }});
      shapes.push({{
        type: 'line', x0: w.lastFrostDoy, x1: w.lastFrostDoy,
        y0: 0, y1: 1, yref: 'paper',
        line: {{color: f.color, width: 1, dash: 'dot'}},
        opacity: 0.6
      }});
    }});
    var layout = {{
      title: {{text: 'Rainfall', font: {{size: 14, color: '#1e293b'}}}},
      margin: {{l: 60, r: 60, t: 40, b: 50}},
      paper_bgcolor: '#fff', plot_bgcolor: '#fff',
      xaxis: {{title: 'Day of Year', dtick: 30, range: [80, 320], color: '#1e293b'}},
      yaxis: {{title: 'Daily rainfall (in)', side: 'left', color: '#1e293b'}},
      yaxis2: {{title: 'Cumulative rainfall (in)', overlaying: 'y', side: 'right', color: '#1e293b'}},
      shapes: shapes,
      legend: {{orientation: 'h', y: 1.15, x: 1, xanchor: 'right', font: {{size: 11}}}},
      hovermode: 'closest', barmode: 'group'
    }};
    if (sharedXRange) layout.xaxis.range = sharedXRange;
    var allTraces = barTraces.concat(lineTraces);
    if (allTraces.length === 0) {{
      layout.annotations = [{{
        text: 'No data for selected fields/years', showarrow: false,
        xref: 'paper', yref: 'paper', x: 0.5, y: 0.5,
        font: {{size: 14, color: '#94a3b8'}}
      }}];
    }}
    var config = {{displayModeBar: false, responsive: true}};
    Plotly.newPlot('rain-chart', allTraces, layout, config);
    document.getElementById('rain-chart').on('plotly_relayout', function(evt) {{
      if (syncingX) return;
      if (evt['xaxis.range[0]'] !== undefined && evt['xaxis.range[1]'] !== undefined) {{
        var rng = [evt['xaxis.range[0]'], evt['xaxis.range[1]']];
        sharedXRange = rng;
        syncingX = true;
        Plotly.relayout('gdd-chart', {{'xaxis.range': rng}});
        syncingX = false;
      }}
    }});
  }}

  function updateAll() {{
    buildFieldItems();
    buildYearItems();
    buildMap();
    fitMapToSelection();
    buildGddChart();
    buildRainChart();
    updateSummary();
  }}

  function selectAllFields() {{
    selectedFields = ALL_FIELDS.map(function(f){{return f.fieldId;}});
    updateAll();
  }}
  function clearAllFields() {{
    selectedFields = [];
    updateAll();
  }}
  function selectAllYears() {{
    selectedYears = ALL_YEARS.slice();
    updateAll();
  }}
  function clearAllYears() {{
    selectedYears = [];
    updateAll();
  }}

  function resetView() {{
    selectedFields = ALL_FIELDS.map(function(f){{return f.fieldId;}});
    selectedYears = DEFAULT_YEAR !== null ? [DEFAULT_YEAR] : (ALL_YEARS.length ? [ALL_YEARS[ALL_YEARS.length-1]] : []);
    sharedXRange = null;
    updateAll();
  }}

  updateAll();
}})();
</script>
</body>
</html>
"""


def _build_dashboard_html(
    *,
    farm_id: str,
    farm_name: str,
    generated_at: str,
    basemap_available: bool,
    basemap_b64: str | None,
    basemap_bounds: tuple[float, float, float, float] | None,
    fields: list[dict[str, Any]],
    plotly_js: str,
) -> str:
    weather_by_field_year: list[dict[str, Any]] = []
    field_metadata: list[dict[str, Any]] = []

    for f in fields:
        fm = {
            "fieldId": f["fieldId"],
            "fieldName": f["fieldName"],
            "acres": f["acres"],
            "color": f["color"],
            "mercatorPolygons": f["mercatorPolygons"],
            "hasWeatherData": f["hasWeatherData"],
            "availableYears": f["availableYears"],
        }
        field_metadata.append(fm)
        for wby in f["weatherByYear"]:
            weather_by_field_year.append(wby)

    all_years = sorted({w["year"] for w in weather_by_field_year})
    default_year = _default_year(all_years)

    data_model = {
        "farm": {
            "farmId": farm_id,
            "farmName": farm_name,
            "generatedAt": generated_at,
            "basemapAvailable": basemap_available,
        },
        "fields": field_metadata,
        "weatherByFieldYear": weather_by_field_year,
    }

    data_json = json.dumps(data_model, indent=2, ensure_ascii=False)

    map_x_min, map_x_max, map_y_min, map_y_max = _compute_mercator_extent(fields)

    images_js = "[]"
    if basemap_available and basemap_b64 and basemap_bounds:
        bminx, bminy, bmaxx, bmaxy = basemap_bounds
        images_js = json.dumps(
            [
                {
                    "source": f"data:image/png;base64,{basemap_b64}",
                    "xref": "x",
                    "yref": "y",
                    "x": bminx,
                    "y": bmaxy,
                    "sizex": bmaxx - bminx,
                    "sizey": bmaxy - bminy,
                    "sizing": "stretch",
                    "layer": "below",
                    "opacity": 1.0,
                }
            ]
        )

    basemap_note = ""
    if not basemap_available:
        basemap_note = '<div class="basemap-note">Satellite imagery unavailable &mdash; using neutral background</div>'

    return _HTML_TEMPLATE.format(
        farm_name=farm_name,
        farm_id=farm_id,
        generated_at=generated_at,
        data_json=data_json,
        default_year_json=json.dumps(default_year),
        map_x_min=map_x_min,
        map_x_max=map_x_max,
        map_y_min=map_y_min,
        map_y_max=map_y_max,
        images_js=images_js,
        basemap_note=basemap_note,
        plotly_js=plotly_js,
    )


def generate_dashboard(
    farm_dir: Path,
    output_path: Path,
    *,
    farm_name: str | None = None,
    no_basemap: bool = False,
    allow_downloads: bool = True,
) -> Path:
    """Generate the weather dashboard HTML for a farm directory.

    Args:
        farm_dir: Path to the farm output directory.
        output_path: Where to write the HTML file.
        farm_name: Override for the farm display name.
        no_basemap: Skip satellite basemap acquisition.
        allow_downloads: Allow build-time downloads of Plotly.js.

    Returns:
        Path to the generated HTML file.

    Raises:
        DiscoveryError: If the farm directory is invalid or missing required data.
    """
    logger.info("Generating dashboard for farm: %s", farm_dir)
    farm_dir = farm_dir.resolve(strict=False)

    if not farm_dir.exists():
        raise DiscoveryError(f"Farm directory does not exist: {farm_dir}")

    grower_slug, farm_slug = extract_grower_and_farm_slugs(farm_dir)
    farm_id = farm_slug
    display_name = farm_name or farm_slug.replace("-", " ").title()

    boundary_gdf = _load_farm_boundary(farm_dir)
    logger.info("Loaded %d field boundaries", len(boundary_gdf))

    fields = _extract_field_data(farm_dir, boundary_gdf)
    logger.info("Processed %d fields", len(fields))

    n_weather_records = sum(
        len(w["daily"]) for f in fields for w in f["weatherByYear"]
    )
    n_field_years = sum(len(f["weatherByYear"]) for f in fields)
    n_no_data = sum(1 for f in fields if not f["hasWeatherData"])

    logger.info(
        "Weather records: %d across %d field-year combinations",
        n_weather_records,
        n_field_years,
    )
    if n_no_data:
        logger.info("Fields with no weather data: %d", n_no_data)

    basemap_available = False
    basemap_b64: str | None = None
    basemap_bounds: tuple[float, float, float, float] | None = None

    if not no_basemap:
        bounds_wgs84 = _compute_farm_bounds_wgs84(fields)
        logger.info("Fetching satellite basemap...")
        try:
            result = fetch_satellite_basemap(bounds_wgs84)
            if result:
                basemap_b64, basemap_bounds = result
                basemap_available = True
                logger.info("Basemap acquired (%d chars)", len(basemap_b64))
            else:
                logger.warning("Basemap fetch returned None; using neutral background")
        except Exception as exc:
            logger.warning("Basemap fetch failed: %s; using neutral background", exc)
    else:
        logger.info("Basemap disabled by --no-basemap")

    logger.info("Loading Plotly.js bundle...")
    plotly_js = get_plotly_bundle(allow_download=allow_downloads)
    logger.info("Plotly.js bundle loaded (%d chars)", len(plotly_js))

    generated_at = datetime.now().isoformat(timespec="seconds")

    html = _build_dashboard_html(
        farm_id=farm_id,
        farm_name=display_name,
        generated_at=generated_at,
        basemap_available=basemap_available,
        basemap_b64=basemap_b64,
        basemap_bounds=basemap_bounds,
        fields=fields,
        plotly_js=plotly_js,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        suffix=".html", prefix="dashboard_", dir=str(output_path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(html)
        os.replace(tmp_name, str(output_path))
    except Exception:
        try:
            Path(tmp_name).unlink(missing_ok=True)
        except Exception:
            pass
        raise

    size_kb = output_path.stat().st_size / 1024
    logger.info("Dashboard saved: %s (%.0f KB)", output_path, size_kb)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an offline Grower Field Weather Dashboard"
    )
    parser.add_argument(
        "--farm-dir",
        default=None,
        help="Path to farm output directory",
    )
    parser.add_argument(
        "--growers-dir",
        default=None,
        help="Path to growers root directory",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Explicit output HTML path (default: <farm-dir>/<farm-slug>_dashboard.html)",
    )
    parser.add_argument(
        "--no-basemap",
        action="store_true",
        help="Skip satellite basemap acquisition; use a neutral background instead",
    )
    parser.add_argument(
        "--no-downloads",
        action="store_true",
        help="Disallow build-time asset downloads (Plotly.js bundle must be pre-cached)",
    )
    parser.add_argument(
        "--farm-name",
        default=None,
        help="Override farm display name in the dashboard header",
    )
    args = parser.parse_args()

    effective_farm_dir = args.farm_dir or os.environ.get("AG_DASHBOARD_FARM_DIR")
    farm_dir = discover_farm_dir(
        farm_dir=effective_farm_dir, growers_dir=args.growers_dir
    )
    logger.info("Resolved farm directory: %s", farm_dir)

    grower_slug, farm_slug = extract_grower_and_farm_slugs(farm_dir)
    logger.info("Grower: %s, Farm: %s", grower_slug, farm_slug)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    elif os.environ.get("AG_DASHBOARD_OUTPUT"):
        output_path = Path(os.environ["AG_DASHBOARD_OUTPUT"]).expanduser().resolve()
    else:
        output_path = farm_dir / f"{farm_slug}_dashboard.html"

    generate_dashboard(
        farm_dir=farm_dir,
        output_path=output_path,
        farm_name=args.farm_name,
        no_basemap=args.no_basemap or os.environ.get("AG_NO_BASEMAP") == "1",
        allow_downloads=not args.no_downloads,
    )


if __name__ == "__main__":
    main()
