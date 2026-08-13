"""Reusable data-loading and validation functions for the dashboard.

All functions accept an explicit ``data_root`` Path so they work without
a pre-existing ``DATA_PIPELINE_DATA_ROOT`` environment variable.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from lib.dashboard_config import (
    CDL_END_YEAR,
    CDL_START_YEAR,
    CONFIRMED_NDVI_FIELDS,
    CROP_ORDER,
    GDD_BASE_C,
    GROWER_CONFIGS,
    GROWER_ORDER,
    NDVI_TARGET_YEAR,
    PROJECT_CRS,
    WEATHER_END_YEAR,
    WEATHER_START_YEAR,
)


def _pipeline_root(data_root: Path) -> Path:
    return data_root / "data-pipeline"


def _growers_root(data_root: Path) -> Path:
    return _pipeline_root(data_root) / "growers"


def _shared_root(data_root: Path) -> Path:
    return _pipeline_root(data_root) / "shared"


def _farm_prefix(farm_slug: str) -> str:
    normalized = farm_slug.replace("-", "_")
    if normalized.endswith("_farm"):
        normalized = normalized[: -len("_farm")]
    return normalized


def _field_slug(field_id: str) -> str:
    return field_id.lower()


def _grower_slug(label: str) -> str:
    return GROWER_CONFIGS[label]["grower_slug"]


def _farm_slug(label: str) -> str:
    return GROWER_CONFIGS[label]["farm_slug"]


def _field_boundaries_path(data_root: Path, label: str) -> Path:
    return (
        _growers_root(data_root)
        / _grower_slug(label)
        / "farms"
        / _farm_slug(label)
        / "boundary"
        / "field_boundaries.geojson"
    )


def _cdl_full_composition_path(data_root: Path, label: str) -> Path:
    prefix = _farm_prefix(_farm_slug(label))
    return (
        _growers_root(data_root)
        / _grower_slug(label)
        / "farms"
        / _farm_slug(label)
        / "derived"
        / "tables"
        / f"{prefix}_cdl_{CDL_START_YEAR}_{CDL_END_YEAR}_full_composition.csv"
    )


def _farm_weather_path(data_root: Path, label: str) -> Path:
    prefix = _farm_prefix(_farm_slug(label))
    return (
        _growers_root(data_root)
        / _grower_slug(label)
        / "farms"
        / _farm_slug(label)
        / "derived"
        / "tables"
        / f"{prefix}_weather_{WEATHER_START_YEAR}_{WEATHER_END_YEAR}.csv"
    )


def _field_weather_path(data_root: Path, label: str, field_id: str) -> Path:
    return (
        _growers_root(data_root)
        / _grower_slug(label)
        / "farms"
        / _farm_slug(label)
        / "fields"
        / _field_slug(field_id)
        / "weather"
        / "daily_weather.csv"
    )


def _field_satellite_dir(data_root: Path, label: str, field_id: str) -> Path:
    return (
        _growers_root(data_root)
        / _grower_slug(label)
        / "farms"
        / _farm_slug(label)
        / "fields"
        / _field_slug(field_id)
        / "satellite"
        / "sentinel"
    )


def _state_boundaries_path(data_root: Path) -> Path:
    return _shared_root(data_root) / "geoadmin" / "l1_states" / "states_usa.geojson"


def _dashboard_output_dir(data_root: Path) -> Path:
    return _shared_root(data_root) / "dashboard"


def _ssurgo_summary_path(data_root: Path, label: str) -> Path:
    prefix = _farm_prefix(_farm_slug(label))
    return (
        _growers_root(data_root)
        / _grower_slug(label)
        / "farms"
        / _farm_slug(label)
        / "derived"
        / "tables"
        / f"{prefix}_ssurgo_summary.csv"
    )


# ── data loading ────────────────────────────────────────────────────────


def load_field_boundaries(data_root: Path, label: str) -> gpd.GeoDataFrame:
    path = _field_boundaries_path(data_root, label)
    if not path.exists():
        raise FileNotFoundError(f"Field boundaries not found: {path}")
    gdf = gpd.read_file(path)
    gdf["grower"] = label
    gdf_proj = gdf.to_crs(PROJECT_CRS)
    gdf["perimeter_m"] = gdf_proj.geometry.length
    gdf["area_m2"] = gdf_proj.geometry.area
    gdf["compactness"] = gdf["perimeter_m"] / gdf["area_m2"]
    centroids_proj = gdf_proj.geometry.centroid
    centroids_wgs84 = gpd.GeoSeries(centroids_proj, crs=PROJECT_CRS).to_crs("EPSG:4326")
    gdf["centroid_lon"] = centroids_wgs84.x
    gdf["centroid_lat"] = centroids_wgs84.y
    return gdf


def load_cdl_composition(data_root: Path, label: str) -> pd.DataFrame:
    path = _cdl_full_composition_path(data_root, label)
    if not path.exists():
        raise FileNotFoundError(f"CDL composition not found: {path}")
    return pd.read_csv(path)


def load_farm_weather(data_root: Path, label: str) -> pd.DataFrame:
    path = _farm_weather_path(data_root, label)
    if not path.exists():
        raise FileNotFoundError(f"Farm weather not found: {path}")
    return pd.read_csv(path, parse_dates=["date"])


def load_field_weather(data_root: Path, label: str, field_id: str) -> pd.DataFrame:
    path = _field_weather_path(data_root, label, field_id)
    if not path.exists():
        raise FileNotFoundError(f"Field weather not found: {path}")
    return pd.read_csv(path, parse_dates=["date"])


def load_state_boundaries(data_root: Path) -> gpd.GeoDataFrame:
    path = _state_boundaries_path(data_root)
    if not path.exists():
        raise FileNotFoundError(f"State boundaries not found: {path}")
    return gpd.read_file(path)


def load_sentinel_ndvi(
    data_root: Path,
    label: str,
    field_id: str,
    year: int = NDVI_TARGET_YEAR,
) -> pd.DataFrame:
    sentinel_dir = _field_satellite_dir(data_root, label, field_id) / str(year)
    if not sentinel_dir.exists():
        raise FileNotFoundError(f"Sentinel directory not found: {sentinel_dir}")

    import rasterio

    records: list[dict[str, Any]] = []
    for date_dir in sorted(sentinel_dir.iterdir()):
        if not date_dir.is_dir():
            continue
        ndvi_tif = date_dir / f"{date_dir.name}_ndvi.tif"
        if not ndvi_tif.exists():
            continue
        try:
            with rasterio.open(ndvi_tif) as src:
                data = src.read(1, masked=True)
                valid = data.count()
                if valid == 0:
                    continue
                mean_val = float(data.mean())
                dt_str = date_dir.name.split("_", 1)[1]
                dt = pd.Timestamp(f"{dt_str[:4]}-{dt_str[4:6]}-{dt_str[6:8]}")
                records.append(
                    {
                        "date": dt,
                        "mean_ndvi": mean_val,
                        "valid_pixels": valid,
                    }
                )
        except Exception:
            continue

    ndvi_df = pd.DataFrame(records)
    if len(ndvi_df) > 0:
        ndvi_df["date"] = pd.to_datetime(ndvi_df["date"])
        ndvi_df = ndvi_df.sort_values("date").reset_index(drop=True)
    return ndvi_df


# ── derived computations ─────────────────────────────────────────────────


def compute_gdd(weather: pd.DataFrame) -> pd.DataFrame:
    df = weather.copy()
    df["GDD"] = np.maximum(0, (df["T2M_MAX"] + df["T2M_MIN"]) / 2 - GDD_BASE_C)
    df["GDD_cumsum"] = df["GDD"].cumsum()
    return df


def compute_seasonal_gdd(weather: pd.DataFrame) -> float:
    df = compute_gdd(weather)
    return float(df["GDD_cumsum"].max())


def detect_peak_ndvi(ndvi_df: pd.DataFrame) -> dict[str, Any]:
    if len(ndvi_df) == 0:
        return {"peak_ndvi": None, "peak_date": None}

    valid = ndvi_df[ndvi_df["mean_ndvi"].notna()]
    if len(valid) == 0:
        return {"peak_ndvi": None, "peak_date": None}

    peak_idx = valid["mean_ndvi"].idxmax()
    return {
        "peak_ndvi": round(float(valid.loc[peak_idx, "mean_ndvi"]), 4),
        "peak_date": str(valid.loc[peak_idx, "date"].date()),
    }


# ── validation helpers ───────────────────────────────────────────────────


def validate_weather_coverage(
    data_root: Path, label: str
) -> dict[str, Any]:
    weather_path = _farm_weather_path(data_root, label)
    if not weather_path.exists():
        return {"exists": False, "path": str(weather_path), "field_count": 0}

    df = pd.read_csv(weather_path, parse_dates=["date"])
    field_ids = sorted(df["field_id"].astype(str).unique())
    date_min = df["date"].min()
    date_max = df["date"].max()
    null_counts = {
        col: int(df[col].isna().sum())
        for col in ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR"]
        if col in df.columns
    }
    dup_key_count = int(df.duplicated(subset=["field_id", "date"]).sum())

    return {
        "exists": True,
        "path": str(weather_path),
        "field_count": len(field_ids),
        "field_ids": field_ids,
        "date_min": str(date_min.date()),
        "date_max": str(date_max.date()),
        "null_counts": null_counts,
        "duplicate_keys": dup_key_count,
    }


def validate_cdl_coverage(data_root: Path, label: str) -> dict[str, Any]:
    cdl_path = _cdl_full_composition_path(data_root, label)
    if not cdl_path.exists():
        return {"exists": False, "path": str(cdl_path)}

    df = pd.read_csv(cdl_path)
    field_ids = sorted(df["field_id"].astype(str).unique())
    years = sorted(df["year"].astype(int).unique())
    null_pct = int(df["pct"].isna().sum())
    null_pixels = int(df["pixel_count"].isna().sum())
    dup_keys = int(
        df.duplicated(subset=["field_id", "year", "crop_code"]).sum()
    )

    return {
        "exists": True,
        "path": str(cdl_path),
        "field_count": len(field_ids),
        "field_ids": field_ids,
        "years_covered": years,
        "null_pct": null_pct,
        "null_pixel_count": null_pixels,
        "duplicate_keys": dup_keys,
    }


def validate_boundaries(data_root: Path, label: str) -> dict[str, Any]:
    path = _field_boundaries_path(data_root, label)
    if not path.exists():
        return {"exists": False, "path": str(path)}

    gdf = gpd.read_file(path)
    field_ids = sorted(gdf["field_id"].astype(str).unique())
    null_area = int(gdf["area_acres"].isna().sum())
    dup_ids = int(gdf["field_id"].duplicated().sum())

    return {
        "exists": True,
        "path": str(path),
        "field_count": len(field_ids),
        "field_ids": field_ids,
        "null_area_acres": null_area,
        "duplicate_field_ids": dup_ids,
        "crs": str(gdf.crs),
    }


def validate_ndvi_coverage(
    data_root: Path, label: str
) -> dict[str, Any]:
    confirmed = CONFIRMED_NDVI_FIELDS.get(label, [])
    if not confirmed:
        return {"field_count": 0, "fields": []}

    results: list[dict[str, Any]] = []
    for entry in confirmed:
        field_id = str(entry["field_id"])
        year = int(entry["year"])
        try:
            ndvi_df = load_sentinel_ndvi(data_root, label, field_id, year)
            results.append(
                {
                    "field_id": field_id,
                    "year": year,
                    "scene_count": len(ndvi_df),
                    "dates": [str(d.date()) for d in ndvi_df["date"]]
                    if len(ndvi_df) > 0
                    else [],
                    "error": None,
                }
            )
        except FileNotFoundError as exc:
            results.append(
                {
                    "field_id": field_id,
                    "year": year,
                    "scene_count": 0,
                    "dates": [],
                    "error": str(exc),
                }
            )

    return {"field_count": len(confirmed), "fields": results}


def load_ssurgo_summary(data_root: Path, label: str) -> pd.DataFrame:
    path = _ssurgo_summary_path(data_root, label)
    if not path.exists():
        raise FileNotFoundError(f"SSURGO summary not found: {path}")
    return pd.read_csv(path)


def validate_soil_coverage(data_root: Path, label: str) -> dict[str, Any]:
    path = _ssurgo_summary_path(data_root, label)
    if not path.exists():
        return {"exists": False, "path": str(path), "field_count": 0}

    df = pd.read_csv(path)
    field_ids = sorted(df["field_id"].astype(str).unique())
    available_cols = [c for c in ["drainage_class", "avg_ph", "avg_om_pct"] if c in df.columns]
    null_counts = {col: int(df[col].isna().sum()) for col in available_cols}

    return {
        "exists": True,
        "path": str(path),
        "field_count": len(field_ids),
        "field_ids": field_ids,
        "available_columns": available_cols,
        "null_counts": null_counts,
    }


def build_soil_summary(data_root: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label in GROWER_ORDER:
        try:
            df = load_ssurgo_summary(data_root, label)
        except FileNotFoundError:
            continue
        for _, row in df.iterrows():
            rows.append(
                {
                    "grower": label,
                    "grower_slug": _grower_slug(label),
                    "field_id": str(row["field_id"]),
                    "drainage_class": str(row.get("drainage_class", ""))
                    if pd.notna(row.get("drainage_class"))
                    else "",
                    "avg_ph": round(float(row["avg_ph"]), 1)
                    if pd.notna(row.get("avg_ph"))
                    else None,
                    "avg_om_pct": round(float(row["avg_om_pct"]), 1)
                    if pd.notna(row.get("avg_om_pct"))
                    else None,
                    "dominant_soil": str(row.get("dominant_soil", ""))
                    if pd.notna(row.get("dominant_soil"))
                    else "",
                }
            )
    return pd.DataFrame(rows)


# ── ID consistency check ────────────────────────────────────────────────


def check_id_consistency(data_root: Path) -> dict[str, Any]:
    issues: list[str] = []
    for label in GROWER_ORDER:
        try:
            b = validate_boundaries(data_root, label)
            w = validate_weather_coverage(data_root, label)
            c = validate_cdl_coverage(data_root, label)
        except Exception as exc:
            issues.append(f"{label}: validation error — {exc}")
            continue

        if not b["exists"] or not c["exists"]:
            issues.append(f"{label}: boundaries or CDL missing")
            continue

        bound_ids = set(b["field_ids"])
        cdl_ids = set(c["field_ids"])

        in_cdl_not_bound = cdl_ids - bound_ids
        in_bound_not_cdl = bound_ids - cdl_ids
        if in_cdl_not_bound:
            issues.append(
                f"{label}: CDL field_ids not in boundaries: {sorted(in_cdl_not_bound)}"
            )
        if in_bound_not_cdl:
            issues.append(
                f"{label}: boundary field_ids not in CDL: {sorted(in_bound_not_cdl)}"
            )

        if w["exists"]:
            weather_ids = set(w["field_ids"])
            in_weather_not_bound = weather_ids - bound_ids
            if in_weather_not_bound:
                issues.append(
                    f"{label}: weather field_ids not in boundaries: "
                    f"{sorted(in_weather_not_bound)}"
                )

    return {"consistent": len(issues) == 0, "issues": issues}


# ── summary CSV builders ─────────────────────────────────────────────────


def build_field_summary(data_root: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label in GROWER_ORDER:
        gdf = load_field_boundaries(data_root, label)
        for _, row in gdf.iterrows():
            rows.append(
                {
                    "grower": label,
                    "grower_slug": _grower_slug(label),
                    "farm_slug": _farm_slug(label),
                    "field_id": row["field_id"],
                    "centroid_lat": round(float(row["centroid_lat"]), 6),
                    "centroid_lon": round(float(row["centroid_lon"]), 6),
                    "area_acres": round(float(row["area_acres"]), 2),
                    "compactness": round(float(row["compactness"]), 6),
                }
            )
    return pd.DataFrame(rows)


def build_weather_summary(data_root: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label in GROWER_ORDER:
        try:
            df = load_farm_weather(data_root, label)
        except FileNotFoundError:
            continue
        df["month"] = df["date"].dt.month
        monthly = (
            df.groupby("month")
            .agg(
                mean_temp_c=("T2M", "mean"),
                mean_precip_mm_day=("PRECTOTCORR", "mean"),
            )
            .reset_index()
        )
        field_count = df["field_id"].nunique()
        for _, row in monthly.iterrows():
            rows.append(
                {
                    "grower": label,
                    "grower_slug": _grower_slug(label),
                    "month": int(row["month"]),
                    "mean_temp_c": round(float(row["mean_temp_c"]), 2),
                    "mean_precip_mm_day": round(
                        float(row["mean_precip_mm_day"]), 2
                    ),
                    "field_count": field_count,
                }
            )
    return pd.DataFrame(rows)


def build_crop_summary(data_root: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label in GROWER_ORDER:
        df = load_cdl_composition(data_root, label)
        total_pixels = df["pixel_count"].sum()
        grouped = df.groupby("crop_name")["pixel_count"].sum()
        dominant_crop = grouped.idxmax()
        for crop_name in CROP_ORDER:
            if crop_name in grouped.index:
                pct = grouped[crop_name] / total_pixels * 100
                rows.append(
                    {
                        "grower": label,
                        "grower_slug": _grower_slug(label),
                        "crop_name": crop_name,
                        "pct_total": round(float(pct), 2),
                        "is_dominant": bool(crop_name == dominant_crop),
                    }
                )
        remaining = set(grouped.index) - set(CROP_ORDER)
        if remaining:
            other_pct = sum(
                grouped[c] / total_pixels * 100 for c in remaining
            )
            rows.append(
                {
                    "grower": label,
                    "grower_slug": _grower_slug(label),
                    "crop_name": "Other",
                    "pct_total": round(float(other_pct), 2),
                    "is_dominant": bool("Other" == dominant_crop),
                }
            )
    return pd.DataFrame(rows)


def build_rotation_summary(data_root: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label in GROWER_ORDER:
        df = load_cdl_composition(data_root, label)
        dom = df.loc[
            df.groupby(["field_id", "year"])["pct"].idxmax()
        ].copy()
        dom = dom.sort_values(["field_id", "year"])

        transitions: list[tuple[str, str]] = []
        for field_id in dom["field_id"].unique():
            sub = dom[dom["field_id"] == field_id]
            crops = sub["crop_name"].tolist()
            for prev_crop, next_crop in zip(crops[:-1], crops[1:]):
                transitions.append((prev_crop, next_crop))

        pairs = Counter(transitions)
        from_crops = set(fr for fr, _ in pairs.keys())
        for from_crop in sorted(from_crops):
            total_from = sum(
                count for (fr, _), count in pairs.items() if fr == from_crop
            )
            for to_crop in sorted(
                {to for fr, to in pairs.keys() if fr == from_crop}
            ):
                prob = pairs.get((from_crop, to_crop), 0) / total_from
                rows.append(
                    {
                        "grower": label,
                        "grower_slug": _grower_slug(label),
                        "from_crop": from_crop,
                        "to_crop": to_crop,
                        "probability": round(float(prob), 4),
                    }
                )
    return pd.DataFrame(rows)


def build_vegetation_summary(data_root: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label in GROWER_ORDER:
        confirmed = CONFIRMED_NDVI_FIELDS.get(label, [])
        for entry in confirmed:
            field_id = str(entry["field_id"])
            year = int(entry["year"])
            try:
                ndvi_df = load_sentinel_ndvi(data_root, label, field_id, year)
            except FileNotFoundError:
                continue
            for _, ndvi_row in ndvi_df.iterrows():
                rows.append(
                    {
                        "grower": label,
                        "grower_slug": _grower_slug(label),
                        "field_id": field_id,
                        "date": str(ndvi_row["date"].date()),
                        "ndvi_mean": round(float(ndvi_row["mean_ndvi"]), 4),
                    }
                )
    return pd.DataFrame(rows)


def build_coverage_summary(data_root: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label in GROWER_ORDER:
        b = validate_boundaries(data_root, label)
        w = validate_weather_coverage(data_root, label)
        c = validate_cdl_coverage(data_root, label)
        n = validate_ndvi_coverage(data_root, label)
        s = validate_soil_coverage(data_root, label)

        total_fields = b.get("field_count", 0)
        weather_fields = w.get("field_count", 0)
        cdl_years_str = (
            ",".join(str(y) for y in c.get("years_covered", []))
            if c.get("years_covered")
            else ""
        )
        ndvi_fields = n.get("field_count", 0)
        ndvi_years_str = (
            ",".join(
                str(f["year"])
                for f in n.get("fields", [])
                if f["scene_count"] > 0
            )
            if n.get("fields")
            else ""
        )
        soil_available = "yes" if s.get("exists") else "no"
        soil_fields = s.get("field_count", 0)

        rows.append(
            {
                "grower": label,
                "grower_slug": _grower_slug(label),
                "total_fields": total_fields,
                "weather_fields": weather_fields,
                "cdl_years": cdl_years_str,
                "ndvi_fields": ndvi_fields,
                "ndvi_years": ndvi_years_str,
                "soil_available": soil_available,
                "soil_fields": soil_fields,
            }
        )
    return pd.DataFrame(rows)


# ── full checklist runner ───────────────────────────────────────────────


def run_data_readiness_checklist(data_root: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "data_root": str(data_root),
        "growers": {},
        "id_consistency": {},
        "overall_ready": True,
    }

    for label in GROWER_ORDER:
        grower_report: dict[str, Any] = {}

        grower_report["boundaries"] = validate_boundaries(data_root, label)
        grower_report["cdl"] = validate_cdl_coverage(data_root, label)
        grower_report["weather"] = validate_weather_coverage(
            data_root, label
        )
        grower_report["ndvi"] = validate_ndvi_coverage(data_root, label)
        grower_report["soil"] = validate_soil_coverage(data_root, label)

        issues: list[str] = []
        if not grower_report["boundaries"]["exists"]:
            issues.append("boundaries missing")
        if not grower_report["cdl"]["exists"]:
            issues.append("CDL missing")
        if grower_report["weather"]["exists"]:
            w = grower_report["weather"]
            if w["duplicate_keys"] > 0:
                issues.append(f"weather has {w['duplicate_keys']} duplicate keys")
            if w.get("null_counts"):
                issues.append(f"weather nulls: {w['null_counts']}")
        if grower_report["cdl"]["exists"]:
            c = grower_report["cdl"]
            if c["duplicate_keys"] > 0:
                issues.append(f"CDL has {c['duplicate_keys']} duplicate keys")

        grower_report["issues"] = issues
        report["growers"][label] = grower_report
        if issues:
            report["overall_ready"] = False

    report["id_consistency"] = check_id_consistency(data_root)
    if not report["id_consistency"]["consistent"]:
        report["overall_ready"] = False

    state_boundary_path = _state_boundaries_path(data_root)
    report["state_boundaries_exists"] = state_boundary_path.exists()

    return report
