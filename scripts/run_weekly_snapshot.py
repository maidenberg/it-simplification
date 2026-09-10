"""
run_weekly_snapshot.py

Orchestrates the active IT Simplification weekly reporting pipeline.

Current flow:

Weekly snapshots workbook
-> snapshot comparison
-> analysis.json
-> leadership candidate generation
-> leadership_insights.txt
-> risks_watchouts.txt
-> leadership_email.txt

The runner coordinates existing pipeline components and manages:

- workbook validation
- snapshot-sheet discovery
- pipeline execution
- output generation
- manifest creation

It does not contain leadership judgement, ranking, risk-identification,
comparison, or reporting business logic. Those responsibilities remain within
the existing pipeline modules.
"""

import contextlib
import io
import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

# Make sibling modules importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from runner_config import RunnerConfig, default_config
from config_loader import build_config, ConfigError
from compare_snapshots import (
    load_snapshot, 
    extract_vendor_data, 
    compare_snapshots,
    find_latest_snapshot_sheets,
)

# reporting/ lives at the repository root (one level above scripts/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.reporting.leadership_insights import generate_leadership_insights
from src.reporting.risks_watchouts import generate_risks_watchouts
from src.reporting.leadership_email import generate_leadership_email


# ---------------------------------------------------------------------------
# Errors — each carries a precise, actionable message.
# ---------------------------------------------------------------------------

class RunnerError(Exception):
    """Base class for runner failures with operator-facing messages."""

class PreflightError(RunnerError):
    """Raised when a workbook fails preflight validation."""


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _quiet():
    """Suppress the pipeline's diagnostic stdout while still capturing errors."""
    return contextlib.redirect_stdout(io.StringIO())


# ---------------------------------------------------------------------------
# Preflight validation (reuses the existing extractor as authority)
# ---------------------------------------------------------------------------

def preflight_workbook(config: RunnerConfig, path: Path, role: str) -> None:
    """
    Validate that a workbook exists, that snapshot worksheets can be identified,
    and that vendor data can be extracted via the existing pipeline.

    Uses the existing pipeline (load_snapshot + extract_vendor_data) as the
    authority — no competing parser is introduced.

    Parameters
    ----------
    role : str
        "current" or "previous", used only for clearer error messages.

    Raises
    ------
    PreflightError
        With a precise message identifying the file/worksheet/condition.
    """
    if not path.exists():
        raise PreflightError(f"[{role}] Workbook does not exist: {path}")

    # Confirm the workbook opens and contains the configured worksheet.
    try:
        wb = openpyxl.load_workbook(path, read_only=True)
    except Exception as exc:  # openpyxl raises varied exceptions for bad files
        raise PreflightError(
            f"[{role}] Workbook cannot be opened (unreadable or corrupt): "
            f"{path} ({exc})"
        )
    try:
        sheet_names = list(wb.sheetnames)
    finally:
        wb.close()

    try:
        find_latest_snapshot_sheets(path)
    except Exception as exc:
        raise PreflightError(
            f"[{role}] Could not identify the latest two snapshot worksheets "
            f"in {path}: {exc}"
        )

    # Use the existing extractor as the authority for structure/fields.
    try:
        with _quiet():
            previous_sheet, current_sheet = find_latest_snapshot_sheets(path)

            raw = load_snapshot(path, current_sheet)
            vendors = extract_vendor_data(raw)
    except Exception as exc:
        raise PreflightError(
            f"[{role}] Failed to extract vendor data from worksheet "
            f"'{current_sheet}' in {path}: {exc}"
        )

    if vendors is None or len(vendors) == 0:
        raise PreflightError(
            f"[{role}] No vendor rows extracted from the latest snapshot "
            f" worksheet in {path}. The required vendor-table structure "
            f"appears to be missing."
        )

    if "Contract" not in vendors.columns:
        raise PreflightError(
            f"[{role}] Extracted vendor data from {path} is missing the required "
            f"'Contract' column. Available columns: {list(vendors.columns)}."
        )


# ---------------------------------------------------------------------------
# Pipeline invocation (reused logic, no new calculations)
# ---------------------------------------------------------------------------

