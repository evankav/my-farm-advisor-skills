#!/usr/bin/env python3
"""Test fixtures for dashboard generation tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_farm_dir(tmp_path):
    """Create a temporary farm directory structure with minimal valid data."""
    farm_dir = tmp_path / "growers" / "test-grower" / "farms" / "test-farm"
    boundary_dir = farm_dir / "boundary"
    boundary_dir.mkdir(parents=True)
    fields_dir = farm_dir / "fields"
    fields_dir.mkdir(parents=True)

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "field_id": "osm-test-001",
                    "area_acres": 100.0,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-94.0, 43.0],
                            [-94.0, 43.01],
                            [-93.99, 43.01],
                            [-93.99, 43.0],
                            [-94.0, 43.0],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "field_id": "osm-test-002",
                    "area_acres": 50.0,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-94.01, 43.0],
                            [-94.01, 43.01],
                            [-94.0, 43.01],
                            [-94.0, 43.0],
                            [-94.01, 43.0],
                        ]
                    ],
                },
            },
        ],
    }
    (boundary_dir / "field_boundaries.geojson").write_text(json.dumps(geojson))

    field_dir_1 = fields_dir / "osm-test-001"
    field_dir_2 = fields_dir / "osm-test-002"
    field_dir_1.mkdir(parents=True)
    field_dir_2.mkdir(parents=True)

    field1_meta = {
        "grower_slug": "test-grower",
        "farm_slug": "test-farm",
        "field_slug": "osm-test-001",
        "display_name": "Field One",
        "field_id": "OSM_test_001",
    }
    (field_dir_1 / "field.json").write_text(json.dumps(field1_meta))

    field2_meta = {"field_slug": "osm-test-002", "field_id": "OSM_test_002"}
    (field_dir_2 / "field.json").write_text(json.dumps(field2_meta))

    return farm_dir


@pytest.fixture
def temp_farm_dir_with_weather(temp_farm_dir):
    """Create a farm directory with valid weather data."""
    import csv

    fields_dir = temp_farm_dir / "fields"

    for field_slug, base_temp in [("osm-test-001", 5.0), ("osm-test-002", 7.0)]:
        weather_dir = fields_dir / field_slug / "weather"
        weather_dir.mkdir(parents=True, exist_ok=True)
        csv_path = weather_dir / "daily_weather.csv"

        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "field_id", "lat", "lon", "date",
                    "T2M", "T2M_MAX", "T2M_MIN",
                    "PRECTOTCORR", "ALLSKY_SFC_SW_DWN",
                    "RH2M", "WS10M",
                ]
            )
            for day in range(1, 366):
                date_str = f"2025-{day:03d}-T00:00:00Z" if day <= 365 else "2025-12-31"
                if day <= 31:
                    date_str = f"2025-{day:02d}-01"
                elif day <= 59:
                    date_str = f"2025-02-{day - 31:02d}"
                elif day <= 90:
                    date_str = f"2025-03-{day - 59:02d}"
                elif day <= 120:
                    date_str = f"2025-04-{day - 90:02d}"
                elif day <= 151:
                    date_str = f"2025-05-{day - 120:02d}"
                elif day <= 181:
                    date_str = f"2025-06-{day - 151:02d}"
                elif day <= 212:
                    date_str = f"2025-07-{day - 181:02d}"
                elif day <= 243:
                    date_str = f"2025-08-{day - 212:02d}"
                elif day <= 273:
                    date_str = f"2025-09-{day - 243:02d}"
                elif day <= 304:
                    date_str = f"2025-10-{day - 273:02d}"
                elif day <= 334:
                    date_str = f"2025-11-{day - 304:02d}"
                else:
                    date_str = f"2025-12-{day - 334:02d}"

                tmin = -3.0 if day < 110 else (8.0 + day * 0.05)
                tmax = tmin + 10.0
                precip = 2.0 if day > 150 else 0.5
                writer.writerow(
                    [
                        field_slug, 43.005, -93.995, date_str,
                        tmin + 5, tmax, tmin,
                        precip, 15.0, 70.0, 3.0,
                    ]
                )

    return temp_farm_dir


@pytest.fixture
def temp_farm_dir_header_only_weather(temp_farm_dir):
    """Create a farm directory where one field has header-only weather."""
    fields_dir = temp_farm_dir / "fields"
    weather_dir = fields_dir / "osm-test-001" / "weather"
    weather_dir.mkdir(parents=True, exist_ok=True)
    (weather_dir / "daily_weather.csv").write_text(
        "field_id,lat,lon,date,T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN,RH2M,WS10M\n"
    )
    return temp_farm_dir


@pytest.fixture
def temp_farm_dir_multipolygon(tmp_path):
    """Create a farm directory with a MultiPolygon field."""
    farm_dir = tmp_path / "growers" / "mp-grower" / "farms" / "mp-farm"
    boundary_dir = farm_dir / "boundary"
    boundary_dir.mkdir(parents=True)
    fields_dir = farm_dir / "fields"
    fields_dir.mkdir(parents=True)

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"field_id": "osm-mp-001", "area_acres": 200.0},
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [
                            [
                                [-94.0, 43.0],
                                [-94.0, 43.005],
                                [-93.99, 43.005],
                                [-93.99, 43.0],
                                [-94.0, 43.0],
                            ]
                        ],
                        [
                            [
                                [-94.01, 43.0],
                                [-94.01, 43.005],
                                [-94.0, 43.005],
                                [-94.0, 43.0],
                                [-94.01, 43.0],
                            ]
                        ],
                    ],
                },
            }
        ],
    }
    (boundary_dir / "field_boundaries.geojson").write_text(json.dumps(geojson))

    field_dir = fields_dir / "osm-mp-001"
    field_dir.mkdir(parents=True)
    (field_dir / "field.json").write_text(
        json.dumps(
            {
                "field_slug": "osm-mp-001",
                "field_id": "OSM_mp_001",
                "display_name": "Multi Field",
            }
        )
    )

    return farm_dir


@pytest.fixture
def temp_farm_dir_no_field_json(temp_farm_dir):
    """Create a farm directory where field.json is missing."""
    (temp_farm_dir / "fields" / "osm-test-001" / "field.json").unlink()
    return temp_farm_dir


@pytest.fixture
def mock_plotly_bundle(monkeypatch):
    """Mock the Plotly.js bundle fetch to avoid network calls."""
    fake_js = "/* Plotly.js v2.35.0 minified placeholder */\nwindow.Plotly={};"

    def _mock_get_plotly_bundle(**kwargs):
        return fake_js

    import reporting.generate_weather_dashboard as dwd

    monkeypatch.setattr(dwd, "get_plotly_bundle", _mock_get_plotly_bundle)
    return fake_js


@pytest.fixture
def mock_satellite_basemap(monkeypatch):
    """Mock satellite basemap fetch to avoid network calls."""
    import base64

    fake_png = base64.b64encode(b"FakePNGData").decode("utf-8")

    def _mock_fetch_satellite(**kwargs):
        return (fake_png, (-10500000.0, 5300000.0, -10400000.0, 5400000.0))

    import reporting.generate_weather_dashboard as dwd

    monkeypatch.setattr(dwd, "fetch_satellite_basemap", _mock_fetch_satellite)
    return fake_png


@pytest.fixture
def iowa_farm_dir():
    """Return the Iowa fixture farm dir if it exists, else return None."""
    path = Path(
        "~/my-farm-advisor-runtime/data-pipeline/growers/"
        "northern-iowa-grower/farms/northern-iowa-grower-iowa"
    ).expanduser()
    if path.is_dir():
        return path
    return None
