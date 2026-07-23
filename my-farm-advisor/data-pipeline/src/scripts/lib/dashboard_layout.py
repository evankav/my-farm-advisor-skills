"""Dashboard HTML layout generator.

Produces a single self-contained HTML document with six tabs, embedded
Plotly figures, KPI stat cards, and interactive controls.  No CDN
dependencies — Plotly.js must be supplied as a pre-fetched bundle string.
"""

from __future__ import annotations

import json
from typing import Any

from lib.dashboard_config import GROWER_COLORS, GROWER_ORDER


def _escape_json(obj: Any) -> str:
    return json.dumps(obj, default=str)


def _grower_kpi_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p><i>No grower data available.</i></p>"

    headers = ["Grower", "Fields", "Median ac", "Total ac", "Wx Fields", "Dominant Crop", "Mean Temp", "pH", "OM%"]
    header_html = "".join(f"<th>{h}</th>" for h in headers)

    body_rows: list[str] = []
    for r in rows:
        color = r.get("color", "#999")
        cells = [
            f'<td><span class="swatch" style="background:{color}"></span> {r["grower"]}</td>',
            f"<td>{r['total_fields']}</td>",
            f"<td>{r['median_acres'] or '—'}</td>",
            f"<td>{r['total_acres'] or '—'}</td>",
            f"<td>{r['weather_fields']} / {r['total_fields']}</td>",
            f"<td>{r['dominant_crop'] or '—'}</td>",
            f"<td>{r['mean_temp_c'] or '—'}°C</td>",
            f"<td>{r['avg_ph'] or '—'}</td>",
            f"<td>{r['avg_om_pct'] or '—'}</td>",
        ]
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    return f"""
    <div class="kpi-table-wrapper">
      <table class="kpi-table">
        <thead><tr>{header_html}</tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
    </div>
    """


def _stat_cards(kpis: dict[str, Any]) -> str:
    cards = [
        ("Growers", kpis.get("grower_count", 0)),
        ("Total Fields", kpis.get("total_fields", 0)),
        ("Total Acres", f"{kpis.get('total_acres', 0):,.0f}"),
        ("Crop Types", kpis.get("crop_count", 0)),
        ("Years", kpis.get("years_covered", "")),
        ("Weather Fields", kpis.get("weather_field_count", 0)),
        ("NDVI Fields", kpis.get("ndvi_field_count", 0)),
        ("Soil Fields", kpis.get("soil_field_count", 0)),
    ]
    html_parts = []
    for label, value in cards:
        html_parts.append(
            f'<div class="stat-card"><div class="stat-number">{value}</div><div class="stat-label">{label}</div></div>'
        )
    return f'<div class="stat-cards">{"".join(html_parts)}</div>'


