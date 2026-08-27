# Milestone 3C.2 — External Configuration and Real-Pair Acceptance: Notes

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
| `incoming_directory`  | string (path) | Where the operator drops the workbook.    |
| `archive_directory`   | string (path) | Where processed workbooks are moved.      |
| `outputs_directory`   | string (path) | Per-run outputs and manifests.            |
| `state_directory`     | string (path) | Location of the last-successful-run state.|
| `allowed_extensions`  | list[string]  | Eligible file extensions (e.g. `.xlsx`).  |

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

## Real-pair acceptance-test result
Two genuinely different single-snapshot workbooks were built from the sample
workbook's two worksheets ("Snapshot Wk 1" as previous, "Snapshot Wk 2" as
current), each saved as its own workbook with the configured worksheet name.

- Movements produced: **3** (increases: 3, decreases: 0).
- Net delta: **+24,750.09**.
- The runner's `executive_summary.txt` and `key_movements.txt` exactly matched the
  output of invoking the existing 2A–3B functions directly on the same pair.
- Archive, output promotion, state update, and a success manifest all verified.

## Test results
`python -m unittest scripts.test_run_weekly_snapshot scripts.test_executive_summary scripts.test_config_loader`
— 41 tests, all pass.

## Remaining assumptions
1. **Worksheet name per workbook.** Each weekly workbook is assumed to contain a
   worksheet whose name matches `snapshot_worksheet`. This is now operator-settable
   via config/CLI; it is still not auto-detected (no fuzzy matching), by design.
2. **One snapshot per workbook** is the operating model; the previous snapshot comes
   from the archived prior run. The acceptance test synthesises single-sheet
   workbooks to model this from the multi-sheet sample.
3. The **acceptance pair reuses the sample data's two worksheets**; a real future
   weekly workbook pair was not available in the repository to test against.
