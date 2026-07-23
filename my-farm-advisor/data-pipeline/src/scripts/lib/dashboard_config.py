"""Shared configuration constants for the final integrated dashboard.

No runtime or environment dependencies. Safe to import anywhere.
"""

from __future__ import annotations

GROWER_CONFIGS: dict[str, dict[str, str]] = {
    "Illinois": {
        "grower_slug": "northern-illinois-grower",
        "farm_slug": "northern-illinois-grower-illinois",
        "county": "Iroquois",
        "state": "IL",
        "state_fips": "17",
    },
    "Iowa": {
        "grower_slug": "northern-iowa-grower",
        "farm_slug": "northern-iowa-grower-iowa",
        "county": "Kossuth",
        "state": "IA",
        "state_fips": "19",
    },
    "Nebraska": {
        "grower_slug": "central-nebraska-grower",
        "farm_slug": "central-nebraska-grower-nebraska",
        "county": "York",
        "state": "NE",
        "state_fips": "31",
    },
}

GROWER_ORDER: list[str] = ["Illinois", "Iowa", "Nebraska"]

GROWER_COLORS: dict[str, str] = {
    "Illinois": "#e41a1c",
    "Iowa": "#377eb8",
    "Nebraska": "#4daf4a",
}

CROP_ORDER: list[str] = [
    "Corn",
    "Soybeans",
    "Winter Wheat",
    "Alfalfa",
    "Fallow/Idle",
    "Grass/Pasture",
    "Forest",
    "Other",
]

CROP_COLORS: dict[str, str] = {
    "Corn": "#ffd700",
    "Soybeans": "#228b22",
    "Winter Wheat": "#d2b48c",
    "Alfalfa": "#9370db",
    "Fallow/Idle": "#cd853f",
    "Grass/Pasture": "#90ee90",
    "Forest": "#006400",
    "Other": "#a9a9a9",
}

PROJECT_CRS: str = "EPSG:5070"

SOYBEAN_GDD_MILESTONES: list[tuple[str, float]] = [
    ("VE emergence", 130.0),
    ("R1 flowering", 500.0),
    ("R5 seed-fill", 900.0),
    ("R7 maturity", 1400.0),
]

CORN_GDD_MILESTONES: list[tuple[str, float]] = [
    ("V6", 475.0),
    ("VT/R1 silking", 1150.0),
    ("R5 dent", 1950.0),
    ("R6 maturity", 2700.0),
]

GDD_BASE_C: float = 10.0

CDL_START_YEAR: int = 2021
CDL_END_YEAR: int = 2025

WEATHER_START_YEAR: int = 2021
WEATHER_END_YEAR: int = 2025

NDVI_TARGET_YEAR: int = 2025

CONFIRMED_NDVI_FIELDS: dict[str, list[dict[str, str | int]]] = {
    "Illinois": [
        {
            "field_id": "osm-1499474531",
            "year": 2025,
            "crop": "Soybeans",
        },
    ],
}

DASHBOARD_DATA_DIR_NAME: str = "dashboard"

SUMMARY_FILES: dict[str, str] = {
    "field": "dashboard_field_summary.csv",
    "weather": "dashboard_weather_summary.csv",
    "crop": "dashboard_crop_summary.csv",
    "rotation": "dashboard_rotation_summary.csv",
    "vegetation": "dashboard_vegetation_summary.csv",
    "coverage": "dashboard_data_coverage.csv",
    "soil": "dashboard_soil_summary.csv",
}
