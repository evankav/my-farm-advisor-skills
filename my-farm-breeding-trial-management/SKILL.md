<!-- Copyright 2026 Clayton Young (borealBytes / Superior Byte Works, LLC) -->
<!-- Licensed under the Apache License, Version 2.0. -->

---
name: breeding-trial-management
description: >
  Breeding trial management toolkit for design, fieldbook generation, germplasm workflows,
  selection, and crossing decisions. Complements qtl-analysis for end-to-end breeding genomics.
allowed-tools: Read Write Edit Bash
license: Apache-2.0
metadata:
  author: Clayton Young (borealBytes / Superior Byte Works, LLC)
  version: "0.1.0"
  category: breeding-genomics
---

# Breeding Trial Management

## Overview

This skill handles breeding operations around trial execution and decision support:
- Trial design planning
- Fieldbook preparation
- Germplasm tracking
- Selection and crossing workflows
- Early-stage breeding simulation examples for planning future cycle decisions

## Installation

```bash
python scripts/check_system.py
```

## Unified CLI

```bash
python scripts/breeding_cli.py design --help
python scripts/breeding_cli.py fieldbook --help
python scripts/breeding_cli.py germplasm --help
python scripts/breeding_cli.py select --help
python scripts/breeding_cli.py cross --help
```

## Tool Selection Guide

- Use `design` for RCBD/alpha-lattice/augmented planning tasks.
- Use `fieldbook` to generate plot sheets and labels.
- Use `germplasm` for accession list and inventory operations.
- Use `select` for ranking and shortlist generation.
- Use `cross` for mate pairing and crossing plan scaffolds.

## How To Use This Skill

```bash
cd examples/design/rcbd-design
python run_rcbd.py
```

Pick the workflow area that matches the task, move into that example directory, and run the
example script directly. These examples are the main starting point for adapting the skill to a
new breeding program.

## Workflow Areas

- `design/`: trial layout planning and field design examples
  - `examples/design/rcbd-design/`
  - `examples/design/alpha-lattice/`
  - `examples/design/augmented-design/`

- `fieldbook/`: field-ready records, imports, and sync workflows
  - `examples/fieldbook/field-book/`
  - `examples/fieldbook/data-import/`
  - `examples/fieldbook/iot-field-sync/`
  - `examples/field-trial-placement/` (field-boundary-aware placement backfill)

- `germplasm/`: accession, pedigree, and mock breeding-system integrations
  - `examples/germplasm/breedbase-client/`
  - `examples/germplasm/bms-client/`
  - `examples/germplasm/pedigree-management/`

- `select/`: ranking, index construction, and compact simulation previews
  - `examples/select/selection-index/`
  - `examples/select/breeding-value-ranking/`
  - `examples/select/breeding-simulation-simple-cycle/`

- `cross/`: cross planning and parent pairing workflows
  - `examples/cross/crossing-plan/`

## Support Scripts

- `scripts/check_system.py`: lightweight environment and dependency check
- `scripts/breeding_cli.py`: unified CLI scaffold for design, fieldbook, germplasm, selection, and crossing workflows
- `references/`: short notes on design theory and mock integration patterns
