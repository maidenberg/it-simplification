# Milestone 3C.2 — External Configuration and Real-Pair Acceptance: Notes

Note: This document records the original Milestone 3C.2 implementation and
validation activities. It is retained as historical project documentation and
may not reflect the current active pipeline architecture.

## Goal
Let an operator process a new weekly snapshot workbook with **no Python code
changes** by externalising runtime configuration, and prove the end-to-end runner
with a genuinely changed previous/current snapshot pair.

## Files added / changed
Added:
- `config/weekly_snapshot.json` — external runtime configuration.
- `scripts/config_loader.py` — load/validate/merge configuration into `RunnerConfig`.
- `scripts/test_config_loader.py` — configuration tests + real-pair acceptance test.
- `docs/3c2-external-config-notes.md` — this note.

Changed:
- `scripts/run_weekly_snapshot.py` — added `--config` / `--worksheet` CLI args and
  configuration-driven `main()`; `run(config)` unchanged in behaviour.
- `scripts/README.md` — external configuration + first-baseline documentation.

Unchanged pipeline modules (verified by golden + real-pair tests):
- `scripts/compare_snapshots.py` (2A snapshot extraction, 2B–2F comparison,
  delta detection, movement classification, aggregation, top movers).
- `scripts/executive_summary.py` (3A executive summary, 3B key movements).
No business rules were modified.

## Configuration schema
`config/weekly_snapshot.json` (all keys optional; unknown keys rejected):

| Key                   | Type          | Meaning                                   |
|-----------------------|---------------|-------------------------------------------|
| `snapshot_worksheet`  | string        | Worksheet the runner reads per workbook.  |
| `outputs_directory`   | string (path) | Per-run outputs and manifests.            |

Paths may be repository-relative (resolved against the repo root) or absolute.

## Configuration precedence
Highest to lowest:
1. CLI override (`--worksheet`, and `--config` to select the file).
2. External configuration file.
3. Built-in `RunnerConfig` defaults.

`--config PATH` requires the file to exist and be valid. With no `--config`, the
default `config/weekly_snapshot.json` is applied when present; otherwise defaults
apply. Backward compatibility: `python scripts/run_weekly_snapshot.py` with no
flags behaves as before.

## Validation behaviour
`config_loader` rejects, with clear messages and before any analysis:
- a missing explicitly-requested config file,
- malformed JSON,
- a top-level value that is not a JSON object,
- unknown keys (lists the offending keys),
- wrong value types (strings for names/paths; list-of-strings for extensions),
- an empty `--worksheet` override.

A configuration failure never archives the incoming workbook and never updates the
baseline state.

## Validation

The active weekly snapshot pipeline was executed successfully after Phase 6
simplification changes. The pipeline successfully generated:

- analysis.json
- leadership_insights.txt
- risks_watchouts.txt
- leadership_email.txt

Validation confirmed that removal of the retired workbook-discovery and
baseline-state workflows did not affect leadership output generation.

## Remaining assumptions
1. **Worksheet name per workbook.** Each weekly workbook is assumed to contain a
   worksheet whose name matches `snapshot_worksheet`. This is now operator-settable
   via config/CLI; it is still not auto-detected (no fuzzy matching), by design.
2. Snapshot comparison is performed using the latest two snapshot worksheets
   within the Weekly snapshots workbook. The active runner identifies the most
   recent worksheet pair and compares them directly.
3. The **acceptance pair reuses the sample data's two worksheets**; a real future
   weekly workbook pair was not available in the repository to test against.