def _extract(config: RunnerConfig, path: Path, worksheet: str):
    """Run 2A extraction for one workbook using the existing functions."""
    with _quiet():
        return extract_vendor_data(load_snapshot(path, worksheet))


def run_pipeline(
    config: RunnerConfig, 
    workbook: Path, 
    previous_sheet: str,
    current_sheet: str,
    ) -> dict:
    """
    Execute 2A->2F analysis then 3A/3B reporting using the existing modules.

    Returns
    -------
    dict
        {
            "analysis": <compare_snapshots result>
        }
    """
    
    previous_vendors = _extract(
        config, 
        workbook, 
        previous_sheet,
        )
    current_vendors = _extract(
        config, 
        workbook, 
        current_sheet,
        )

    analysis = compare_snapshots(previous_vendors, current_vendors)  # 2B-2F

    return {
        "analysis": analysis,
    }


# ---------------------------------------------------------------------------
# Output + manifest
# ---------------------------------------------------------------------------

def _write_outputs(dest: Path, results: dict) -> None:
    """Write report text and a JSON analysis dump into a directory."""
    dest.mkdir(parents=True, exist_ok=True)
    
    # Persist the comparison-analysis output for downstream reporting,
    # traceability, and validation.
    with open(dest / "analysis.json", "w", encoding="utf-8") as fh:
        json.dump(results["analysis"], fh, indent=2)


def _write_manifest(config: RunnerConfig, manifest: dict) -> Path:
    """Write the per-run manifest under outputs/, keyed by run id."""
    config.outputs_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = config.outputs_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    return manifest_path


# ---------------------------------------------------------------------------
# Orchestration entry point
# ---------------------------------------------------------------------------

def run(config: RunnerConfig | None = None) -> dict:
    """
    Execute the full drop-in run. Returns the run manifest dict.

    A manifest is produced for every attempt. On failure, no promoted output directory is left behind.
    """
    config = config or default_config()
    config.ensure_directories()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    manifest = {
        "run_id": run_id,
        "status": "failed",
        "current_snapshot": None,
        "previous_sheet": None,
        "current_sheet": None,
        "output_directory": None,
        "stages_completed": [],
        "generated_artefacts": [],
        "warnings": [],
        "errors": [],
        "started_at": _now_iso(),
    }

    temp_dir = config.outputs_dir / f".tmp_{run_id}"

    try:
        # 3. Select workbook.
        current = config.weekly_snapshot_workbook

        manifest["current_snapshot"] = str(current)
        manifest["stages_completed"].append("workbook_selection")

        # 4. Identify snapshot sheets.
        previous_sheet, current_sheet = find_latest_snapshot_sheets(current)
        
        manifest["previous_sheet"] = previous_sheet
        manifest["current_sheet"] = current_sheet
        
        manifest["stages_completed"].append("worksheet_selection")


        # 5. Preflight workbook and snapshot worksheets.
        preflight_workbook(config, current, "current")
        manifest["stages_completed"].append("preflight")

        # 6-7. Analysis (2A-2F) + reporting (3A/3B).
        results = run_pipeline(
            config, 
            current,
            previous_sheet, 
            current_sheet,
        )
        
        from src.reporting.leadership_candidates import (
            build_candidate_pool,
            load_candidate_commentary,
            build_commentary_lookup,
            enrich_candidates_with_commentary,
            candidates_with_meaningful_commentary,
            rank_candidates_for_leadership,
        )

        current_vendors = _extract (
            config,
            current,
            current_sheet,
        )

        candidates = build_candidate_pool (current_vendors)

        commentary_df = load_candidate_commentary (
            "data/IT simplification dashboard.xlsx"
        )

        commentary_lookup = build_commentary_lookup (commentary_df)

        candidates = enrich_candidates_with_commentary (
            candidates,
            commentary_lookup,
        )

        commented_candidates = candidates_with_meaningful_commentary (candidates)

        ranked_candidates = rank_candidates_for_leadership (commented_candidates)

        print("\nTOP LEADERSHIP CANDIDATES")

        for candidate in ranked_candidates[:5]:
            print (
                f"{candidate.contract} | "
                f"{candidate.commentary}"
            )

        print("\nTOP 20 RANKED CANDIDATES")

        for candidate in ranked_candidates[:20]:
            print (
                f"{candidate.costout:,.0f} | "
                f"{candidate.contract} | "
                f"{candidate.commentary}"
            )

        manifest["stages_completed"].extend(["analysis", "reporting"])

        # 8. Write to temp output location.
        _write_outputs(temp_dir, results)

       # 8a. Assemble leadership insights from the just-written 3A/3B artefacts
        # (3D.2). Reuses existing outputs only; no new analytics.
        generate_leadership_insights(
            output_path=temp_dir / "leadership_insights.txt",
            ranked_candidates=ranked_candidates,
        )
        manifest["stages_completed"].append("leadership_insights")

        # 8b. Assemble risks & watchouts from existing reporting artefacts
        # (3D.3). Reuses existing outputs only; no new analytics.
        generate_risks_watchouts(
            leadership_insights_path=temp_dir / "leadership_insights.txt",
            output_path=temp_dir / "risks_watchouts.txt",
            ranked_candidates=ranked_candidates,
        )
        manifest["stages_completed"].append("risks_watchouts")

        # 8c. Generate leadership email
        comparison_label = (
            f"Comparison: {previous_sheet} → {current_sheet}"
        )
        
        generate_leadership_email (
            leadership_insights_path = temp_dir / "leadership_insights.txt",
            risks_watchouts_path = temp_dir / "risks_watchouts.txt",
            output_path=temp_dir / "leadership_email.txt",
            comparison_label= comparison_label,
        )

        manifest["stages_completed"].append("leadership_email")

        # 8d. Record the generated artefacts (sorted for deterministic manifests).
        manifest["generated_artefacts"] = sorted(
            p.name for p in temp_dir.iterdir() if p.is_file()
        )

        # 9. Promote temp output to outputs/<run-id> only after success.
        final_output = config.outputs_dir / "latest"
        if final_output.exists():
            shutil.rmtree(final_output)
        shutil.move(str(temp_dir), str(final_output))
        manifest["output_directory"] = str(final_output)
        manifest["stages_completed"].append("promote")
       
        manifest["status"] = "success"

    except RunnerError as exc:
        manifest["errors"].append(str(exc))
    except Exception as exc:  # unexpected failure — never corrupt state
        manifest["errors"].append(f"Unexpected error: {exc}")
    finally:
        # Never leave a partial temp output that could look like a real report.
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        manifest["finished_at"] = _now_iso()
        _write_manifest(config, manifest)

    return manifest


