# Local Instructions

## Purpose

This folder owns the Assignment 2 field-level EDA subskill. It compares field boundaries, CDL/cropland data, and weather across three growers (Illinois, Iowa, Nebraska) using static matplotlib/seaborn visualizations.

## Safe edit scope

Edits should stay in this folder and its children unless the user explicitly asks for a broader skill change. Do not change parent `SKILL.md`, sibling EDA workflows, or root policy from a subskill task unless explicitly requested.

## Read nearby docs first

Read `GUIDE.md` first, then `scripts/eda_assignment2.py`. If routing context is needed, read `../INDEX.md` and `../../SKILL.md`.

## Local validation

```bash
export DATA_PIPELINE_DATA_ROOT=$HOME/my-farm-advisor-runtime
export DATA_PIPELINE_VENV_DIR="${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv"
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_VENV_DIR}/bin/python" \
  /home/coder/.config/opencode/skills/my-farm-advisor/eda/eda-assignment-2/scripts/eda_assignment2.py
```

Output PNGs land at `${DATA_PIPELINE_DATA_ROOT}/data-pipeline/eda/eda-assignment-2/output/`.

## Runtime contract

- `DATA_PIPELINE_DATA_ROOT` is required.
- The script reads from the canonical grower tree under `${DATA_PIPELINE_DATA_ROOT}/data-pipeline/growers/`.
- Weather data uses the farm-level aggregate CSV (3 of 10 fields for IL/IA, 10 of 10 for NE).
- CDL data uses per-farm full-composition and rotation CSVs.

## Local-delta-only reminder

This nested AGENTS.md only records instructions that differ from the parent or root files. Do not duplicate root-wide asset, vendor, or validation policy here except this pointer to `../../../AGENTS.md`.
