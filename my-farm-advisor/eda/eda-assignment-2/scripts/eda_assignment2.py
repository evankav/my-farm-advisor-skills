"""Assignment 2 field-level EDA: compare IL, IA, NE across boundaries, CDL, and weather.

Generates 9 static PNG figures under the configured output directory.
Run from the runtime root with DATA_PIPELINE_DATA_ROOT set.
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)

# ── path helpers ────────────────────────────────────────────────────────────

DATA_ROOT = Path(os.environ.get("DATA_PIPELINE_DATA_ROOT", ""))
if not DATA_ROOT.is_dir():
    sys.exit("FATAL: set DATA_PIPELINE_DATA_ROOT to your runtime root.")

OUTPUT = DATA_ROOT / "data-pipeline" / "eda" / "eda-assignment-2" / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)

GROWER_SLUGS: dict[str, str] = {
    "Illinois": "northern-illinois-grower",
    "Iowa": "northern-iowa-grower",
    "Nebraska": "central-nebraska-grower",
}

FARM_SLUGS: dict[str, str] = {
    "Illinois": "northern-illinois-grower-illinois",
    "Iowa": "northern-iowa-grower-iowa",
    "Nebraska": "central-nebraska-grower-nebraska",
}

COLORS = {"Illinois": "#e41a1c", "Iowa": "#377eb8", "Nebraska": "#4daf4a"}
ORDER = ["Illinois", "Iowa", "Nebraska"]

PROJECT_CRS = "EPSG:5070"  # NAD83 Conus Albers for accurate area / perimeter


# ── figure 1: field size distribution ──────────────────────────────────────

def fig_field_size_distribution() -> None:
    sizes: dict[str, list[float]] = {}
    for name in ORDER:
        slug = GROWER_SLUGS[name]
        farm = FARM_SLUGS[name]
        p = DATA_ROOT / "data-pipeline" / "growers" / slug / "farms" / farm / "boundary" / "field_boundaries.geojson"
        gdf = gpd.read_file(p)
        sizes[name] = gdf["area_acres"].dropna().tolist()

    fig, ax = plt.subplots(figsize=(8, 5))
    data = []
    tick_labels = []
    for name in ORDER:
        data.append(sizes[name])
        tick_labels.append(f"{name}\n(n={len(sizes[name])})")
    bp = ax.boxplot(data, patch_artist=True, widths=0.5)
    ax.set_xticklabels(tick_labels)
    for patch, name in zip(bp["boxes"], ORDER):
        patch.set_facecolor(COLORS[name])
        patch.set_alpha(0.5)
    for name in ORDER:
        jitter = np.random.default_rng(42).uniform(-0.15, 0.15, len(sizes[name]))
        ax.scatter(
            [ORDER.index(name) + 1 + j for j in jitter],
            sizes[name],
            color=COLORS[name],
            alpha=0.7,
            s=40,
            zorder=3,
        )
    ax.set_ylabel("Field area (acres)")
    ax.set_title("Field size distribution by grower")
    fig.tight_layout()
    fig.savefig(OUTPUT / "field_size_distribution_by_grower.png", dpi=300)
    plt.close(fig)
    print("  ✓ field_size_distribution_by_grower.png")


# ── figure 2: field compactness (perimeter / area) ─────────────────────────

def fig_field_compactness() -> None:
    ratios: dict[str, list[float]] = {}
    for name in ORDER:
        slug = GROWER_SLUGS[name]
        farm = FARM_SLUGS[name]
        p = DATA_ROOT / "data-pipeline" / "growers" / slug / "farms" / farm / "boundary" / "field_boundaries.geojson"
        gdf = gpd.read_file(p).to_crs(PROJECT_CRS)
        perim = gdf.geometry.length  # meters
        area_m2 = gdf.geometry.area  # sq meters
        # perimeter / area = compactness (lower = more compact)
        ratios[name] = (perim / area_m2).dropna().tolist()

    fig, ax = plt.subplots(figsize=(8, 5))
    for i, name in enumerate(ORDER):
        vals = ratios[name]
        ax.hist(
            vals,
            bins=8,
            alpha=0.55,
            color=COLORS[name],
            label=f"{name} (n={len(vals)})",
            edgecolor="white",
        )
    ax.set_xlabel("Perimeter / Area (m / m²)")
    ax.set_ylabel("Number of fields")
    ax.set_title("Field compactness by grower\n(lower = more compact)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT / "field_compactness_by_grower.png", dpi=300)
    plt.close(fig)
    print("  ✓ field_compactness_by_grower.png")


# ── figure 3: field size vs latitude ───────────────────────────────────────

def fig_field_size_vs_latitude() -> None:
    all_data: list[dict] = []
    for name in ORDER:
        slug = GROWER_SLUGS[name]
        farm = FARM_SLUGS[name]
        p = DATA_ROOT / "data-pipeline" / "growers" / slug / "farms" / farm / "boundary" / "field_boundaries.geojson"
        gdf = gpd.read_file(p)
        lat_lon = gdf.to_crs(PROJECT_CRS).geometry.centroid
        gdf_proj = gdf.to_crs(PROJECT_CRS)
        centroids_wgs84 = gdf.geometry.centroid
        for idx, row in gdf.iterrows():
            all_data.append({
                "grower": name,
                "area_acres": row["area_acres"],
                "latitude": centroids_wgs84[idx].y,
            })
    df = pd.DataFrame(all_data)
    fig, ax = plt.subplots(figsize=(8, 5))
    for name in ORDER:
        sub = df[df["grower"] == name]
        ax.scatter(sub["latitude"], sub["area_acres"], color=COLORS[name], label=name, alpha=0.7, s=50, edgecolors="white", linewidth=0.5)
    ax.set_xlabel("Latitude (°N)")
    ax.set_ylabel("Field area (acres)")
    ax.set_title("Field size vs. latitude")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT / "field_size_vs_latitude.png", dpi=300)
    plt.close(fig)
    print("  ✓ field_size_vs_latitude.png")


# ── figure 4: crop composition stacked bar ─────────────────────────────────

CROP_ORDER = ["Corn", "Soybeans", "Winter Wheat", "Alfalfa", "Fallow/Idle", "Grass/Pasture", "Forest", "Other"]
CROP_COLORS = {
    "Corn": "#ffd700",
    "Soybeans": "#228b22",
    "Winter Wheat": "#d2b48c",
    "Alfalfa": "#9370db",
    "Fallow/Idle": "#cd853f",
    "Grass/Pasture": "#90ee90",
    "Forest": "#006400",
    "Other": "#a9a9a9",
}

def _slug_underscore(name: str) -> str:
    return FARM_SLUGS[name].replace("-", "_")


def _load_cdl_full(name: str) -> pd.DataFrame:
    farm_dir = FARM_SLUGS[name]
    farm_file = _slug_underscore(name)
    p = DATA_ROOT / "data-pipeline" / "growers" / GROWER_SLUGS[name] / "farms" / farm_dir / "derived" / "tables" / f"{farm_file}_cdl_2021_2025_full_composition.csv"
    return pd.read_csv(p)


def fig_crop_composition() -> None:
    comp: dict[str, dict[str, float]] = {}
    for name in ORDER:
        df = _load_cdl_full(name)
        total = df["pixel_count"].sum()
        groups = df.groupby("crop_name")["pixel_count"].sum()
        others = 0
        row: dict[str, float] = {}
        for crop in CROP_ORDER:
            if crop in groups.index:
                row[crop] = groups[crop] / total * 100
            else:
                row[crop] = 0.0
        remaining = groups.index.difference(CROP_ORDER)
        for c in remaining:
            others += groups[c] / total * 100
        row["Other"] = others
        comp[name] = row

    fig, ax = plt.subplots(figsize=(9, 5.5))
    categories = [c for c in CROP_ORDER if any(comp[g][c] > 0 for g in ORDER)] + ["Other"]
    bottom = np.zeros(len(ORDER))
    for crop in categories:
        vals = [comp[g][crop] for g in ORDER]
        color = CROP_COLORS.get(crop, "#a9a9a9")
        ax.bar(ORDER, vals, bottom=bottom, label=crop, color=color, edgecolor="white", linewidth=0.5)
        bottom += vals
    ax.set_ylabel("Percent of total pixels")
    ax.set_title("Crop composition by grower (all fields, 2021–2025)")
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUTPUT / "crop_composition_by_grower.png", dpi=300)
    plt.close(fig)
    print("  ✓ crop_composition_by_grower.png")


# ── figure 5: crop purity boxplot ──────────────────────────────────────────

def fig_crop_purity() -> None:
    rows: list[dict] = []
    for name in ORDER:
        df = _load_cdl_full(name)
        dominant = df.loc[df.groupby(["field_id", "year"])["pct"].idxmax()]
        for _, r in dominant.iterrows():
            rows.append({"grower": name, "pct": r["pct"], "crop": r["crop_name"]})
    plot_df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(8, 5))
    bp = ax.boxplot(
        [plot_df[plot_df["grower"] == g]["pct"] for g in ORDER],
        patch_artist=True, widths=0.5,
    )
    ax.set_xticklabels([f"{g}\n(n={len(plot_df[plot_df['grower']==g])})" for g in ORDER])
    for patch, name in zip(bp["boxes"], ORDER):
        patch.set_facecolor(COLORS[name])
        patch.set_alpha(0.5)
    for i, name in enumerate(ORDER):
        sub = plot_df[plot_df["grower"] == name]
        jitter = np.random.default_rng(7).uniform(-0.15, 0.15, len(sub))
        ax.scatter([i + 1 + j for j in jitter], sub["pct"], color=COLORS[name], alpha=0.5, s=25, zorder=3)
    ax.set_ylabel("Percent of field in dominant crop")
    ax.set_title("Field-level crop purity by grower")
    fig.tight_layout()
    fig.savefig(OUTPUT / "crop_purity_by_grower.png", dpi=300)
    plt.close(fig)
    print("  ✓ crop_purity_by_grower.png")


# ── figure 6: crop rotation transition heatmap ─────────────────────────────

def fig_crop_transition() -> None:
    all_transitions: dict[str, list[tuple[str, str]]] = {}
    for name in ORDER:
        df = _load_cdl_full(name)
        dom = df.loc[df.groupby(["field_id", "year"])["pct"].idxmax()].copy()
        dom = dom.sort_values(["field_id", "year"])
        transitions: list[tuple[str, str]] = []
        for field_id in dom["field_id"].unique():
            sub = dom[dom["field_id"] == field_id]
            crops = sub["crop_name"].tolist()
            for prev_crop, next_crop in zip(crops[:-1], crops[1:]):
                transitions.append((prev_crop, next_crop))
        all_transitions[name] = transitions

    crops_seen = sorted({c for trans in all_transitions.values() for pair in trans for c in pair})
    if "Other" not in crops_seen:
        crops_seen.append("Other")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
    for ax, name in zip(axes, ORDER):
        trans = all_transitions[name]
        pairs = Counter(trans)
        matrix = pd.DataFrame(0, index=crops_seen, columns=crops_seen, dtype=float)
        for (prev_, next_), count in pairs.items():
            prev = prev_ if prev_ in crops_seen else "Other"
            next_ = next_ if next_ in crops_seen else "Other"
            matrix.loc[prev, next_] = count
        row_sums = matrix.sum(axis=1)
        for r in matrix.index:
            if row_sums[r] > 0:
                matrix.loc[r] = matrix.loc[r] / row_sums[r]
        sns.heatmap(matrix, annot=True, fmt=".2f", cmap="YlGn", cbar=False, ax=ax, vmin=0, vmax=1, linewidths=0.5)
        ax.set_title(name, fontsize=12)
        ax.set_xlabel("To crop", fontsize=9)
        if ax == axes[0]:
            ax.set_ylabel("From crop", fontsize=9)
    fig.suptitle("Crop rotation transition probabilities", fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(OUTPUT / "crop_transition_heatmap.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("  ✓ crop_transition_heatmap.png")


# ── figure 7: monthly temperature cycle ────────────────────────────────────

def _load_weather(name: str) -> pd.DataFrame:
    farm_dir = FARM_SLUGS[name]
    farm_file = _slug_underscore(name)
    p = DATA_ROOT / "data-pipeline" / "growers" / GROWER_SLUGS[name] / "farms" / farm_dir / "derived" / "tables" / f"{farm_file}_weather_2021_2025.csv"
    df = pd.read_csv(p, parse_dates=["date"])
    df["month"] = df["date"].dt.month
    df["grower"] = name
    return df


def fig_monthly_temperature() -> None:
    frames = [_load_weather(n) for n in ORDER]
    df = pd.concat(frames, ignore_index=True)
    monthly = df.groupby(["grower", "month"])["T2M"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(8, 5))
    for name in ORDER:
        sub = monthly[monthly["grower"] == name]
        ax.plot(sub["month"], sub["T2M"], color=COLORS[name], marker="o", label=name, linewidth=2)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_ylabel("Mean temperature (°C)")
    ax.set_title("Monthly temperature cycle (2021–2025 average)")
    ax.axhline(10, color="gray", linestyle="--", alpha=0.5, label="10°C threshold")
    ax.legend(loc="lower right")
    n_il = df[df["grower"] == "Illinois"]["field_id"].nunique()
    n_ia = df[df["grower"] == "Iowa"]["field_id"].nunique()
    n_ne = df[df["grower"] == "Nebraska"]["field_id"].nunique()
    ax.text(0.98, 0.02, f"Fields: IL={n_il}, IA={n_ia}, NE={n_ne}",
            transform=ax.transAxes, fontsize=8, ha="right", va="bottom",
            style="italic", color="gray")
    fig.tight_layout()
    fig.savefig(OUTPUT / "monthly_temperature_cycle.png", dpi=300)
    plt.close(fig)
    print(f"  ✓ monthly_temperature_cycle.png  (fields: IL={n_il}, IA={n_ia}, NE={n_ne})")


# ── figure 8: monthly precipitation ────────────────────────────────────────

def fig_monthly_precipitation() -> None:
    frames = [_load_weather(n) for n in ORDER]
    df = pd.concat(frames, ignore_index=True)
    monthly = df.groupby(["grower", "month"])["PRECTOTCORR"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(8, 5))
    width = 0.25
    x = np.arange(1, 13)
    for i, name in enumerate(ORDER):
        sub = monthly[monthly["grower"] == name]
        ax.bar(x + i * width, sub["PRECTOTCORR"], width, label=name, color=COLORS[name], alpha=0.8)
    ax.set_xticks(x + width)
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_ylabel("Mean daily precipitation (mm / day)")
    ax.set_title("Monthly precipitation by grower (2021–2025 average)")
    ax.legend()
    ax.text(0.98, 0.98, f"Fields: IL={df[df['grower']=='Illinois']['field_id'].nunique()}, IA={df[df['grower']=='Iowa']['field_id'].nunique()}, NE={df[df['grower']=='Nebraska']['field_id'].nunique()}",
            transform=ax.transAxes, fontsize=8, ha="right", va="top",
            style="italic", color="gray")
    fig.tight_layout()
    fig.savefig(OUTPUT / "monthly_precipitation_by_grower.png", dpi=300)
    plt.close(fig)
    print("  ✓ monthly_precipitation_by_grower.png")


# ── figure 9: climate space ────────────────────────────────────────────────

def fig_climate_space() -> None:
    frames = [_load_weather(n) for n in ORDER]
    df = pd.concat(frames, ignore_index=True)
    monthly = df.groupby(["grower", "month"]).agg({"T2M": "mean", "PRECTOTCORR": "mean"}).reset_index()

    fig, ax = plt.subplots(figsize=(8, 5))
    for name in ORDER:
        sub = monthly[monthly["grower"] == name]
        ax.scatter(sub["PRECTOTCORR"], sub["T2M"], color=COLORS[name], label=name, alpha=0.7, s=60, edgecolors="white", linewidth=0.5)
    ax.set_xlabel("Mean daily precipitation (mm / day)")
    ax.set_ylabel("Mean temperature (°C)")
    ax.set_title("Climate space by grower\n(monthly averages, 2021–2025)")
    ax.legend()
    ax.text(0.98, 0.02, f"Fields: IL={df[df['grower']=='Illinois']['field_id'].nunique()}, IA={df[df['grower']=='Iowa']['field_id'].nunique()}, NE={df[df['grower']=='Nebraska']['field_id'].nunique()}",
            transform=ax.transAxes, fontsize=8, ha="right", va="bottom",
            style="italic", color="gray")
    fig.tight_layout()
    fig.savefig(OUTPUT / "climate_space_by_grower.png", dpi=300)
    plt.close(fig)
    print("  ✓ climate_space_by_grower.png")


# ── figure 10: field location map ───────────────────────────────────────────

SHARED = DATA_ROOT / "data-pipeline" / "shared"


def fig_field_location_map() -> None:
    states_path = SHARED / "geoadmin" / "l1_states" / "states_usa.geojson"
    if not states_path.exists():
        print("  ⚠ states_usa.geojson not found — skipping map")
        return
    states = gpd.read_file(states_path)
    target = states[states["state_code"].isin(["IL", "IA", "NE"])].to_crs(PROJECT_CRS)

    fig, ax = plt.subplots(figsize=(10, 7))
    target.plot(ax=ax, facecolor="#e8e8e8", edgecolor="#555555", linewidth=1.0, alpha=0.6)

    for name in ORDER:
        slug = GROWER_SLUGS[name]
        farm = FARM_SLUGS[name]
        p = DATA_ROOT / "data-pipeline" / "growers" / slug / "farms" / farm / "boundary" / "field_boundaries.geojson"
        gdf = gpd.read_file(p).to_crs(PROJECT_CRS)
        centroids = gdf.geometry.centroid
        ax.scatter(centroids.x, centroids.y, color=COLORS[name], label=name,
                   s=80, edgecolor="white", linewidth=0.8, alpha=0.9, zorder=5)

    for _, row in target.iterrows():
        centroid = row.geometry.centroid
        ax.text(centroid.x, centroid.y, row["state_code"], fontsize=16, fontweight="bold",
                ha="center", va="center", color="#333333", alpha=0.5)

    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title("Field location map — field centroids colored by grower", fontsize=13, fontweight="bold")
    ax.legend(loc="lower right", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUTPUT / "field_location_map.png", dpi=300)
    plt.close(fig)
    print("  ✓ field_location_map.png")


# ── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"Output → {OUTPUT}\n")

    print("── Field boundaries ──")
    fig_field_size_distribution()
    fig_field_compactness()
    fig_field_size_vs_latitude()

    print("\n── CDL / Cropland data layer ──")
    fig_crop_composition()
    fig_crop_purity()
    fig_crop_transition()

    print("\n── Weather ──")
    fig_monthly_temperature()
    fig_monthly_precipitation()
    fig_climate_space()

    print("\n── Geospatial ──")
    fig_field_location_map()

    print(f"\nDone. {len(list(OUTPUT.glob('*.png')))} PNGs in {OUTPUT}")


if __name__ == "__main__":
    main()
