# Scripts

This folder contains automation scripts for the IT Simplification project.

Examples:
- Data extraction
- Data transformation
- Dashboard generation
- Reporting automation

## Weekly Snapshot Runner (Milestone 3C.1)

Drop in one new weekly workbook and run a single command to execute the existing
analysis (2A–2F) and reporting (3A–3B) pipeline. The runner is orchestration only;
it does not change any analysis or reporting logic.

### Setup (one time)

Install dependencies:

```
pip install -r scripts/requirements.txt
```

The runner uses these directories (created automatically if missing):

- `data/incoming/` — where you drop the new weekly workbook
- `data/archive/` — successfully processed workbooks are moved here
- `data/outputs/` — one folder per run (`<run-id>`) plus a manifest per attempt
- `data/state/` — `last_successful_run.json`, the baseline pointer

Runtime settings (paths, allowed extensions, and the worksheet the runner reads)
live in `scripts/runner_config.py`. The default worksheet is `Snapshot Wk 2`.

### Weekly operator workflow

1. Place exactly **one** new `.xlsx` workbook in `data/incoming/`.
2. Run the weekly snapshot command:

   ```
   python scripts/run_weekly_snapshot.py
   ```

3. Review the generated output in `data/outputs/<run-id>/`:
   - `executive_summary.txt` (3A)
   - `key_movements.txt` (3B)
   - `analysis.json` (raw movement-analysis result)
   - and the run manifest at `data/outputs/manifest_<run-id>.json`
4. **On success**, the workbook is moved to `data/archive/` and becomes the
   baseline (previous snapshot) for the following run.
5. **On failure**, the workbook stays in `data/incoming/`, the baseline is left
   unchanged, no partial report is promoted, and the printed error identifies
   exactly what must be corrected.

### External configuration (Milestone 3C.2)

Runtime settings can be changed with **no Python code edits** via
`config/weekly_snapshot.json`:

```json
{
  "snapshot_worksheet": "Snapshot Wk 2",
  "incoming_directory": "data/incoming",
  "archive_directory": "data/archive",
  "outputs_directory": "data/outputs",
  "state_directory": "data/state",
  "allowed_extensions": [".xlsx"]
}
```

Precedence (highest first): **CLI flag > configuration file > built-in default.**

- `--worksheet NAME` overrides the worksheet for a single run.
- `--config PATH` uses a specific configuration file (it must exist and be valid).
- With no flags, `config/weekly_snapshot.json` is used if present; otherwise the
  built-in defaults apply.

Invalid configuration (missing explicit file, malformed JSON, unknown key, wrong
value type) fails the run *before* any analysis, and never archives the workbook
or changes the baseline.

Run against a different worksheet:

```
python scripts/run_weekly_snapshot.py --worksheet "Snapshot Wk 1"
```

### Establishing the first baseline

The first run needs a previous snapshot to compare against. Until a baseline
exists the runner stops with a clear message ("a baseline must be established").
The runner never uses the current file as both previous and current.

To establish the first baseline, record an already-processed workbook as the
baseline. This writes `data/state/last_successful_run.json` pointing at that
workbook (place the baseline workbook in `data/archive/` first):

```
python -c "import sys; sys.path.insert(0,'scripts'); from config_loader import build_config; import run_weekly_snapshot as r; from pathlib import Path; c=build_config(); c.ensure_directories(); r.write_state(c, Path('data/archive/<baseline>.xlsx'), 'manual-baseline')"
```

After this, drop the next week's workbook into `data/incoming/` and run the
normal command. On each subsequent success the processed workbook is archived and
automatically becomes the baseline for the following run.

### Rules the runner enforces

- Exactly one eligible workbook must be in `data/incoming/`. Zero or multiple
  stops the run with an actionable message (multiple lists the candidates).
- Temporary Excel lock files (names starting with `~$`) are ignored.
- The current and previous snapshots must be different files.
- Preflight validation opens both workbooks, confirms the required worksheet is
  present, and reuses the existing extractor to confirm vendor structure before
  any analysis or reporting runs.

### Tests

```
python -m unittest scripts.test_run_weekly_snapshot scripts.test_executive_summary
```
