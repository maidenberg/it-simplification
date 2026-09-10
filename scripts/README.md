# Scripts

This folder contains automation scripts for the IT Simplification project.

Examples:
- Data extraction
- Data transformation
- Dashboard generation
- Reporting automation

## Weekly Snapshot Runner

Drop in one new weekly workbook and run a single command to execute the weekly IT Simplification reporting pipeline.
The runner is orchestration only; it does not change any analysis or reporting logic.

### Setup (one time)

Install dependencies:

```
pip install -r scripts/requirements.txt
```

The runner uses:
 
- data/Weekly snapshots.xlsx — source workbook containing snapshot worksheets.
- data/outputs/latest/ — generated reporting artefacts and leadership email outputs.
 
Runtime settings live in scripts/runner_config.py. The default worksheet is Live Dashboard.

### Weekly operator workflow

1. Update the latest snapshot within `data/Weekly snapshots.xlsx`.
2. Run the weekly snapshot command in PowerShell:
 
python scripts/run_weekly_snapshot.py
 
3. Review the generated output in `data/outputs/latest/`:
- analysis.json
- leadership_insights.txt
- risks_watchouts.txt
- leadership_email.txt
 
4. On success, outputs are written to `data/outputs/latest/`.
 
5. On failure, no partial report is promoted and the printed error identifies
the issue that must be corrected before re-running.

### External configuration 

Runtime settings can be changed with **no Python code edits** via `config/weekly_snapshot.json`:

```json
{
  "snapshot_worksheet": "Live dashboard",
  "outputs_directory": "data/outputs",
}
```

Precedence (highest first): **CLI flag > configuration file > built-in default.**

- `--worksheet NAME` overrides the worksheet for a single run.
- `--config PATH` uses a specific configuration file (it must exist and be valid).
- With no flags, `config/weekly_snapshot.json` is used if present; otherwise the
  built-in defaults apply.

Invalid configuration (missing explicit file, malformed JSON, unknown key, or
wrong value type) fails the run before any analysis or output generation.

### Rules the runner enforces

- Preflight validation confirms that the workbook can be opened, that valid
snapshot worksheets can be identified, and that vendor data can be extracted
before any analysis or reporting runs.

### Tests

See the active test suite in the tests/ folder.
