# Milestone 3C.1 — Drop-in Snapshot Runner: Implementation Note

## Goal
Let an operator drop one new weekly Excel workbook into `data/incoming/` and run a
single command that executes the existing, unchanged 2A–3B pipeline against the
current workbook versus the previous successful workbook.

## Existing components reused (unchanged)
All analysis and reporting logic is invoked as-is. No signatures or bodies change.

Analysis (`scripts/compare_snapshots.py`):
- `load_snapshot(filepath, sheet_name)` — 2A: reads one worksheet into a DataFrame.
- `extract_vendor_data(snapshot_df)` — 2A: locates vendor blocks, cleans, dedupes.
- `compare_snapshots(previous_df, current_df)` — 2B–2F: contract presence, costout
  delta, movement classification, portfolio aggregation, top movers. Returns the
  single result dict consumed by reporting.

Reporting (`scripts/executive_summary.py`):
- `generate_executive_summary(analysis)` — 3A.
- `generate_key_movements(analysis)` — 3B.

The runner calls these in the established order:
`load_snapshot -> extract_vendor_data` (per workbook) ->
`compare_snapshots(previous, current)` -> `generate_executive_summary` +
`generate_key_movements`. The runner performs **no** calculations or formatting of
its own.

## Key coupling identified
The existing pipeline compares two *worksheets in one workbook*
(`"Snapshot Wk 1"` / `"Snapshot Wk 2"`). The drop-in model treats each *workbook*
as one snapshot. To reuse `load_snapshot` without changing it, the runner must know
which worksheet inside a dropped workbook holds the snapshot table.

Decision: the worksheet name is a **runtime configuration value**
(`snapshot_worksheet`, default `"Snapshot Wk 2"` — the sheet the pipeline treats as
"current"). This is a runtime input, not a business rule. Preflight validates the
sheet is present; the runner never fuzzy-matches or guesses a sheet name.

## New wrapper components (added, additive only)
- `scripts/runner_config.py` — runtime configuration: directory paths, allowed Excel
  extensions, lock-file prefix, snapshot worksheet name, state file location. No
  business rules. Overridable via a `RunnerConfig` dataclass for tests.
- `scripts/run_weekly_snapshot.py` — orchestrator + CLI entry point. Discovery,
  previous-snapshot resolution, preflight, pipeline invocation, temp->promote output,
  archive, state update, per-run JSON manifest. Importable functions so tests can
  drive it without the CLI.
- Folders: `data/incoming/`, `data/archive/`, `data/outputs/`, `data/state/`
  (each with `.gitkeep`).

## State
`data/state/last_successful_run.json` records the last successfully processed
workbook (archived path) plus run metadata. It is written only after 3B completes.
The previous snapshot is resolved from this file.

## Failure guarantees
On any failure: baseline state is not updated, the incoming workbook is not archived
or removed, and no promoted output directory is created (work happens in a temp dir
that is discarded). A manifest is still written for every attempt.

## Regression
The known pair (`"Snapshot Wk 1"` as previous, `"Snapshot Wk 2"` as current, from the
existing `data/Fake vendor data.xlsx`) is the golden result. A test asserts the runner
produces byte-identical executive-summary and key-movements text to calling the
existing functions directly.
