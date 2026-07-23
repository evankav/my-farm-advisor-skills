#!/usr/bin/env python3
"""Farm directory discovery and validation for the data-pipeline runtime.

Supports explicit paths, growers-dir roots, environment variables, and automatic
discovery beneath the user's home directory.
"""

from __future__ import annotations

import os
from pathlib import Path


def _expand_and_resolve(path: str | Path | None) -> Path | None:
    if path is None:
        return None
    return Path(path).expanduser().resolve(strict=False)


def _is_valid_farm_dir(farm_dir: Path) -> bool:
    """A farm directory is valid if it contains the minimum expected structure."""
    boundary = farm_dir / "boundary" / "field_boundaries.geojson"
    fields_dir = farm_dir / "fields"
    if not boundary.exists():
        return False
    if not boundary.is_file():
        return False
    if not fields_dir.is_dir():
        return False
    return True


def _discover_farms_under(root: Path) -> list[Path]:
    """Walk root looking for valid farm directories."""
    if not root.is_dir():
        return []
    farms: list[Path] = []
    for item in root.rglob("*"):
        if not item.is_dir():
            continue
        if _is_valid_farm_dir(item):
            farms.append(item)
    return farms


def _candidate_runtime_roots() -> list[Path]:
    """Return likely runtime root directories under the user's home."""
    home = Path.home()
    candidates: list[Path] = []
    patterns = [
        "my-farm-advisor-runtime",
        "my-farm-advisor-data",
        "farm-advisor-runtime",
    ]
    for name in patterns:
        candidate = home / name
        if candidate.is_dir():
            candidates.append(candidate / "data-pipeline")
    for item in home.iterdir():
        if not item.is_dir():
            continue
        if item.name.startswith("."):
            continue
        growers = item / "data-pipeline" / "growers"
        if growers.is_dir():
            candidate = item / "data-pipeline"
            if candidate not in candidates:
                candidates.append(candidate)
        elif (item / "growers").is_dir() and (item / "shared").is_dir():
            if item not in candidates:
                candidates.append(item)
    return candidates


class DiscoveryError(RuntimeError):
    """Raised when farm directory discovery or validation fails."""
    pass


def discover_farm_dir(
    *,
    farm_dir: str | Path | None = None,
    growers_dir: str | Path | None = None,
) -> Path:
    """Resolve a single farm directory using precedence rules.

    Precedence:
      1. Explicit ``--farm-dir``
      2. Explicit ``--growers-dir`` (must contain exactly one valid farm)
      3. Environment variable ``MY_FARM_ADVISOR_DATA_ROOT`` / ``DATA_PIPELINE_DATA_ROOT``
      4. Automatic discovery under ``~`` looking for likely runtime roots

    Returns:
        Path: Resolved farm directory.

    Raises:
        DiscoveryError: If no farm is found or multiple farms are found.
    """
    explicit_farm = _expand_and_resolve(farm_dir)
    if explicit_farm is not None:
        if not explicit_farm.exists():
            raise DiscoveryError(f"Farm directory does not exist: {explicit_farm}")
        if not _is_valid_farm_dir(explicit_farm):
            raise DiscoveryError(
                f"Farm directory is missing required files "
                f"(boundary/field_boundaries.geojson and fields/): {explicit_farm}"
            )
        return explicit_farm

    explicit_growers = _expand_and_resolve(growers_dir)
    if explicit_growers is not None:
        if not explicit_growers.exists():
            raise DiscoveryError(f"Growers directory does not exist: {explicit_growers}")
        farms = _discover_farms_under(explicit_growers)
        if len(farms) == 0:
            raise DiscoveryError(
                f"No valid farm directories found under growers directory: {explicit_growers}"
            )
        if len(farms) > 1:
            raise DiscoveryError(
                f"Multiple farms found under {explicit_growers}. "
                f"Use --farm-dir to select one:\n"
                + "\n".join(f"  - {f}" for f in sorted(farms))
            )
        return farms[0]

    env_root = os.environ.get("MY_FARM_ADVISOR_DATA_ROOT") or os.environ.get(
        "DATA_PIPELINE_DATA_ROOT"
    )
    if env_root:
        env_path = _expand_and_resolve(env_root)
        if env_path is not None:
            if _is_valid_farm_dir(env_path):
                return env_path
            runtime_base = (
                env_path / "data-pipeline"
                if not (env_path / "growers").exists()
                else env_path
            )
            farms = _discover_farms_under(runtime_base)
            if len(farms) == 1:
                return farms[0]
            if len(farms) > 1:
                raise DiscoveryError(
                    f"Multiple farms found under runtime root {runtime_base} from "
                    f"environment. Use --farm-dir to select one:\n"
                    + "\n".join(f"  - {f}" for f in sorted(farms))
                )

    candidates = _candidate_runtime_roots()
    all_farms: list[Path] = []
    for root in candidates:
        all_farms.extend(_discover_farms_under(root))

    if len(all_farms) == 0:
        try:
            from paths import DATA_ROOT

            if DATA_ROOT and DATA_ROOT != Path("."):
                farms = _discover_farms_under(DATA_ROOT)
                if len(farms) == 1:
                    return farms[0]
                if len(farms) > 1:
                    raise DiscoveryError(
                        f"Multiple farms found under DATA_ROOT {DATA_ROOT}. "
                        f"Use --farm-dir to select one:\n"
                        + "\n".join(f"  - {f}" for f in sorted(farms))
                    )
        except Exception:
            pass
        raise DiscoveryError(
            "No farm directory found.\n"
            "Suggestions:\n"
            "  - Use --farm-dir to specify the farm directory directly.\n"
            "  - Use --growers-dir to specify the growers root.\n"
            "  - Set MY_FARM_ADVISOR_DATA_ROOT or DATA_PIPELINE_DATA_ROOT "
            "environment variable.\n"
            "  - Ensure a valid farm exists under "
            "~/my-farm-advisor-runtime/data-pipeline/growers/<grower>/farms/<farm>"
        )

    if len(all_farms) == 1:
        return all_farms[0]

    raise DiscoveryError(
        "Multiple farms found during auto-discovery. "
        "Use --farm-dir to select one:\n"
        + "\n".join(f"  - {f}" for f in sorted(all_farms))
    )


def extract_grower_and_farm_slugs(farm_dir: Path) -> tuple[str, str]:
    """Infer grower_slug and farm_slug from a canonical farm directory path.

    Expected structure: .../growers/<grower-slug>/farms/<farm-slug>
    """
    parts = farm_dir.parts
    try:
        growers_idx = parts.index("growers")
        farms_idx = parts.index("farms", growers_idx)
        grower_slug = parts[growers_idx + 1]
        farm_slug = parts[farms_idx + 1]
        return (grower_slug, farm_slug)
    except (ValueError, IndexError):
        return (farm_dir.parent.parent.name, farm_dir.name)
