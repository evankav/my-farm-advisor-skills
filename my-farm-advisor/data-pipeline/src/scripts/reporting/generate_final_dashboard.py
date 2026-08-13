#!/usr/bin/env python3
"""Step 4 — Generate the Final Integrated Dashboard.

Reads the seven Phase A summary CSV files, computes KPIs, builds Plotly
figures, and assembles a single self-contained HTML dashboard.

Usage:
    export DATA_PIPELINE_DATA_ROOT=/absolute/path/to/runtime
    python generate_final_dashboard.py
    python generate_final_dashboard.py --summary-dir /custom/summaries
    python generate_final_dashboard.py --output ~/Desktop/dashboard.html
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPT_DIR.parent
sys.path.insert(0, str(_SRC_DIR))

from lib.dashboard_config import (
    CONFIRMED_NDVI_FIELDS,
    GROWER_ORDER,
    NDVI_TARGET_YEAR,
)
from lib.dashboard_kpis import (
    compute_grower_table,
    compute_overview_kpis,
    load_summary_csvs,
)
from lib.dashboard_layout import build_dashboard_html
from lib.dashboard_plots import build_all_figures
from lib.dashboard_data import (
    _dashboard_output_dir,
    compute_gdd,
    load_field_weather,
)

_PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.27.0.min.js"
_PLOTLY_CACHE = Path.home() / ".cache" / "my-farm-advisor" / "plotly-2.27.0.min.js"


def _get_plotly_bundle() -> str:
    if _PLOTLY_CACHE.exists():
        return _PLOTLY_CACHE.read_text(encoding="utf-8")

    import requests

    print(f"Downloading Plotly.js bundle ...")
    resp = requests.get(_PLOTLY_CDN, timeout=60)
    resp.raise_for_status()
    js = resp.text
    if not js or len(js) < 1000:
        raise RuntimeError("Downloaded Plotly bundle appears empty")
    _PLOTLY_CACHE.parent.mkdir(parents=True, exist_ok=True)
    _PLOTLY_CACHE.write_text(js, encoding="utf-8")
    return js


def _resolve_summary_dir(args: argparse.Namespace) -> Path:
    if args.summary_dir:
        p = Path(args.summary_dir)
        if p.is_dir():
            return p
        sys.exit(f"Summary directory not found: {p}")

    raw = os.environ.get("DATA_PIPELINE_DATA_ROOT")
    if raw:
        default = _dashboard_output_dir(Path(raw))
        if default.is_dir():
            return default

    sys.exit(
        "No summary data found. Either:\n"
        "  1. Set DATA_PIPELINE_DATA_ROOT and run prepare_dashboard_data.py first, or\n"
        "  2. Use --summary-dir to point at an existing summary directory."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the Integrated Field Intelligence Dashboard"
    )
    parser.add_argument(
        "--summary-dir",
        default=None,
        help="Path to directory containing dashboard summary CSV files.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output HTML path (default: shared/dashboard/integrated_field_intelligence_dashboard.html).",
    )
    args = parser.parse_args()

    summary_dir = _resolve_summary_dir(args)
    print(f"Summary dir: {summary_dir}")

    print("Loading summary CSVs ...")
    summaries = load_summary_csvs(summary_dir)
    found = [k for k in summaries]
    missing = [k for k in ["field", "weather", "crop", "rotation", "vegetation", "coverage", "soil"] if k not in summaries]
    print(f"  Found ({len(found)}): {', '.join(found)}")
    if missing:
        print(f"  Missing ({len(missing)}): {', '.join(missing)}")

    field_df = summaries.get("field", _empty_frame())
    weather_df = summaries.get("weather", _empty_frame())
    crop_df = summaries.get("crop", _empty_frame())
    rotation_df = summaries.get("rotation", _empty_frame())
    veg_df = summaries.get("vegetation", _empty_frame())
    soil_df = summaries.get("soil", _empty_frame())

    print("Computing KPIs ...")
    overview_kpis = compute_overview_kpis(summaries=summaries)
    grower_table = compute_grower_table(summaries=summaries)
    print(f"  Growers: {overview_kpis.get('grower_count', 0)}")
    print(f"  Fields:  {overview_kpis.get('total_fields', 0)}")
    print(f"  Acres:   {overview_kpis.get('total_acres', 0):,.0f}")

    print("Loading daily weather for GDD ...")
    daily_weather = None
    ndvi_coverage_note = ""
    try:
        for label in GROWER_ORDER:
            confirmed = CONFIRMED_NDVI_FIELDS.get(label, [])
            for entry in confirmed:
                field_id = str(entry["field_id"])
                try:
                    raw = os.environ.get("DATA_PIPELINE_DATA_ROOT")
                    if raw:
                        data_root = Path(raw)
                        daily_weather = load_field_weather(data_root, label, field_id)
                        daily_weather = daily_weather[
                            daily_weather["date"].dt.year == NDVI_TARGET_YEAR
                        ]
                        print(f"  Loaded weather for {label}/{field_id}: {len(daily_weather)} days")
                    break
                except Exception as exc:
                    print(f"  Skipping daily weather for {label}/{field_id}: {exc}")
                    continue
            if daily_weather is not None:
                break
    except Exception:
        pass

    if daily_weather is None:
        print("  No daily weather loaded — GDD chart will show placeholder")

    ndvi_count = len(veg_df) if not veg_df.empty else 0
    if ndvi_count > 0:
        ndvi_field = veg_df["field_id"].iloc[0] if "field_id" in veg_df.columns else "?"
        ndvi_coverage_note = (
            f"NDVI coverage: {ndvi_count} observation(s) — {ndvi_field}. "
            "Additional field-years pending pipeline extension."
        )

    print("Building Plotly figures ...")
    figures = build_all_figures(
        field_df=field_df,
        weather_df=weather_df,
        crop_df=crop_df,
        rotation_df=rotation_df,
        veg_df=veg_df,
        soil_df=soil_df,
        daily_weather=daily_weather,
    )
    print(f"  Built {len(figures)} figures")

    print("Serialising figures ...")
    figures_json: dict[str, str] = {}
    for key, fig in figures.items():
        js_key = key.replace("_", "-")
        figures_json[js_key] = fig.to_json()

    print("Fetching Plotly.js ...")
    plotly_bundle = _get_plotly_bundle()
    print(f"  Bundle: {len(plotly_bundle):,} bytes")

    print("Assembling HTML ...")
    html = build_dashboard_html(
        figures_json=figures_json,
        overview_kpis=overview_kpis,
        grower_table=grower_table,
        plotly_bundle=plotly_bundle,
        ndvi_coverage_note=ndvi_coverage_note,
    )
    print(f"  HTML size: {len(html):,} bytes")

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = summary_dir / "integrated_field_intelligence_dashboard.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"Dashboard written: {output_path}")
    print(f"  Open with: firefox {output_path}")
    print(f"{'=' * 60}")
    return 0


def _empty_frame() -> "pd.DataFrame":
    import pandas as pd
    return pd.DataFrame()


if __name__ == "__main__":
    sys.exit(main())