def build_dashboard_html(
    *,
    figures_json: dict[str, str],
    overview_kpis: dict[str, Any],
    grower_table: list[dict[str, Any]],
    plotly_bundle: str,
    ndvi_coverage_note: str = "",
) -> str:
    figures_js = ",\n    ".join(
        f'"{key}": {val}' for key, val in figures_json.items()
    )
    figures_js_block = f"const FIGURES = {{\n    {figures_js}\n}};"

    grower_colors_js = _escape_json(GROWER_COLORS)
    grower_order_js = _escape_json(GROWER_ORDER)

    stat_html = _stat_cards(overview_kpis)
    kpi_table_html = _grower_kpi_table(grower_table)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Integrated Field Intelligence Dashboard</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f1f5f9; color: #1e293b; }}
  .dashboard-header {{
    background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
    color: #fff; padding: 1.2rem 2rem;
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;
  }}
  .dashboard-header h1 {{ margin: 0; font-size: 1.4rem; font-weight: 600; }}
  .grower-filters {{ display: flex; gap: 0.6rem; }}
  .grower-filters label {{
    display: flex; align-items: center; gap: 0.35rem;
    background: rgba(255,255,255,0.15); padding: 0.35rem 0.8rem; border-radius: 6px;
    cursor: pointer; font-size: 0.85rem; user-select: none;
  }}
  .grower-filters label input {{ accent-color: #fff; }}
  .tab-nav {{
    display: flex; background: #fff; border-bottom: 2px solid #e2e8f0;
    padding: 0 1rem; overflow-x: auto;
  }}
  .tab-btn {{
    background: none; border: none; padding: 0.8rem 1.3rem;
    font-size: 0.9rem; font-weight: 500; cursor: pointer;
    color: #64748b; border-bottom: 3px solid transparent;
    margin-bottom: -2px; transition: color 0.15s, border-color 0.15s;
    white-space: nowrap;
  }}
  .tab-btn:hover {{ color: #1e3a5f; }}
  .tab-btn.active {{ color: #2563eb; border-bottom-color: #2563eb; }}
  .tab-content {{ display: none; padding: 1.5rem; max-width: 1400px; margin: 0 auto; }}
  .tab-content.active {{ display: block; }}
  .stat-cards {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.8rem; margin-bottom: 1.5rem;
  }}
  .stat-card {{
    background: #fff; border-radius: 10px; padding: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08); text-align: center;
  }}
  .stat-number {{ font-size: 1.6rem; font-weight: 700; color: #1e3a5f; }}
  .stat-label {{ font-size: 0.75rem; color: #64748b; margin-top: 0.2rem; text-transform: uppercase; letter-spacing: 0.5px; }}
  .kpi-table-wrapper {{ overflow-x: auto; margin-bottom: 1.5rem; }}
  .kpi-table {{
    width: 100%; border-collapse: collapse; background: #fff;
    border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    font-size: 0.85rem;
  }}
  .kpi-table th {{
    background: #f8fafc; padding: 0.6rem 0.8rem; text-align: left;
    font-weight: 600; color: #475569; border-bottom: 2px solid #e2e8f0;
  }}
  .kpi-table td {{ padding: 0.55rem 0.8rem; border-bottom: 1px solid #f1f5f9; }}
  .kpi-table tr:hover td {{ background: #f8fafc; }}
  .swatch {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; }}
  .plot-container {{ margin-bottom: 1.5rem; background: #fff; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); overflow: hidden; }}
  .chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
  .chart-grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1.5rem; }}
  @media (max-width: 900px) {{
    .chart-grid, .chart-grid-3 {{ grid-template-columns: 1fr; }}
    .tab-btn {{ padding: 0.6rem 0.8rem; font-size: 0.8rem; }}
  }}
  .interpretation {{ background: #fff; border-radius: 10px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); line-height: 1.7; }}
  .interpretation h3 {{ margin-top: 0; color: #1e3a5f; }}
  .interpretation ul {{ padding-left: 1.2rem; }}
  .interpretation li {{ margin-bottom: 0.5rem; }}
  .limitations {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 1rem 1.5rem; border-radius: 6px; margin-top: 1.5rem; }}
  .limitations h4 {{ margin-top: 0; color: #92400e; }}
  .coverage-note {{
    background: #dbeafe; border-left: 4px solid #2563eb;
    padding: 0.6rem 1rem; border-radius: 6px; margin: 0.5rem 0 1rem;
    font-size: 0.85rem; color: #1e40af;
  }}
  .section-title {{ font-size: 1.1rem; font-weight: 600; color: #1e3a5f; margin: 0 0 1rem; }}
</style>
</head>
<body>

<div class="dashboard-header">
  <h1>Integrated Field Intelligence Dashboard<br><span style="font-size:0.8rem;font-weight:400;opacity:0.8">Illinois &middot; Iowa &middot; Nebraska Grower Comparison</span></h1>
  <div class="grower-filters">
    <label><input type="checkbox" class="grower-cb" data-grower="Illinois" checked> Illinois</label>
    <label><input type="checkbox" class="grower-cb" data-grower="Iowa" checked> Iowa</label>
    <label><input type="checkbox" class="grower-cb" data-grower="Nebraska" checked> Nebraska</label>
  </div>
</div>

<div class="tab-nav">
  <button class="tab-btn active" data-tab="overview">Overview</button>
  <button class="tab-btn" data-tab="locations">Field Locations</button>
  <button class="tab-btn" data-tab="weather">Weather</button>
  <button class="tab-btn" data-tab="crops">Crop Distribution</button>
  <button class="tab-btn" data-tab="health">Vegetation Health</button>
  <button class="tab-btn" data-tab="interpretation">Interpretation</button>
</div>

<!-- ── Tab: Overview ── -->
<div class="tab-content active" id="tab-overview">
  {stat_html}
  <div class="section-title">Grower Comparison</div>
  {kpi_table_html}
  <div class="chart-grid">
    <div class="plot-container" id="plot-field-size"></div>
    <div class="plot-container" id="plot-compactness"></div>
  </div>
  <div class="plot-container" id="plot-soil-drainage"></div>
</div>

<!-- ── Tab: Field Locations ── -->
<div class="tab-content" id="tab-locations">
  <div class="section-title">Field Map — All 30 Fields</div>
  <div class="plot-container" id="plot-field-map" style="min-height:500px"></div>
  <p style="font-size:0.8rem;color:#64748b;">Marker size = field acreage. Click markers for field details. Basemap &copy; OpenStreetMap contributors.</p>
</div>

<!-- ── Tab: Weather ── -->
<div class="tab-content" id="tab-weather">
  <div class="chart-grid">
    <div class="plot-container" id="plot-temperature"></div>
    <div class="plot-container" id="plot-precipitation"></div>
  </div>
  <div class="plot-container" id="plot-climate-space"></div>
</div>

<!-- ── Tab: Crop Distribution ── -->
<div class="tab-content" id="tab-crops">
  <div class="chart-grid">
    <div class="plot-container" id="plot-crop-composition"></div>
    <div class="plot-container" id="plot-rotation"></div>
  </div>
</div>

<!-- ── Tab: Vegetation Health ── -->
<div class="tab-content" id="tab-health">
  {f'<div class="coverage-note">{ndvi_coverage_note}</div>' if ndvi_coverage_note else ''}
  <div class="chart-grid">
    <div class="plot-container" id="plot-ndvi"></div>
    <div class="plot-container" id="plot-gdd"></div>
  </div>
</div>

<!-- ── Tab: Interpretation ── -->
<div class="tab-content" id="tab-interpretation">
  <div class="interpretation">
    <h3>Key Observations</h3>
    <ul>
      <li><strong>Field scale:</strong> Iowa fields are the largest (median ~118 ac, max 307 ac), consistent with the flat glacial till plains of the prairie pothole region. Nebraska fields cluster around ~30 ac, reflecting center-pivot irrigation circle sizes. Illinois has the widest spread including very small fields.</li>
      <li><strong>Field shape:</strong> Nebraska fields are distinctly more compact (lowest perimeter/area ratio), consistent with circular center-pivot irrigation. Illinois and Iowa fields have higher ratios, reflecting irregular rectilinear boundaries typical of rain-fed row-crop agriculture.</li>
      <li><strong>Crop mix:</strong> All three growers are corn-soybean dominant (>85% of pixels). Each state has a distinctive third crop: alfalfa in Iowa, winter wheat in Nebraska, forest patches in Illinois.</li>
      <li><strong>Rotations:</strong> Corn-soybean alternation dominates all three states. Iowa shows evidence of continuous corn (~25% corn-to-corn transitions). Nebraska shows weak fallow persistence.</li>
      <li><strong>Climate gradient:</strong> Illinois is cool-wet (highest precipitation, moderate temperatures). Nebraska is warm-dry (lowest precipitation, highest temperatures). Iowa is coldest with moderate precipitation. Growing season (months above 10°C) is shortest in Iowa, longest in Nebraska.</li>
      <li><strong>Soil drainage:</strong> Drainage class distributions reflect underlying parent materials. Iowa fields on the Des Moines Lobe tend toward somewhat poorly drained soils requiring tile drainage, while Nebraska loess uplands are predominantly well-drained.</li>
    </ul>

    <div class="limitations">
      <h4>Limitations and Coverage</h4>
      <ul>
        <li><strong>Weather:</strong> Illinois and Iowa have weather data for 3 of 10 fields each vs. 10 of 10 for Nebraska. Temperature and precipitation comparisons should be interpreted with this asymmetry in mind.</li>
        <li><strong>NDVI:</strong> Only one field-year is confirmed (osm-1499474531, IL, Soybeans 2025). The NDVI chart is not a cross-grower comparison.</li>
        <li><strong>Field boundaries:</strong> Sourced from OpenStreetMap (volunteer-contributed), not surveyed property lines.</li>
        <li><strong>CDL:</strong> 30 m satellite-derived crop classification, not ground-truthed at the field level.</li>
        <li><strong>Soil (SSURGO):</strong> Map unit scale (1:12,000 to 1:24,000). Drainage class is assigned per map unit component, not measured per field. Top 30 cm only.</li>
        <li><strong>Time window:</strong> 5 years (2021-2025) is informative but does not represent climate norms.</li>
        <li><strong>Causality:</strong> All conclusions are observational comparisons. The data does not support causal claims about why differences exist.</li>
      </ul>
    </div>
  </div>
</div>

<script>
{plotly_bundle}
</script>

<script>
{figures_js_block}

const GROWER_COLORS = {grower_colors_js};
const GROWER_ORDER = {grower_order_js};

const PLOT_IDS = [
  'field-size', 'compactness', 'soil-drainage',
  'field-map', 'temperature', 'precipitation',
  'climate-space', 'crop-composition', 'rotation',
  'ndvi', 'gdd'
];

function renderPlot(id) {{
  const el = document.getElementById('plot-' + id);
  if (!el) return;
  const fig = FIGURES[id];
  if (!fig) {{
    el.innerHTML = '<p style="padding:2rem;text-align:center;color:#888;"><i>Chart not available.</i></p>';
    return;
  }}
  const layout = JSON.parse(JSON.stringify(fig.layout || {{}}));
  layout.autosize = true;
  layout.margin = layout.margin || {{l: 20, r: 20, t: 50, b: 20}};
  const config = {{
    responsive: true,
    displayModeBar: true,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
    displaylogo: false,
  }};
  Plotly.newPlot(el, fig.data, layout, config);
}}

function renderAllPlots() {{
  PLOT_IDS.forEach(renderPlot);
}}

document.addEventListener('DOMContentLoaded', function() {{
  renderAllPlots();

  // Tab switching
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabBtns.forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      const tabId = this.getAttribute('data-tab');
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      this.classList.add('active');
      const target = document.getElementById('tab-' + tabId);
      if (target) target.classList.add('active');
    }});
  }});

  // Grower filter (currently informational)
  const growerCbs = document.querySelectorAll('.grower-cb');
  growerCbs.forEach(function(cb) {{
    cb.addEventListener('change', function() {{
      // Future: filter charts by selected growers
    }});
  }});
}});

window.addEventListener('resize', function() {{
  PLOT_IDS.forEach(function(id) {{
    const el = document.getElementById('plot-' + id);
    if (el && el._fullLayout) {{
      Plotly.Plots.resize(el);
    }}
  }});
}});
</script>

</body>
</html>"""