def _parse_args(argv=None):
    """Parse CLI arguments for the runner."""
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Run the weekly IT Simplification snapshot pipeline on the workbook "
            "in the incoming directory."
        )
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help=(
            "Path to an external JSON configuration file. If omitted, the "
            "default config/weekly_snapshot.json is used when present."
        ),
    )
    parser.add_argument(
        "--worksheet",
        metavar="NAME",
        default=None,
        help=(
            "Worksheet name to read from each workbook. Overrides both the "
            "configuration file and the built-in default."
        ),
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)

    # Build configuration with precedence: CLI > file > defaults.
    # Configuration errors fail here, before any analysis, archiving, or state
    # change occurs.
    try:
        config_path = Path(args.config) if args.config else None
        config = build_config(
            config_path=config_path,
            require_config_file=bool(args.config),
        )
    except ConfigError as exc:
        print("Weekly snapshot run: FAILED (configuration error)", file=sys.stderr)
        print(f"  - {exc}", file=sys.stderr)
        print("  No analysis was run; the incoming workbook and baseline are unchanged.",
              file=sys.stderr)
        return 1

    manifest = run(config)
    if manifest["status"] == "success":
        print("Weekly snapshot run: SUCCESS")
        print(f"  Run ID:            {manifest['run_id']}")
        print(f" Current snapshot:   {manifest['current_snapshot']}")
        print(f" Previous sheet:     {manifest['previous_sheet']}")
        print(f" Current sheet:      {manifest['current_sheet']}")
        print(f" Output directory:   {manifest['output_directory']}")
        return 0

    print("Weekly snapshot run: FAILED", file=sys.stderr)
    for err in manifest["errors"]:
        print(f"  - {err}", file=sys.stderr)
    print(f"  Run ID: {manifest['run_id']}", file=sys.stderr)
    print("  The incoming workbook was left in place; correct the issue and re-run.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
