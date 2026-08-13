#!/usr/bin/env python3
"""Step 3 — Prepare and Finalise Dashboard Data.

Reads pipeline outputs for all three growers, runs the data-readiness
checklist, and exports six clean summary CSV files to
``shared/dashboard/`` under the runtime tree.

Usage:
    export DATA_PIPELINE_DATA_ROOT=/absolute/path/to/my-farm-advisor-runtime
    python prepare_dashboard_data.py
    python prepare_dashboard_data.py --output-dir /custom/output

Output:
    shared/dashboard/
      dashboard_field_summary.csv
      dashboard_weather_summary.csv
      dashboard_crop_summary.csv
      dashboard_rotation_summary.csv
      dashboard_vegetation_summary.csv
      dashboard_data_coverage.csv
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPT_DIR.parent
sys.path.insert(0, str(_SRC_DIR))

from lib.dashboard_config import GROWER_ORDER, SUMMARY_FILES
from lib.dashboard_data import (
    _dashboard_output_dir,
    build_coverage_summary,
    build_crop_summary,
    build_field_summary,
    build_rotation_summary,
    build_soil_summary,
    build_vegetation_summary,
    build_weather_summary,
    run_data_readiness_checklist,
)


def main() -> int:
    data_root_raw = os.environ.get("DATA_PIPELINE_DATA_ROOT")
    if not data_root_raw:
        print("ERROR: DATA_PIPELINE_DATA_ROOT is not set.", file=sys.stderr)
        print(
            "Export it to point at the pipeline runtime root and re-run.",
            file=sys.stderr,
        )
        return 1

    data_root = Path(data_root_raw).expanduser().resolve()
    if not data_root.is_dir():
        print(f"ERROR: DATA_PIPELINE_DATA_ROOT does not exist: {data_root}",
              file=sys.stderr)
        return 1

    pipeline_root = data_root / "data-pipeline"
    if not pipeline_root.is_dir():
        print(f"ERROR: data-pipeline directory not found under {data_root}",
              file=sys.stderr)
        print("Run my-farm-advisor/data-pipeline/scripts/install.sh first.",
              file=sys.stderr)
        return 1

    print("=" * 64)
    print("Step 3 — Data Readiness Checklist")
    print("=" * 64)
    print(f"  Runtime root: {data_root}")

    print("\n[1] Running validation...")
    report = run_data_readiness_checklist(data_root)

    print(f"\n  State boundaries: {'OK' if report['state_boundaries_exists'] else 'MISSING'}")

    all_ok = True
    for label in GROWER_ORDER:
        g = report["growers"][label]
        b = g["boundaries"]
        w = g["weather"]
        c = g["cdl"]
        n = g["ndvi"]
        s = g.get("soil", {})
        print(f"\n  ── {label} ──")
        print(f"    Boundaries: {b['field_count']} fields {'✓' if b['exists'] else '✗ MISSING'}"
              f" (null area_acres={b.get('null_area_acres', '?')})")
        print(f"    CDL:        {c['field_count']} fields, years={c.get('years_covered', '?')}"
              f" {'✓' if c['exists'] else '✗ MISSING'}")
        print(f"    Weather:    {w['field_count']} fields"
              f" {'✓' if w['exists'] else '✗ MISSING'}")
        print(f"    NDVI:       {n['field_count']} field-year(s) confirmed")
        for f in n.get("fields", []):
            status = f"✓ {f['scene_count']} scenes" if not f["error"] else f"✗ {f['error']}"
            print(f"      {f['field_id']} ({f['year']}): {status}")
        print(f"    SSURGO:     {s.get('field_count', 0)} fields"
              f" {'✓' if s.get('exists') else '✗ MISSING'}"
              f" cols={s.get('available_columns', [])}")

        if g["issues"]:
            all_ok = False
            for issue in g["issues"]:
                print(f"    ⚠  {issue}")

    print(f"\n  ID consistency: {'✓' if report['id_consistency']['consistent'] else '✗ ISSUES'}")
    for issue in report["id_consistency"].get("issues", []):
        print(f"    ⚠  {issue}")

    print(f"\n  Overall ready: {'YES' if report['overall_ready'] else 'NO — see issues above'}")

    print("\n[2] Building summary datasets...")
    output_dir = _dashboard_output_dir(data_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    builders = {
        "field": build_field_summary,
        "weather": build_weather_summary,
        "crop": build_crop_summary,
        "rotation": build_rotation_summary,
        "vegetation": build_vegetation_summary,
        "coverage": build_coverage_summary,
        "soil": build_soil_summary,
    }

    created: list[str] = []
    for key, filename in SUMMARY_FILES.items():
        builder = builders[key]
        try:
            df = builder(data_root)
        except Exception as exc:
            print(f"  ✗ {filename}: {exc}")
            continue

        out_path = output_dir / filename
        df.to_csv(out_path, index=False)
        size_kb = out_path.stat().st_size / 1024
        print(f"  ✓ {filename}  ({len(df)} rows, {size_kb:.1f} KB)")
        created.append(str(out_path))

    print(f"\n[3] Writing validation report...")
    report_path = output_dir / "dashboard_data_readiness_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  ✓ {report_path}")

    print(f"\n{'=' * 64}")
    print("Phase A complete.")
    print(f"  Output: {output_dir}")
    print(f"  Files:  {len(created)} summary CSVs + readiness report")
    if not report["overall_ready"]:
        print("\n  ⚠  WARNING: Data readiness issues found. Review the report")
        print("     before proceeding to Step 4 (Build the Dashboard).")

    return 0 if report["overall_ready"] else 2


if __name__ == "__main__":
    sys.exit(main())
