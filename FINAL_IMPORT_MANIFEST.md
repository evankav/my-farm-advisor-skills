# Final Import Manifest

Finalized: 2026-04-28
Repository: `my-farm-advisor-skills`

## Imported Skills

| Skill | Destination | Source | Source Path | Ref | Source Commit | Source Status |
| --- | --- | --- | --- | --- | --- | --- |
| `my-farm-advisor` | `my-farm-advisor/` | `https://github.com/borealBytes/my-farm-advisor.git` | `skills/my-farm-advisor/` | `main` | `4a82ab779e8374035ca5e15f1cb1c0571395dc3d` | clean remote ref |
| `my-farm-breeding-trial-management` | `my-farm-breeding-trial-management/` | local worktree + `https://github.com/borealBytes/my-farm-advisor.git` baseline | `scientific-skills/breeding-trial-management/` | `feat/breeding-trial-management` | `f479f5d2d494d12c8b60fbdc338bf1219dd5a0d1` | untracked worktree base; remote baseline `main@4a82ab779e8374035ca5e15f1cb1c0571395dc3d` |
| `my-farm-qtl-analysis` | `my-farm-qtl-analysis/` | local worktree + `https://github.com/borealBytes/my-farm-advisor.git` baseline | `scientific-skills/qtl-analysis/` | `feat/qtl-analysis` | `f479f5d2d494d12c8b60fbdc338bf1219dd5a0d1` | untracked worktree base |

## Exclusions

### `my-farm-advisor`

- `.git/`
- Generated geoadmin runtime payloads including `countries.geojson`, `states_usa.geojson`, and runtime copies under `data/my-farm-advisor/shared/geoadmin/{l0_countries,l1_states,l2_counties}/`
- Generated maturity report and table artifacts under `data-pipeline/src/shared/*/{reports,tables}/`
- Repo-local CI or deployment files outside `skills/my-farm-advisor/`

### `my-farm-breeding-trial-management`

- `.git/`
- Unrelated scientific skills outside `scientific-skills/breeding-trial-management/`
- Remote flat-layout paths that would overwrite the grouped local example taxonomy

### `my-farm-qtl-analysis`

- `.git/`
- Generated `examples/**/output/` artifacts
- Generated `scripts/output/` artifacts
- Unrelated scientific skills outside `scientific-skills/qtl-analysis/`
- Remote flattening of the local grouped example taxonomy

### Repository-level forbidden content

- `superior-byte-works-wrighter`
- `superior-byte-works-google-timesfm-forecasting`
- `countries.geojson`
- `states_usa.geojson`
- `node_modules/`
- `.cache/`
- `data/`
- `.sisyphus/`

## Local Modifications

### Imported skill adjustments

- `my-farm-advisor`: preserved geoadmin metadata JSON files and downloader code while excluding generated payloads; preserved `farm_dashboard.py`, `run_farm_pipeline.py`, and `run_maturity_by_fips.py`.
- `my-farm-breeding-trial-management`: kept the local grouped worktree as the structural base; backfilled remote `README.md`, `scripts/breeding_cli.py`, and `examples/field-trial-placement/`; preserved local grouped examples and local breeding references.
- `my-farm-qtl-analysis`: kept the local grouped worktree as the structural base; backfilled remote `README.md` and `scripts/qtl_cli.py`; preserved `scripts/verify_gpu_hpc.py` and `VISUALIZATION_SUMMARY.md`; removed generated outputs after audit.

### Repository-level documentation added after import

- Root `README.md` documents the SBW dependency boundary, sibling-clone installation flow, and required SBW-first update order.
- Root `IMPORT_MANIFEST.md` and `PROVENANCE.md` record the final exclusion policy and geodata handling details.
- `my-farm-advisor/README.md` now points readers to geodata runtime guidance.
- `my-farm-advisor/docs/GEODATA.md` documents the committed metadata files, runtime destinations, and downloader commands for excluded geoadmin payloads.

## Validation Status

- `./scripts/validate.sh`: **PASS** (`38 pass, 0 warn, 0 fail`)
- Source-destination map check: **PASS** — only `my-farm-advisor/`, `my-farm-breeding-trial-management/`, and `my-farm-qtl-analysis/` are present as top-level skill directories.
- Forbidden path check: **PASS** — no forbidden SBW copies, no tracked geodata payloads, no `node_modules/`, no `.cache/`, no `data/`, and no repo-local `.sisyphus/` tree.
- Working-tree audit target: root tree must be clean after the final manifest commit, with no temporary clones, worktrees, archives, or source dumps left in the repository.

## Update Owners

| Skill / Area | Update owner | Refresh source |
| --- | --- | --- |
| `my-farm-advisor` | My Farm Advisor maintainers | `borealBytes/my-farm-advisor@main` |
| `my-farm-breeding-trial-management` | My Farm breeding maintainers | Local worktree `scientific-agent-skills-worktrees/scientific-agent-skills-breeding-trial-management` with `borealBytes/my-farm-advisor@main` as completeness baseline |
| `my-farm-qtl-analysis` | My Farm QTL maintainers | Local worktree `scientific-agent-skills-worktrees/scientific-agent-skills-qtl-analysis` with `borealBytes/my-farm-advisor@main` as completeness baseline |
| Cross-repo dependency guidance | My Farm Advisor maintainers | `superior-byte-works-skills` consumer documentation and validation rules |
