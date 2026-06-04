# Import Manifest

This manifest tracks planned and completed imports for `my-farm-advisor-skills`. Each entry must retain the full provenance field set even before import execution.

## my-farm-advisor

- source_repo: https://github.com/borealBytes/my-farm-advisor.git
- source_local_path: N/A
- source_ref: main
- source_commit: 4a82ab779e8374035ca5e15f1cb1c0571395dc3d
- source_status: clean remote ref
- source_path: skills/my-farm-advisor/
- destination_path: my-farm-advisor/
- import_date: 2026-04-28
- exclusions: `.git/`; `data-pipeline/src/shared/geoadmin/l0_countries/countries.geojson`; `data-pipeline/src/shared/geoadmin/l1_states/states_usa.geojson`; generated maturity report/table artifacts under `data-pipeline/src/shared/*/{reports,tables}/`; any repo-local CI or deployment files outside `skills/my-farm-advisor/`
- local_modifications: Imported `skills/my-farm-advisor/` into `my-farm-advisor/` and intentionally omitted the two generated geoadmin GeoJSON payloads plus generated maturity report/table artifacts while preserving metadata JSON files plus `download_geoadmin.py`, `farm_dashboard.py`, `run_farm_pipeline.py`, and `run_maturity_by_fips.py`.
- update_procedure: Run `git ls-remote https://github.com/borealBytes/my-farm-advisor.git refs/heads/main`, confirm the SHA, clone or fetch the repo, copy only `skills/my-farm-advisor/` into `my-farm-advisor/`, exclude `data-pipeline/src/shared/geoadmin/l0_countries/countries.geojson`, `data-pipeline/src/shared/geoadmin/l1_states/states_usa.geojson`, and generated maturity report/table artifacts under `data-pipeline/src/shared/*/{reports,tables}/`, rerun `./scripts/validate.sh`, and refresh the QA evidence plus provenance fields in the same commit.

## my-farm-breeding-trial-management

- source_repo: https://github.com/borealBytes/my-farm-advisor.git
- source_local_path: /media/clay/Data/dev/scientific-agent-skills-worktrees/scientific-agent-skills-breeding-trial-management
- source_ref: feat/breeding-trial-management
- source_commit: f479f5d2d494d12c8b60fbdc338bf1219dd5a0d1
- source_status: untracked worktree: scientific-skills/breeding-trial-management/
- source_path: scientific-skills/breeding-trial-management/
- destination_path: my-farm-breeding-trial-management/
- import_date: 2026-04-28
- remote_baseline_ref: main
- remote_baseline_commit: 4a82ab779e8374035ca5e15f1cb1c0571395dc3d
- remote_baseline_path: skills/my-farm-breeding-trial-management/
- exclusions: `.git/`; any unrelated scientific skills outside `scientific-skills/breeding-trial-management/`; remote flat-layout paths that would overwrite the grouped local example taxonomy
- local_modifications: Copied the local untracked skill tree as the structural base; added root `README.md` from the remote skill with grouped-path adjustments; backfilled remote-only `scripts/breeding_cli.py` and `examples/field-trial-placement/`; merged remote unified-CLI/tool-selection documentation into local `SKILL.md` while preserving local grouped examples and local `references/bms-api.md` + `references/breedbase-api.md`.
- update_procedure: Re-run `git branch --show-current`, `git rev-parse HEAD`, and `git status --short` in `/media/clay/Data/dev/scientific-agent-skills-worktrees/scientific-agent-skills-breeding-trial-management`; copy only `scientific-skills/breeding-trial-management/` into `my-farm-breeding-trial-management/`; resolve `https://github.com/borealBytes/my-farm-advisor.git` `main` to a commit SHA; then re-apply the remote completeness backfill for `README.md`, `scripts/breeding_cli.py`, and `examples/field-trial-placement/` without replacing the grouped local taxonomy or adjusted reference files.

## my-farm-qtl-analysis

- source_repo: https://github.com/borealBytes/my-farm-advisor.git
- source_local_path: /media/clay/Data/dev/scientific-agent-skills-worktrees/scientific-agent-skills-qtl-analysis
- source_ref: feat/qtl-analysis
- source_commit: f479f5d2d494d12c8b60fbdc338bf1219dd5a0d1
- source_status: untracked worktree: scientific-skills/qtl-analysis/
- source_path: scientific-skills/qtl-analysis/
- destination_path: my-farm-qtl-analysis/
- import_date: 2026-04-28
- exclusions: `.git/`; generated `examples/**/output/` artifacts; generated `scripts/output/` artifacts; no unrelated scientific skills outside `scientific-skills/qtl-analysis/`; no remote flattening of the local grouped example taxonomy
- local_modifications: Imported the local grouped example layout as the structural base, backfilled remote-only `README.md` and `scripts/qtl_cli.py`, merged richer remote SKILL sections without changing example-first behavior, normalized stale path assumptions to `my-farm-qtl-analysis/`, preserved `scripts/verify_gpu_hpc.py` and `VISUALIZATION_SUMMARY.md`, and removed generated outputs after asset audit. No new LFS-tracked assets were required.
- update_procedure: Re-run `GIT_MASTER=1 git ls-remote https://github.com/borealBytes/my-farm-advisor.git refs/heads/main`, capture the resolved baseline SHA for `skills/my-farm-qtl-analysis`, rerun `GIT_MASTER=1 git branch --show-current`, `GIT_MASTER=1 git rev-parse HEAD`, and `GIT_MASTER=1 git status --short` in the local worktree, copy only `scientific-skills/qtl-analysis/`, re-apply the remote backfill files and grouped-path normalization, repeat the asset audit, and refresh this manifest plus `my-farm-qtl-analysis/PROVENANCE.md` in the same commit.

## Forbidden Imports

The following old My Farm Advisor Superior Byteworks skill copies are explicitly excluded from this repository. They are superseded by canonical skills maintained in `superior-byte-works-skills` and must not be imported here.

- `superior-byte-works-wrighter` — excluded, superseded by the canonical Wrighter delivery in `superior-byte-works-skills`
- `superior-byte-works-google-timesfm-forecasting` — excluded, superseded by the Google-approved TimesFM forecasting skill in `superior-byte-works-skills`
