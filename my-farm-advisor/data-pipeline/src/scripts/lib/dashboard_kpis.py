"""Dashboard KPI computation module.

Reads the seven Phase A summary CSV files and returns structured
dictionaries for each dashboard section. All functions accept either a
``Path`` to the summary directory or pre-loaded DataFrames.

No plotly, matplotlib, or heavy dependencies needed here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from lib.dashboard_config import (
    CROP_ORDER,
    GROWER_COLORS,
    GROWER_ORDER,
    SUMMARY_FILES,
)


def load_summary_csvs(summary_dir: Path) -> dict[str, pd.DataFrame]:
    """Load all seven summary CSV files from the given directory."""
    frames: dict[str, pd.DataFrame] = {}
    for key, filename in SUMMARY_FILES.items():
        path = summary_dir / filename
        if path.exists():
            frames[key] = pd.read_csv(path)
    return frames


def compute_overview_kpis(
    summary_dir: Path | None = None,
    summaries: dict[str, pd.DataFrame] | None = None,
) -> dict[str, Any]:
    """Compute the high-level overview KPIs for the dashboard header."""
    if summaries is None and summary_dir is not None:
        summaries = load_summary_csvs(summary_dir)
    if summaries is None:
        return {}

    field_df = summaries.get("field", pd.DataFrame())
    coverage_df = summaries.get("coverage", pd.DataFrame())
    crop_df = summaries.get("crop", pd.DataFrame())

    total_fields = len(field_df)
    total_acres = round(float(field_df["area_acres"].sum()), 1) if "area_acres" in field_df.columns else 0
    grower_count = len(GROWER_ORDER)

    years_covered = "2021–2025"
    distinct_crops = sorted(crop_df["crop_name"].unique().tolist()) if "crop_name" in crop_df.columns else []

    weather_fields = int(coverage_df["weather_fields"].sum()) if not coverage_df.empty else 0
    ndvi_fields = int(coverage_df["ndvi_fields"].sum()) if not coverage_df.empty else 0
    soil_fields = int(coverage_df.get("soil_fields", pd.Series()).sum()) if not coverage_df.empty else 0

    return {
        "total_fields": total_fields,
        "total_acres": total_acres,
        "grower_count": grower_count,
        "years_covered": years_covered,
        "distinct_crops": distinct_crops,
        "crop_count": len(distinct_crops),
        "weather_field_count": weather_fields,
        "ndvi_field_count": ndvi_fields,
        "soil_field_count": soil_fields,
    }


def compute_grower_table(
    summary_dir: Path | None = None,
    summaries: dict[str, pd.DataFrame] | None = None,
) -> list[dict[str, Any]]:
    """Return a list of per-grower KPI dicts for the Overview table."""
    if summaries is None and summary_dir is not None:
        summaries = load_summary_csvs(summary_dir)
    if summaries is None:
        return []

    field_df = summaries.get("field", pd.DataFrame())
    weather_df = summaries.get("weather", pd.DataFrame())
    coverage_df = summaries.get("coverage", pd.DataFrame())
    crop_df = summaries.get("crop", pd.DataFrame())
    soil_df = summaries.get("soil", pd.DataFrame())

    rows: list[dict[str, Any]] = []
    for label in GROWER_ORDER:
        f = field_df[field_df["grower"] == label]
        c = coverage_df[coverage_df["grower"] == label]
        cr = crop_df[crop_df["grower"] == label]
        w = weather_df[weather_df["grower"] == label]
        s = soil_df[soil_df["grower"] == label] if not soil_df.empty else pd.DataFrame()

        total = len(f)
        median_acres = round(float(f["area_acres"].median()), 1) if not f.empty else None
        total_acres = round(float(f["area_acres"].sum()), 1) if not f.empty else None

        weather_f = int(c["weather_fields"].iloc[0]) if not c.empty and "weather_fields" in c.columns else 0
        ndvi_f = int(c["ndvi_fields"].iloc[0]) if not c.empty else 0
        soil_f = int(c["soil_fields"].iloc[0]) if not c.empty and "soil_fields" in c.columns else 0

        dominant = ""
        if not cr.empty:
            dom_mask = cr["is_dominant"] == True
            if dom_mask.any():
                dominant = str(cr.loc[dom_mask, "crop_name"].iloc[0])

        mean_temp = round(float(w["mean_temp_c"].mean()), 1) if not w.empty else None
        mean_precip = round(float(w["mean_precip_mm_day"].mean()), 2) if not w.empty else None

        avg_ph = round(float(s["avg_ph"].mean()), 1) if not s.empty and "avg_ph" in s.columns else None
        avg_om = round(float(s["avg_om_pct"].mean()), 1) if not s.empty and "avg_om_pct" in s.columns else None

        rows.append(
            {
                "grower": label,
                "color": GROWER_COLORS.get(label, "#999"),
                "total_fields": total,
                "median_acres": median_acres,
                "total_acres": total_acres,
                "weather_fields": weather_f,
                "ndvi_fields": ndvi_f,
                "soil_fields": soil_f,
                "dominant_crop": dominant,
                "mean_temp_c": mean_temp,
                "mean_precip_mm_day": mean_precip,
                "avg_ph": avg_ph,
                "avg_om_pct": avg_om,
            }
        )

    return rows


def compute_soil_drainage(
    summary_dir: Path | None = None,
    summaries: dict[str, pd.DataFrame] | None = None,
) -> dict[str, Any]:
    """Compute drainage class distribution per grower."""
    if summaries is None and summary_dir is not None:
        summaries = load_summary_csvs(summary_dir)
    if summaries is None:
        return {}

    soil_df = summaries.get("soil", pd.DataFrame())
    if soil_df.empty:
        return {"available": False}

    drainage_by_grower: dict[str, dict[str, int]] = {}
    for label in GROWER_ORDER:
        sub = soil_df[soil_df["grower"] == label]
        if sub.empty:
            continue
        counts = sub["drainage_class"].value_counts().to_dict()
        drainage_by_grower[label] = {str(k): int(v) for k, v in counts.items() if k}

    all_classes = sorted(
        {cls for dist in drainage_by_grower.values() for cls in dist}
    )

    return {
        "available": True,
        "classes": all_classes,
        "by_grower": drainage_by_grower,
    }


def compute_rotation_text(
    summary_dir: Path | None = None,
    summaries: dict[str, pd.DataFrame] | None = None,
) -> dict[str, list[str]]:
    """Extract notable rotation patterns per grower for Interpretation tab."""
    if summaries is None and summary_dir is not None:
        summaries = load_summary_csvs(summary_dir)
    if summaries is None:
        return {}

    rot_df = summaries.get("rotation", pd.DataFrame())
    if rot_df.empty:
        return {}

    patterns: dict[str, list[str]] = {}
    for label in GROWER_ORDER:
        sub = rot_df[rot_df["grower"] == label]
        items: list[str] = []
        corn_corn = sub[(sub["from_crop"] == "Corn") & (sub["to_crop"] == "Corn")]
        if not corn_corn.empty:
            prob = corn_corn["probability"].iloc[0]
            if prob > 0.1:
                items.append(f"Continuous corn: {prob:.0%}")
        soy_corn = sub[(sub["from_crop"] == "Soybeans") & (sub["to_crop"] == "Corn")]
        if not soy_corn.empty:
            prob = soy_corn["probability"].iloc[0]
            items.append(f"Soy→Corn: {prob:.0%}")
        corn_soy = sub[(sub["from_crop"] == "Corn") & (sub["to_crop"] == "Soybeans")]
        if not corn_soy.empty:
            prob = corn_soy["probability"].iloc[0]
            items.append(f"Corn→Soy: {prob:.0%}")
        patterns[label] = items
    return patterns
