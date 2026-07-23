#!/usr/bin/env python3
"""Tests for the weather dashboard generation module."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest

_SCRIPT_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "scripts"
)
sys.path.insert(0, str(_SCRIPT_DIR / "lib"))
sys.path.insert(0, str(_SCRIPT_DIR))

from reporting.generate_weather_dashboard import (
    _compute_last_frost_date,
    _default_year,
    _extract_field_data,
    _load_farm_boundary,
    _load_field_metadata,
    _load_field_weather,
    _process_weather_for_field,
    generate_dashboard,
)
from farm_discovery import (
    DiscoveryError,
    _is_valid_farm_dir,
    discover_farm_dir,
    extract_grower_and_farm_slugs,
)


class TestFarmDiscovery:
    def test_is_valid_farm_dir(self, temp_farm_dir):
        assert _is_valid_farm_dir(temp_farm_dir) is True

    def test_is_not_valid_farm_dir(self, tmp_path):
        assert _is_valid_farm_dir(tmp_path) is False

    def test_discover_farm_dir_explicit(self, temp_farm_dir):
        result = discover_farm_dir(farm_dir=str(temp_farm_dir))
        assert result == temp_farm_dir.resolve()

    def test_discover_farm_dir_nonexistent(self):
        with pytest.raises(DiscoveryError, match="does not exist"):
            discover_farm_dir(farm_dir="/nonexistent/path")

    def test_discover_farm_dir_invalid(self, tmp_path):
        with pytest.raises(DiscoveryError, match="missing required files"):
            discover_farm_dir(farm_dir=str(tmp_path))

    def test_discover_farm_dir_growers_with_multiple(self, tmp_path):
        farm1 = tmp_path / "farm1"
        farm2 = tmp_path / "farm2"
        for farm in (farm1, farm2):
            (farm / "boundary").mkdir(parents=True)
            (farm / "boundary" / "field_boundaries.geojson").write_text(
                '{"type":"FeatureCollection","features":[]}'
            )
            (farm / "fields").mkdir()

        with pytest.raises(DiscoveryError, match="Multiple farms"):
            discover_farm_dir(growers_dir=str(tmp_path))

    def test_extract_grower_and_farm_slugs_canonical(self, temp_farm_dir):
        grower, farm = extract_grower_and_farm_slugs(temp_farm_dir)
        assert grower == "test-grower"
        assert farm == "test-farm"

    def test_extract_grower_and_farm_slugs_flat(self, tmp_path):
        grower, farm = extract_grower_and_farm_slugs(tmp_path)
        assert isinstance(grower, str)
        assert isinstance(farm, str)
        assert len(grower) > 0
        assert len(farm) > 0


class TestFieldDataLoading:
    def test_load_farm_boundary(self, temp_farm_dir):
        gdf = _load_farm_boundary(temp_farm_dir)
        assert len(gdf) == 2
        assert gdf.crs is not None

    def test_load_farm_boundary_missing(self, tmp_path):
        with pytest.raises(DiscoveryError, match="Missing boundary file"):
            _load_farm_boundary(tmp_path)

    def test_load_field_metadata(self, temp_farm_dir):
        meta = _load_field_metadata(temp_farm_dir / "fields" / "osm-test-001")
        assert meta.get("display_name") == "Field One"

    def test_load_field_metadata_missing(self, temp_farm_dir):
        meta = _load_field_metadata(temp_farm_dir / "fields" / "osm-test-002")
        assert meta.get("field_id") == "OSM_test_002"

    def test_load_field_weather_empty(self, temp_farm_dir):
        df = _load_field_weather(temp_farm_dir / "fields" / "osm-test-001")
        assert df.empty

    def test_load_field_weather_with_data(self, temp_farm_dir_with_weather):
        df = _load_field_weather(
            temp_farm_dir_with_weather / "fields" / "osm-test-001"
        )
        assert not df.empty
        assert "T2M_MIN" in df.columns
        assert "T2M_MAX" in df.columns
        assert "PRECTOTCORR" in df.columns

    def test_load_field_weather_header_only(self, temp_farm_dir_header_only_weather):
        df = _load_field_weather(
            temp_farm_dir_header_only_weather / "fields" / "osm-test-001"
        )
        assert df.empty or len(df) == 0


class TestWeatherProcessing:
    def test_compute_last_frost_date_finds_latest_before_july(self):
        dates = pd.date_range("2025-01-01", "2025-06-30")
        data = {
            "date": dates,
            "T2M_MIN": [-1.0] * 120 + [2.0] * (len(dates) - 120),
        }
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        frost_date, frost_doy = _compute_last_frost_date(df, 2025)
        assert frost_date.month == 4
        assert frost_date.day == 30
        assert frost_doy == 120

    def test_compute_last_frost_date_no_frost(self):
        dates = pd.date_range("2025-01-01", "2025-06-30")
        data = {
            "date": dates,
            "T2M_MIN": [5.0] * len(dates),
        }
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        frost_date, frost_doy = _compute_last_frost_date(df, 2025)
        assert frost_date == pd.Timestamp("2025-01-01").date()
        assert frost_doy == 1

    def test_compute_last_frost_date_frost_after_july_ignored(self):
        dates = pd.date_range("2025-01-01", "2025-12-31")
        n_half = len(dates) // 2
        temps = [2.0] * 181 + [-1.0] * 30 + [2.0] * (len(dates) - 211)
        data = {
            "date": dates,
            "T2M_MIN": temps,
        }
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        frost_date, _ = _compute_last_frost_date(df, 2025)
        assert frost_date is not None

    def test_process_weather_generates_correct_records(self):
        dates = pd.date_range("2025-04-01", "2025-09-30")
        n = len(dates)
        data = {
            "date": dates,
            "T2M_MIN": [8.0] * n,
            "T2M_MAX": [22.0] * n,
            "PRECTOTCORR": [2.0] * n,
        }
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])

        results = _process_weather_for_field("test", df)
        assert len(results) == 1
        assert results[0]["fieldId"] == "test"
        assert results[0]["year"] == 2025

        daily = results[0]["daily"]
        assert len(daily) > 0

        expected_gdd = max((22.0 + 8.0) / 2.0 - 10.0, 0.0)
        assert daily[0]["dailyGdd"] == round(expected_gdd, 2)

        expected_rain_in = round(2.0 * 0.0393701, 2)
        assert daily[0]["dailyRainfallIn"] == expected_rain_in

    def test_process_weather_missing_columns(self):
        df = pd.DataFrame(
            {"date": pd.to_datetime(["2025-01-01"]), "T2M": [5.0]}
        )
        results = _process_weather_for_field("test", df)
        assert results == []


class TestComputeGdd:
    def test_gdd_formula(self):
        """Test GDD formula: max((T2M_MAX + T2M_MIN) / 2 - 10.0, 0)"""
        from reporting.generate_weather_dashboard import _GDD_BASE_C

        tmin, tmax = 10.0, 20.0
        gdd = max((tmax + tmin) / 2.0 - _GDD_BASE_C, 0.0)
        assert gdd == 5.0

        tmin, tmax = 0.0, 10.0
        gdd = max((tmax + tmin) / 2.0 - _GDD_BASE_C, 0.0)
        assert gdd == 0.0

    def test_rainfall_conversion(self):
        """Test rainfall mm to inches."""
        from reporting.generate_weather_dashboard import _MM_TO_INCH

        rain_in = 25.4 * _MM_TO_INCH
        assert abs(rain_in - 1.0) < 0.01


class TestDefaultYear:
    def test_defaults_to_2025(self):
        assert _default_year([2021, 2022, 2023, 2024, 2025]) == 2025

    def test_defaults_to_latest_when_no_2025(self):
        assert _default_year([2021, 2022, 2023]) == 2023

    def test_returns_none_for_empty(self):
        assert _default_year([]) is None


class TestExtractFieldData:
    def test_extract_fields_from_geojson(self, temp_farm_dir):
        gdf = _load_farm_boundary(temp_farm_dir)
        fields = _extract_field_data(temp_farm_dir, gdf)
        assert len(fields) == 2
        field_ids = {f["fieldId"] for f in fields}
        assert "OSM_test_001" in field_ids or "osm-test-001" in field_ids

    def test_no_weather_yields_available_years_empty(self, temp_farm_dir):
        gdf = _load_farm_boundary(temp_farm_dir)
        fields = _extract_field_data(temp_farm_dir, gdf)
        for f in fields:
            assert f["availableYears"] == []

    def test_weather_yields_available_years(self, temp_farm_dir_with_weather):
        gdf = _load_farm_boundary(temp_farm_dir_with_weather)
        fields = _extract_field_data(temp_farm_dir_with_weather, gdf)
        for f in fields:
            if f["hasWeatherData"]:
                assert 2025 in f["availableYears"]

    def test_field_colors_are_stable(self, temp_farm_dir):
        gdf = _load_farm_boundary(temp_farm_dir)
        fields1 = _extract_field_data(temp_farm_dir, gdf)
        fields2 = _extract_field_data(temp_farm_dir, gdf)
        for f1, f2 in zip(fields1, fields2):
            assert f1["color"] == f2["color"]

    def test_multipolygon_supported(self, temp_farm_dir_multipolygon):
        gdf = _load_farm_boundary(temp_farm_dir_multipolygon)
        fields = _extract_field_data(temp_farm_dir_multipolygon, gdf)
        assert len(fields) == 1
        assert len(fields[0]["mercatorPolygons"]) == 2

    def test_missing_field_json_fallback(self, temp_farm_dir_no_field_json):
        gdf = _load_farm_boundary(temp_farm_dir_no_field_json)
        fields = _extract_field_data(temp_farm_dir_no_field_json, gdf)
        assert len(fields) == 2


class TestDashboardGeneration:
    def test_generate_dashboard_creates_html(self, temp_farm_dir, mock_plotly_bundle):
        output = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
        output.close()
        try:
            result = generate_dashboard(
                farm_dir=temp_farm_dir,
                output_path=Path(output.name),
                no_basemap=True,
                allow_downloads=False,
            )
            assert result.exists()
            content = result.read_text(encoding="utf-8")
            assert "<!DOCTYPE html>" in content
            assert "Plotly" in content
        finally:
            Path(output.name).unlink(missing_ok=True)

    def test_generated_html_no_cdn_urls(self, temp_farm_dir, mock_plotly_bundle):
        output = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
        output.close()
        try:
            result = generate_dashboard(
                farm_dir=temp_farm_dir,
                output_path=Path(output.name),
                no_basemap=True,
                allow_downloads=False,
            )
            content = result.read_text(encoding="utf-8")
            forbidden_patterns = [
                'src="https://',
                'src="http://',
                'href="https://fonts.googleapis.com',
                'href="https://cdn.',
                'href="http://cdn.',
            ]
            for pattern in forbidden_patterns:
                assert pattern not in content, f"Found external reference: {pattern}"
        finally:
            Path(output.name).unlink(missing_ok=True)

    def test_dashboard_has_embedded_data(self, temp_farm_dir_with_weather, mock_plotly_bundle):
        output = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
        output.close()
        try:
            result = generate_dashboard(
                farm_dir=temp_farm_dir_with_weather,
                output_path=Path(output.name),
                no_basemap=True,
                allow_downloads=False,
            )
            content = result.read_text(encoding="utf-8")
            assert "DASHBOARD_DATA" in content
            assert '"fieldId"' in content
            assert '"farmId"' in content
            assert '"fields"' in content
            assert '"weatherByFieldYear"' in content
        finally:
            Path(output.name).unlink(missing_ok=True)

    def test_header_only_weather_no_failure(self, temp_farm_dir_header_only_weather, mock_plotly_bundle):
        output = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
        output.close()
        try:
            result = generate_dashboard(
                farm_dir=temp_farm_dir_header_only_weather,
                output_path=Path(output.name),
                no_basemap=True,
                allow_downloads=False,
            )
            content = result.read_text(encoding="utf-8")
            assert "(no data)" in content
        finally:
            Path(output.name).unlink(missing_ok=True)

    def test_no_basemap_produces_dashboard(self, temp_farm_dir, mock_plotly_bundle):
        output = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
        output.close()
        try:
            result = generate_dashboard(
                farm_dir=temp_farm_dir,
                output_path=Path(output.name),
                no_basemap=True,
                allow_downloads=False,
            )
            content = result.read_text(encoding="utf-8")
            assert "Satellite imagery unavailable" in content
        finally:
            Path(output.name).unlink(missing_ok=True)

    def test_atomic_write(self, temp_farm_dir, mock_plotly_bundle):
        output = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
        output.close()
        output_path = Path(output.name)
        try:
            result = generate_dashboard(
                farm_dir=temp_farm_dir,
                output_path=output_path,
                no_basemap=True,
                allow_downloads=False,
            )
            parent_contents = list(output_path.parent.iterdir())
            temp_files = [p for p in parent_contents if p.name.startswith("dashboard_")]
            assert len(temp_files) == 0
        finally:
            output_path.unlink(missing_ok=True)


@pytest.mark.skipif(
    not Path(
        "~/my-farm-advisor-runtime/data-pipeline/growers/"
        "northern-iowa-grower/farms/northern-iowa-grower-iowa"
    )
    .expanduser()
    .is_dir(),
    reason="Iowa fixture not available",
)
class TestIowaFixture:
    @pytest.fixture(autouse=True)
    def _mock_assets(self, mock_plotly_bundle, mock_satellite_basemap):
        pass

    def test_generate_for_iowa_fixture(self, iowa_farm_dir, tmp_path):
        output = tmp_path / "test_iowa_dashboard.html"
        result = generate_dashboard(
            farm_dir=iowa_farm_dir,
            output_path=output,
            no_basemap=True,
            allow_downloads=False,
        )
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "Grower Field Weather Dashboard" in content
        assert "DASHBOARD_DATA" in content
        assert "fieldBoundaries" not in content.lower() or "field_boundaries" not in content.lower()

    def test_iowa_dashboard_has_field_metadata(self, iowa_farm_dir, tmp_path):
        output = tmp_path / "test_iowa_meta_dashboard.html"
        result = generate_dashboard(
            farm_dir=iowa_farm_dir,
            output_path=output,
            no_basemap=True,
            allow_downloads=False,
        )
        content = result.read_text(encoding="utf-8")
        assert '"fieldId"' in content
        assert '"fieldName"' in content
        assert '"mercatorPolygons"' in content

    def test_iowa_dashboard_has_weather_data(self, iowa_farm_dir, tmp_path):
        output = tmp_path / "test_iowa_wx_dashboard.html"
        result = generate_dashboard(
            farm_dir=iowa_farm_dir,
            output_path=output,
            no_basemap=True,
            allow_downloads=False,
        )
        content = result.read_text(encoding="utf-8")
        assert '"dailyGdd"' in content
        assert '"cumulativeGdd"' in content
        assert '"dailyRainfallIn"' in content
        assert '"cumulativeRainfallIn"' in content

    def test_iowa_dashboard_defaults_to_2025(self, iowa_farm_dir, tmp_path):
        output = tmp_path / "test_iowa_default_year.html"
        generate_dashboard(
            farm_dir=iowa_farm_dir,
            output_path=output,
            no_basemap=True,
            allow_downloads=False,
        )
        content = output.read_text(encoding="utf-8")
        assert "DEFAULT_YEAR" in content
        assert "2025" in content
