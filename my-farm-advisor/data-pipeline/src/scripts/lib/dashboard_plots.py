"""Dashboard Plotly figure builders.

Each function accepts DataFrames from the summary CSV files and returns a
Plotly ``Figure`` ready for JSON serialisation.  All colours follow the
central ``dashboard_config.GROWER_COLORS`` palette.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from lib.dashboard_config import (
    CROP_COLORS,
    CROP_ORDER,
    CORN_GDD_MILESTONES,
    GDD_BASE_C,
    GROWER_COLORS,
    GROWER_ORDER,
    SOYBEAN_GDD_MILESTONES,
)

_DEFAULT_PLOT_HEIGHT = 350
_NO_DATA_MSG = (
    "<i>No data available for this visualisation.</i>"
)

# ── helpers ─────────────────────────────────────────────────────────────


def _grower_color(label: str) -> str:
    return GROWER_COLORS.get(label, "#999999")


def _empty_figure(message: str = _NO_DATA_MSG) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color="#888"),
    )
    fig.update_layout(
        height=200,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


# ── Tab 1: Overview ─────────────────────────────────────────────────────


def build_field_size_boxplot(field_df: pd.DataFrame) -> go.Figure:
    if field_df.empty or "area_acres" not in field_df.columns:
        return _empty_figure("No field size data available.")

    fig = go.Figure()
    for label in GROWER_ORDER:
        vals = field_df[field_df["grower"] == label]["area_acres"].dropna().tolist()
        if len(vals) == 0:
            continue
        fig.add_trace(
            go.Box(
                y=vals,
                name=label,
                marker_color=_grower_color(label),
                boxmean=True,
            )
        )
    fig.update_layout(
        title="Field Size Distribution by Grower",
        yaxis_title="Area (acres)",
        height=_DEFAULT_PLOT_HEIGHT,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
    )
    return fig


def build_compactness_histogram(field_df: pd.DataFrame) -> go.Figure:
    if field_df.empty or "compactness" not in field_df.columns:
        return _empty_figure("No compactness data available.")

    fig = go.Figure()
    for label in GROWER_ORDER:
        vals = field_df[field_df["grower"] == label]["compactness"].dropna().tolist()
        if len(vals) == 0:
            continue
        fig.add_trace(
            go.Histogram(
                x=vals,
                name=label,
                marker_color=_grower_color(label),
                opacity=0.7,
                nbinsx=8,
            )
        )
    fig.update_layout(
        title="Field Compactness by Grower<br><sup>Lower = more compact</sup>",
        xaxis_title="Perimeter / Area (m/m\u00b2)",
        yaxis_title="Number of fields",
        height=_DEFAULT_PLOT_HEIGHT,
        margin=dict(l=10, r=10, t=50, b=10),
        barmode="overlay",
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
    )
    return fig


def build_soil_drainage_chart(soil_df: pd.DataFrame) -> go.Figure:
    if soil_df.empty or "drainage_class" not in soil_df.columns:
        return _empty_figure("No SSURGO drainage data available.")

    classes: list[str] = []
    data: dict[str, list[int]] = {label: [] for label in GROWER_ORDER}
    for label in GROWER_ORDER:
        sub = soil_df[soil_df["grower"] == label]
        counts = sub["drainage_class"].value_counts()
        for cls in sorted(counts.index):
            if cls and cls not in classes:
                classes.append(cls)
        for cls in classes:
            data[label].append(int(counts.get(cls, 0)))

    if not classes:
        return _empty_figure("No drainage classes found in SSURGO data.")

    fig = go.Figure()
    for i, label in enumerate(GROWER_ORDER):
        fig.add_trace(
            go.Bar(
                name=label,
                x=classes,
                y=data[label],
                marker_color=_grower_color(label),
            )
        )
    fig.update_layout(
        title="SSURGO Drainage Class Distribution",
        xaxis_title="Drainage class",
        yaxis_title="Number of fields",
        height=_DEFAULT_PLOT_HEIGHT,
        margin=dict(l=10, r=10, t=40, b=80),
        barmode="group",
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
    )
    return fig


# ── Tab 2: Field Locations ──────────────────────────────────────────────


def build_field_map(field_df: pd.DataFrame) -> go.Figure:
    if field_df.empty:
        return _empty_figure("No field location data available.")

    required = {"centroid_lat", "centroid_lon", "area_acres"}
    if not required.issubset(field_df.columns):
        return _empty_figure("Field data missing centroid coordinates.")

    fig = go.Figure()
    for label in GROWER_ORDER:
        sub = field_df[field_df["grower"] == label]
        if sub.empty:
            continue
        fig.add_trace(
            go.Scattermapbox(
                lat=sub["centroid_lat"].tolist(),
                lon=sub["centroid_lon"].tolist(),
                mode="markers",
                marker=dict(
                    size=sub["area_acres"].tolist(),
                    sizemode="area",
                    sizeref=2.0 * max(sub["area_acres"].max(), 1) / (18**2),
                    color=_grower_color(label),
                ),
                name=label,
                customdata=sub["area_acres"].tolist(),
                text=sub["field_id"].tolist(),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Grower: %{name}<br>"
                    "Area: %{customdata:.1f} acres<br>"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=41.8, lon=-93.5),
            zoom=5,
        ),
        height=500,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center"),
    )
    return fig


# ── Tab 3: Weather ──────────────────────────────────────────────────────


def build_temperature_cycle(weather_df: pd.DataFrame) -> go.Figure:
    if weather_df.empty:
        return _empty_figure("No weather data available.")

    fig = go.Figure()
    for label in GROWER_ORDER:
        sub = weather_df[weather_df["grower"] == label].sort_values("month")
        if sub.empty or "mean_temp_c" not in sub.columns:
            continue
        field_count = sub["field_count"].iloc[0] if "field_count" in sub.columns else "?"
        fig.add_trace(
            go.Scatter(
                x=sub["month"].tolist(),
                y=sub["mean_temp_c"].tolist(),
                mode="lines+markers",
                name=f"{label} ({field_count} fields)",
                line=dict(color=_grower_color(label), width=2),
                marker=dict(size=6),
            )
        )
    fig.add_hline(
        y=10, line_dash="dash", line_color="gray", opacity=0.5,
        annotation_text="10\u00b0C",
    )

    month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    fig.update_layout(
        title="Monthly Temperature Cycle (2021\u20132025 average)",
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(1, 13)),
            ticktext=month_labels,
        ),
        yaxis_title="Mean temperature (\u00b0C)",
        height=_DEFAULT_PLOT_HEIGHT,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
    )
    return fig


def build_precipitation_comparison(weather_df: pd.DataFrame) -> go.Figure:
    if weather_df.empty:
        return _empty_figure("No weather data available.")

    fig = go.Figure()
    for label in GROWER_ORDER:
        sub = weather_df[weather_df["grower"] == label].sort_values("month")
        if sub.empty or "mean_precip_mm_day" not in sub.columns:
            continue
        field_count = sub["field_count"].iloc[0] if "field_count" in sub.columns else "?"
        fig.add_trace(
            go.Bar(
                x=sub["month"].tolist(),
                y=sub["mean_precip_mm_day"].tolist(),
                name=f"{label} ({field_count} fields)",
                marker_color=_grower_color(label),
                opacity=0.8,
            )
        )
    month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    fig.update_layout(
        title="Monthly Precipitation by Grower (2021\u20132025 average)",
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(1, 13)),
            ticktext=month_labels,
        ),
        yaxis_title="Mean daily precipitation (mm/day)",
        height=_DEFAULT_PLOT_HEIGHT,
        margin=dict(l=10, r=10, t=40, b=10),
        barmode="group",
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
    )
    return fig


def build_climate_space(weather_df: pd.DataFrame) -> go.Figure:
    if weather_df.empty:
        return _empty_figure("No weather data available.")

    required = {"mean_temp_c", "mean_precip_mm_day"}
    if not required.issubset(weather_df.columns):
        return _empty_figure("Weather data missing required columns.")

    fig = go.Figure()
    for label in GROWER_ORDER:
        sub = weather_df[weather_df["grower"] == label]
        if sub.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=sub["mean_precip_mm_day"].tolist(),
                y=sub["mean_temp_c"].tolist(),
                mode="markers",
                name=label,
                marker=dict(
                    color=_grower_color(label),
                    size=12,
                    line=dict(width=1, color="white"),
                ),
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    "Precip: %{x:.2f} mm/day<br>"
                    "Temp: %{y:.1f}\u00b0C<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        title="Climate Space by Grower<br><sup>Monthly averages, 2021\u20132025</sup>",
        xaxis_title="Mean daily precipitation (mm/day)",
        yaxis_title="Mean temperature (\u00b0C)",
        height=_DEFAULT_PLOT_HEIGHT,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
    )
    return fig


# ── Tab 4: Crop Distribution ────────────────────────────────────────────


def build_crop_composition(crop_df: pd.DataFrame) -> go.Figure:
    if crop_df.empty:
        return _empty_figure("No CDL crop data available.")

    all_crops = [c for c in CROP_ORDER if c in crop_df["crop_name"].unique()]

    fig = go.Figure()
    for crop in all_crops:
        vals = []
        for label in GROWER_ORDER:
            row = crop_df[
                (crop_df["grower"] == label) & (crop_df["crop_name"] == crop)
            ]
            vals.append(row["pct_total"].iloc[0] if len(row) > 0 else 0.0)
        fig.add_trace(
            go.Bar(
                name=crop,
                x=GROWER_ORDER,
                y=vals,
                marker_color=CROP_COLORS.get(crop, "#a9a9a9"),
            )
        )
    fig.update_layout(
        title="Crop Composition by Grower (2021\u20132025, all fields)",
        yaxis_title="Percent of total pixels",
        height=_DEFAULT_PLOT_HEIGHT,
        margin=dict(l=10, r=10, t=40, b=10),
        barmode="stack",
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
    )
    return fig


def build_rotation_heatmap(rotation_df: pd.DataFrame) -> go.Figure:
    if rotation_df.empty:
        return _empty_figure("No rotation data available.")

    crops = sorted(
        set(rotation_df["from_crop"].unique())
        | set(rotation_df["to_crop"].unique())
    )

    heatmaps = []
    titles = []
    for label in GROWER_ORDER:
        sub = rotation_df[rotation_df["grower"] == label]
        matrix = pd.DataFrame(0.0, index=crops, columns=crops)
        for _, row in sub.iterrows():
            fc = row["from_crop"]
            tc = row["to_crop"]
            if fc in matrix.index and tc in matrix.columns:
                matrix.loc[fc, tc] = row["probability"]
        heatmaps.append(matrix.values)
        titles.append(label)

    n = len(GROWER_ORDER)
    cols = min(n, 3)
    rows_count = (n + cols - 1) // cols

    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=rows_count,
        cols=cols,
        subplot_titles=titles,
        shared_yaxes=True,
    )

    for i, (matrix, label) in enumerate(zip(heatmaps, titles)):
        row = i // cols + 1
        col = i % cols + 1
        fig.add_trace(
            go.Heatmap(
                z=matrix.tolist(),
                x=crops,
                y=crops,
                colorscale="YlGn",
                zmin=0,
                zmax=1,
                text=np.round(matrix, 2).tolist(),
                texttemplate="%{text:.2f}",
                textfont=dict(size=9),
                showscale=(i == 0),
                colorbar=dict(title="Probability", len=0.8) if i == 0 else None,
                name=label,
            ),
            row=row,
            col=col,
        )

    fig.update_layout(
        title="Crop Rotation Transition Probabilities",
        height=250 * rows_count,
        margin=dict(l=10, r=10, t=40, b=40),
    )
    return fig


# ── Tab 5: Vegetation Health ────────────────────────────────────────────


def build_ndvi_timeseries(veg_df: pd.DataFrame) -> go.Figure:
    if veg_df.empty or "ndvi_mean" not in veg_df.columns:
        return _empty_figure("No NDVI data available for any field-year.")

    veg_df = veg_df.dropna(subset=["ndvi_mean"]).copy()
    if veg_df.empty:
        return _empty_figure("No valid NDVI values found.")

    field_id = str(veg_df["field_id"].iloc[0])
    veg_df["date"] = pd.to_datetime(veg_df["date"])
    veg_df = veg_df.sort_values("date")

    fig = go.Figure()
    fig.add_trace(
            go.Scatter(
                x=veg_df["date"].tolist(),
                y=veg_df["ndvi_mean"].tolist(),
            mode="lines+markers",
            name=f"NDVI — {field_id}",
            line=dict(color="#228B22", width=2),
            marker=dict(size=8, color="#228B22", line=dict(width=1, color="white")),
        )
    )

    peak_idx = veg_df["ndvi_mean"].idxmax()
    peak_row = veg_df.loc[peak_idx]
    fig.add_annotation(
        x=peak_row["date"],
        y=peak_row["ndvi_mean"] + 0.04,
        text=f"Peak {peak_row['ndvi_mean']:.3f}",
        showarrow=True,
        arrowhead=1,
        font=dict(size=10, color="#8B0000"),
    )

    fig.update_layout(
        title=f"Sentinel-2 NDVI — {field_id} (field mean)",
        xaxis_title="Date",
        yaxis_title="NDVI",
        yaxis=dict(range=[0, 0.85]),
        height=_DEFAULT_PLOT_HEIGHT + 50,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def build_gdd_chart(
    daily_weather: pd.DataFrame | None = None,
    crop_type: str = "Soybeans",
) -> go.Figure:
    if daily_weather is None or daily_weather.empty:
        return _empty_figure("No daily weather data for GDD calculation.")

    required = {"date", "T2M_MAX", "T2M_MIN"}
    if not required.issubset(daily_weather.columns):
        return _empty_figure("Daily weather missing T2M_MAX or T2M_MIN.")

    df = daily_weather.copy()
    df = df.sort_values("date")
    df["GDD"] = np.maximum(0, (df["T2M_MAX"] + df["T2M_MIN"]) / 2 - GDD_BASE_C)
    df["GDD_cumsum"] = df["GDD"].cumsum()

    milestones = (
        SOYBEAN_GDD_MILESTONES
        if crop_type.lower() == "soybeans"
        else CORN_GDD_MILESTONES
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"].tolist(),
            y=df["GDD_cumsum"].tolist(),
            mode="lines",
            name=f"Cumulative GDD ({crop_type})",
            line=dict(color="#2ca02c", width=2),
            fill="tozeroy",
            fillcolor="rgba(44,160,44,0.08)",
        )
    )
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="green",
        opacity=0.3,
        annotation_text=f"Base {GDD_BASE_C}\u00b0C",
    )

    for label, threshold in milestones:
        reached = df[df["GDD_cumsum"] >= threshold]
        if len(reached) > 0:
            stage_date = reached.iloc[0]["date"]
            gdd_val = reached.iloc[0]["GDD_cumsum"]
            fig.add_annotation(
                x=stage_date,
                y=gdd_val,
                text=label,
                showarrow=True,
                arrowhead=1,
                font=dict(size=9, color="#8B0000"),
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#8B0000",
                borderpad=3,
                ax=20,
                ay=-30,
            )

    fig.update_layout(
        title=f"Cumulative Growing Degree Days — {crop_type} (base {GDD_BASE_C}\u00b0C)",
        xaxis_title="Date",
        yaxis_title=f"GDD (\u00b0C-days, base {GDD_BASE_C}\u00b0C)",
        height=_DEFAULT_PLOT_HEIGHT + 100,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


# ── figure collection ───────────────────────────────────────────────────


def build_all_figures(
    field_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    crop_df: pd.DataFrame,
    rotation_df: pd.DataFrame,
    veg_df: pd.DataFrame,
    soil_df: pd.DataFrame,
    daily_weather: pd.DataFrame | None = None,
) -> dict[str, go.Figure]:
    figures: dict[str, go.Figure] = {}

    figures["field_size"] = build_field_size_boxplot(field_df)
    figures["compactness"] = build_compactness_histogram(field_df)
    figures["soil_drainage"] = build_soil_drainage_chart(soil_df)
    figures["field_map"] = build_field_map(field_df)
    figures["temperature"] = build_temperature_cycle(weather_df)
    figures["precipitation"] = build_precipitation_comparison(weather_df)
    figures["climate_space"] = build_climate_space(weather_df)
    figures["crop_composition"] = build_crop_composition(crop_df)
    figures["rotation"] = build_rotation_heatmap(rotation_df)
    figures["ndvi"] = build_ndvi_timeseries(veg_df)

    crop_type = "Soybeans"
    if not veg_df.empty and "field_id" in veg_df.columns:
        figures["gdd"] = build_gdd_chart(daily_weather, crop_type)
    else:
        figures["gdd"] = _empty_figure("No daily weather data for GDD computation.")

    return figures
