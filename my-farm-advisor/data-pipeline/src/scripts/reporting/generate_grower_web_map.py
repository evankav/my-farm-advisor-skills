#!/usr/bin/env python3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportGeneralTypeIssues=false
"""Generate a lightweight, interactive HTML web map for each grower.

Discovers all farms and fields under a grower, reads their boundary GeoJSON,
and builds a single self-contained HTML file with Leaflet.js.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path

_LOCAL_LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(_LOCAL_LIB))

from runtime_paths import resolve_runtime_paths  # noqa: E402

_RUNTIME_PATHS = resolve_runtime_paths()
_REPO = _RUNTIME_PATHS.runtime_base
_SCRIPTS = _RUNTIME_PATHS.runtime_scripts
_LIB = _RUNTIME_PATHS.runtime_scripts / "lib"
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_LIB))

from paths import grower_dir  # noqa: E402

_DEFAULT_GROWER = os.environ.get("AG_GROWER_SLUG", "default-grower")

# Distinct fill colors for field polygons (Leaflet-compatible hex)
_COLOR_CYCLE = [
    "#3388ff",
    "#e31a1c",
    "#33a02c",
    "#ff7f00",
    "#6a3d9a",
    "#b15928",
    "#1f78b4",
    "#fb9a99",
    "#b2df8a",
    "#fdbf6f",
]


def _discover_fields(grower_slug: str) -> list[dict]:
    """Walk the canonical tree and return a list of field dicts with metadata + geojson."""
    base = grower_dir(grower_slug)
    fields: list[dict] = []
    farms_dir = base / "farms"
    if not farms_dir.exists():
        return fields

    for farm_path in sorted(farms_dir.iterdir()):
        if not farm_path.is_dir():
            continue
        farm_slug = farm_path.name
        fields_dir = farm_path / "fields"
        if not fields_dir.exists():
            continue

        for field_path in sorted(fields_dir.iterdir()):
            if not field_path.is_dir():
                continue
            field_slug = field_path.name
            field_json = field_path / "field.json"
            boundary_geojson = field_path / "boundary" / "field_boundary.geojson"

            meta = {}
            if field_json.exists():
                try:
                    meta = json.loads(field_json.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    pass

            geojson = None
            if boundary_geojson.exists():
                try:
                    geojson = json.loads(boundary_geojson.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    pass

            if geojson is None:
                continue

            # Merge properties from GeoJSON features with metadata
            props = {}
            if isinstance(geojson, dict) and "features" in geojson:
                for feat in geojson["features"]:
                    if isinstance(feat, dict) and "properties" in feat:
                        props.update(feat["properties"])

            fields.append(
                {
                    "grower_slug": grower_slug,
                    "farm_slug": farm_slug,
                    "field_slug": field_slug,
                    "display_name": meta.get("display_name", field_slug),
                    "field_id": meta.get("field_id", field_slug),
                    "area_acres": props.get("area_acres"),
                    "geojson": geojson,
                }
            )

    return fields


def _build_geojson_feature_collection(fields: list[dict]) -> dict:
    features: list[dict] = []
    for idx, f in enumerate(fields):
        geo = f["geojson"]
        if isinstance(geo, dict) and "features" in geo:
            for feat in geo["features"]:
                if not isinstance(feat, dict):
                    continue
                # Inject/overwrite properties so the popup is self-describing
                props = dict(feat.get("properties", {}))
                props.update(
                    {
                        "_grower": f["grower_slug"],
                        "_farm": f["farm_slug"],
                        "_field": f["display_name"],
                        "_field_id": f["field_id"],
                        "_area_acres": f["area_acres"],
                        "_color_idx": idx,
                    }
                )
                features.append(
                    {
                        "type": "Feature",
                        "geometry": feat.get("geometry"),
                        "properties": props,
                    }
                )
        elif isinstance(geo, dict) and "geometry" in geo:
            props = dict(geo.get("properties", {}))
            props.update(
                {
                    "_grower": f["grower_slug"],
                    "_farm": f["farm_slug"],
                    "_field": f["display_name"],
                    "_field_id": f["field_id"],
                    "_area_acres": f["area_acres"],
                    "_color_idx": idx,
                }
            )
            features.append(
                {"type": "Feature", "geometry": geo["geometry"], "properties": props}
            )

    return {"type": "FeatureCollection", "features": features}


def _build_sidebar_items(fields: list[dict]) -> str:
    items: list[str] = []
    for idx, f in enumerate(fields):
        color = _COLOR_CYCLE[idx % len(_COLOR_CYCLE)]
        area_str = f"{f['area_acres']:.1f} ac" if f["area_acres"] is not None else ""
        items.append(
            f"""\
            <div class="field-item" data-idx="{idx}">
              <span class="swatch" style="background:{color}"></span>
              <div class="field-info">
                <div class="field-name">{f['display_name']}</div>
                <div class="field-meta">{f['farm_slug']} {area_str}</div>
              </div>
              <button class="zoom-btn" data-idx="{idx}">Zoom</button>
            </div>
            """
        )
    return "\n".join(items)


def _build_html(grower_slug: str, fields: list[dict]) -> str:
    fc = _build_geojson_feature_collection(fields)
    geojson_str = json.dumps(fc)
    sidebar_html = _build_sidebar_items(fields)
    colors_json = json.dumps(_COLOR_CYCLE)
    n_fields = len(fields)
    n_farms = len({f["farm_slug"] for f in fields})

    return textwrap.dedent(
        f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>{grower_slug} — Grower Web Map</title>
          <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
                integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
                crossorigin=""/>
          <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
                  integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
                  crossorigin=""></script>
          <style>
            html, body {{ margin: 0; padding: 0; height: 100%; font-family: system-ui, -apple-system, sans-serif; }}
            #container {{ display: flex; height: 100vh; width: 100vw; }}
            #sidebar {{
              width: 280px; min-width: 220px; max-width: 320px;
              background: #f8fafc; border-right: 1px solid #e2e8f0;
              display: flex; flex-direction: column;
            }}
            #sidebar header {{
              padding: 1rem; border-bottom: 1px solid #e2e8f0;
              background: #fff;
            }}
            #sidebar header h1 {{ margin: 0; font-size: 1.1rem; color: #0f172a; }}
            #sidebar header p {{ margin: 0.25rem 0 0; font-size: 0.8rem; color: #64748b; }}
            #field-list {{ flex: 1; overflow-y: auto; padding: 0.5rem; }}
            .field-item {{
              display: flex; align-items: center; gap: 0.6rem;
              padding: 0.6rem; margin-bottom: 0.4rem;
              background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
              cursor: pointer; transition: box-shadow 0.15s;
            }}
            .field-item:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-color: #cbd5e1; }}
            .swatch {{ width: 14px; height: 14px; border-radius: 50%; border: 2px solid #fff; box-shadow: 0 0 0 1px #cbd5e1; flex-shrink: 0; }}
            .field-info {{ flex: 1; min-width: 0; }}
            .field-name {{ font-size: 0.85rem; font-weight: 600; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .field-meta {{ font-size: 0.75rem; color: #64748b; }}
            .zoom-btn {{
              font-size: 0.7rem; padding: 0.25rem 0.5rem;
              border: 1px solid #cbd5e1; border-radius: 6px;
              background: #fff; color: #334155; cursor: pointer;
            }}
            .zoom-btn:hover {{ background: #f1f5f9; }}
            #map {{ flex: 1; height: 100%; }}
            .popup-row {{ margin: 0.15rem 0; font-size: 0.85rem; }}
            .popup-label {{ font-weight: 600; color: #334155; }}
            @media (max-width: 640px) {{
              #sidebar {{ width: 100%; max-width: none; height: 35vh; border-right: none; border-bottom: 1px solid #e2e8f0; }}
              #container {{ flex-direction: column; }}
              #map {{ height: 65vh; }}
            }}
          </style>
        </head>
        <body>
          <div id="container">
            <div id="sidebar">
              <header>
                <h1>{grower_slug}</h1>
                <p>{n_farms} farm(s) &middot; {n_fields} field(s)</p>
              </header>
              <div id="field-list">
                {sidebar_html}
              </div>
            </div>
            <div id="map"></div>
          </div>
          <script>
            (function() {{
              var colors = {colors_json};
              var geojsonData = {geojson_str};

              var map = L.map('map').setView([40, -95], 5);

              L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                maxZoom: 19,
                attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
              }}).addTo(map);

              var layerGroup = L.featureGroup().addTo(map);
              var layersByIdx = {{}};

              function styleFeature(feature) {{
                var idx = feature.properties._color_idx || 0;
                var color = colors[idx % colors.length];
                return {{
                  color: color,
                  weight: 2.5,
                  opacity: 0.9,
                  fillColor: color,
                  fillOpacity: 0.25
                }};
              }}

              function onEachFeature(feature, layer) {{
                var p = feature.properties;
                var area = p._area_acres != null ? parseFloat(p._area_acres).toFixed(1) + ' ac' : '—';
                var popupHtml = '<div class="popup-row"><span class="popup-label">Grower:</span> ' + (p._grower || '—') + '</div>' +
                                '<div class="popup-row"><span class="popup-label">Farm:</span> ' + (p._farm || '—') + '</div>' +
                                '<div class="popup-row"><span class="popup-label">Field:</span> ' + (p._field || '—') + '</div>' +
                                '<div class="popup-row"><span class="popup-label">Field ID:</span> ' + (p._field_id || '—') + '</div>' +
                                '<div class="popup-row"><span class="popup-label">Area:</span> ' + area + '</div>';
                layer.bindPopup(popupHtml);
                var idx = p._color_idx || 0;
                if (!layersByIdx[idx]) layersByIdx[idx] = [];
                layersByIdx[idx].push(layer);
              }}

              L.geoJSON(geojsonData, {{
                style: styleFeature,
                onEachFeature: onEachFeature
              }}).addTo(layerGroup);

              if (layerGroup.getLayers().length > 0) {{
                map.fitBounds(layerGroup.getBounds(), {{ padding: [40, 40] }});
              }}

              function zoomToField(idx) {{
                var layers = layersByIdx[idx];
                if (!layers || !layers.length) return;
                var group = L.featureGroup(layers);
                map.fitBounds(group.getBounds(), {{ padding: [60, 60], maxZoom: 16 }});
                layers.forEach(function(layer) {{ layer.openPopup(); }});
              }}

              document.querySelectorAll('.field-item').forEach(function(item) {{
                var idx = parseInt(item.getAttribute('data-idx'), 10);
                item.addEventListener('click', function() {{ zoomToField(idx); }});
              }});

              document.querySelectorAll('.zoom-btn').forEach(function(btn) {{
                var idx = parseInt(btn.getAttribute('data-idx'), 10);
                btn.addEventListener('click', function(e) {{
                  e.stopPropagation();
                  zoomToField(idx);
                }});
              }});
            }})();
          </script>
        </body>
        </html>
        """
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a grower-level interactive web map.")
    parser.add_argument(
        "--grower-slug",
        default=_DEFAULT_GROWER,
        help="Grower slug (default: AG_GROWER_SLUG env or 'default-grower').",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Override output directory (default: growers/<grower>/derived/reports).",
    )
    args = parser.parse_args()

    grower_slug = args.grower_slug
    print(f"Generating web map for grower: {grower_slug}")

    fields = _discover_fields(grower_slug)
    if not fields:
        print("ERROR: No fields found for this grower.")
        sys.exit(1)

    print(f"  Discovered {len(fields)} field(s) across {len({f['farm_slug'] for f in fields})} farm(s)")

    html = _build_html(grower_slug, fields)

    if args.output_dir:
        out_dir = Path(args.output_dir)
    else:
        out_dir = grower_dir(grower_slug) / "derived" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{grower_slug}_web_map.html"
    out_path.write_text(html, encoding="utf-8")

    size_kb = out_path.stat().st_size / 1024
    print(f"  Saved → {out_path}")
    print(f"  Size: {size_kb:.1f} KB")
    print("Done.")


if __name__ == "__main__":
    main()
