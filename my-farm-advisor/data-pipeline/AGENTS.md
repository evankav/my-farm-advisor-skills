# Local Instructions

## Purpose

This folder owns the deterministic data pipeline that copies baseline `src/` files into live My Farm Advisor runtime storage and runs farm data, reporting, and poster scripts.

## Safe edit scope

Edits should stay in this folder and its children unless the user explicitly asks for a broader skill change. Do not change parent `SKILL.md`, sibling workflows, or root policy from a subskill task unless explicitly requested.

## Read nearby docs first

Read `README.md` first. Review `scripts/install.sh`, `src/scripts/bootstrap_runtime.py`, and `src/scripts/run_farm_pipeline.py` before changing runtime or pipeline behavior. Read `../data-sources/INDEX.md` for related rebuild and reporting workflows.

## Local workflow notes

- Keep this skill tiny and operational: copy baseline files from `src/` into live storage, preserve live data across reboot or redeploy, and use auditable `rsync` commands.
- Live data wins unless the user explicitly runs an upgrade workflow.
- Runtime data root resolution stays: `DATA_PIPELINE_DATA_ROOT`, then `/data/workspace/data/my-farm-advisor`, then checkout-relative `data/my-farm-advisor`.
- Safe data seeding uses `rsync -r --no-times --ignore-existing` and must not overwrite or delete existing files.
- Upgrade data seeding uses `rsync -r --no-times --checksum` and must not delete existing files.
- Keep `src/` shaped like the canonical runtime tree with `growers/`, `shared/`, and `scripts/`.

## Local validation

For runtime setup changes, run `./scripts/install.sh` when dependencies are available. For pipeline changes, run `python src/scripts/run_farm_pipeline.py` with a small demo farm. Otherwise run `./scripts/validate.sh` from the repository root after structural changes.

## Local-delta-only reminder

This nested AGENTS.md only records instructions that differ from the parent or root files. Do not duplicate root-wide asset, vendor, or validation policy here except this pointer to `../../AGENTS.md`.
