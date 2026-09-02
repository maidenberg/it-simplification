"""
run_weekly_snapshot.py — Drop-in weekly snapshot runner (Milestone 3C.1).

Orchestration only. This module wires together the existing, unchanged pipeline:

    2A  compare_snapshots.load_snapshot / extract_vendor_data
    2B-2F  compare_snapshots.compare_snapshots
    3A  executive_summary.generate_executive_summary
    3B  executive_summary.generate_key_movements

The runner performs no analysis or reporting calculations itself. It adds only
discovery, previous-snapshot resolution, preflight validation, temp->promote
output handling, archiving, last-successful-run state, and a per-run manifest.

Operator workflow:
    1. Place exactly one new .xlsx workbook in data/incoming/.
    2. Run:  python scripts/run_weekly_snapshot.py
    3. Review data/outputs/<run-id>/ and the manifest.
    4. On success the workbook is archived and becomes the next baseline.
    5. On failure the workbook stays in incoming/ and the error says why.

Usage:
    python scripts/run_weekly_snapshot.py
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
from executive_summary import generate_executive_summary, generate_key_movements

# reporting/ lives at the repository root (one level above scripts/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from reporting.weekly_update import assemble_weekly_update
from src.reporting.leadership_insights import generate_leadership_insights
from src.reporting.risks_watchouts import generate_risks_watchouts
from src.reporting.reporting_package import generate_reporting_package
from src.reporting.promotion_package import generate_promotion_package
from src.reporting.leadership_email import generate_leadership_email


# ---------------------------------------------------------------------------
# Errors — each carries a precise, actionable message.
# ---------------------------------------------------------------------------

class RunnerError(Exception):
    """Base class for runner failures with operator-facing messages."""


class DiscoveryError(RunnerError):
    """Raised when the incoming directory does not contain exactly one workbook."""


class BaselineError(RunnerError):
    """Raised when no previous successful snapshot baseline is available."""


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
# B. Current snapshot discovery
# ---------------------------------------------------------------------------

def discover_current_snapshot(config: RunnerConfig) -> Path:
    """
    Return the single eligible workbook in the incoming directory.

    Eligibility: file suffix in allowed_extensions and name not starting with the
    lock-file prefix (temporary Excel "~$" files are ignored).

    Raises
    ------
    DiscoveryError
        If zero or more than one eligible workbook is present.
    """
    if not config.incoming_dir.exists():
        raise DiscoveryError(
            f"Incoming directory does not exist: {config.incoming_dir}. "
            f"Create it and place exactly one workbook inside."
        )

    candidates = sorted(
        p for p in config.incoming_dir.iterdir()
        if p.is_file()
        and not p.name.startswith(config.lock_file_prefix)
        and p.suffix.lower() in config.allowed_extensions
    )

    if len(candidates) == 0:
        raise DiscoveryError(
            f"No eligible workbook found in {config.incoming_dir}. "
            f"Place exactly one {'/'.join(config.allowed_extensions)} file to process."
        )
    if len(candidates) > 1:
        names = "\n  - ".join(p.name for p in candidates)
        raise DiscoveryError(
            f"Multiple eligible workbooks found in {config.incoming_dir}; "
            f"expected exactly one. Candidates:\n  - {names}\n"
            f"Remove all but the workbook you want to process."
        )

    return candidates[0]


# ---------------------------------------------------------------------------
# C. Previous snapshot resolution + state
# ---------------------------------------------------------------------------

def read_state(config: RunnerConfig) -> dict | None:
    """Return the last-successful-run state dict, or None if none exists."""
    if not config.state_file.exists():
        return None
    with open(config.state_file, "r", encoding="utf-8") as fh:
        return json.load(fh)


def resolve_previous_snapshot(config: RunnerConfig, current: Path) -> Path:
    """
    Resolve the previous successful snapshot from state.

    Raises
    ------
    BaselineError
        If no previous successful snapshot exists, or the resolved file is
        missing, or it resolves to the same file as the current snapshot.
    """
    state = read_state(config)
    if not state or not state.get("snapshot_path"):
        raise BaselineError(
            "No previous successful snapshot found. A baseline must be "
            "established first: process an initial workbook so its result "
            "becomes the baseline for subsequent runs."
        )

    previous = Path(state["snapshot_path"])
    if not previous.exists():
        raise BaselineError(
            f"Previous snapshot recorded in state is missing on disk: {previous}. "
            f"Re-establish a baseline before running."
        )

    if previous.resolve() == current.resolve():
        raise BaselineError(
            f"Current and previous snapshots resolve to the same file: "
            f"{previous}. Provide a new workbook distinct from the baseline."
        )

    return previous


def write_state(config: RunnerConfig, archived_snapshot: Path, run_id: str) -> None:
    """Persist the last-successful-run state (called only after 3B succeeds)."""
    config.state_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "snapshot_path": str(archived_snapshot.resolve()),
        "run_id": run_id,
        "updated_at": _now_iso(),
    }
    with open(config.state_file, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


# ---------------------------------------------------------------------------
# D. Preflight validation (reuses the existing extractor as authority)
# ---------------------------------------------------------------------------

def preflight_workbook(config: RunnerConfig, path: Path, role: str) -> None:
    """
    Validate that a workbook exists, opens, contains the configured worksheet,
    and yields vendor data via the existing extractor.

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
            f"'{config.snapshot_worksheet}' in {path}: {exc}"
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


def run_pipeline(config: RunnerConfig, previous: Path, current: Path) -> dict:
    """
    Execute 2A->2F analysis then 3A/3B reporting using the existing modules.

    Returns
    -------
    dict
        {"analysis": <compare_snapshots result>,
         "executive_summary": <str>, "key_movements": <str>}
    """
    
    previous_sheet, current_sheet = find_latest_snapshot_sheets(current)
    
    previous_vendors = _extract(config, current, previous_sheet)
    current_vendors = _extract(config, current, current_sheet)

    analysis = compare_snapshots(previous_vendors, current_vendors)  # 2B-2F

    exec_summary = generate_executive_summary(analysis)  # 3A
    key_moves = generate_key_movements(analysis)         # 3B

    return {
        "analysis": analysis,
        "executive_summary": exec_summary,
        "key_movements": key_moves,
    }


# ---------------------------------------------------------------------------
# Output + manifest
# ---------------------------------------------------------------------------

def _write_outputs(dest: Path, results: dict) -> None:
    """Write report text and a JSON analysis dump into a directory."""
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "executive_summary.txt").write_text(
        results["executive_summary"], encoding="utf-8"
    )
    (dest / "key_movements.txt").write_text(
        results["key_movements"], encoding="utf-8"
    )
    # A machine-readable dump of the analysis result (contracts are strings,
    # deltas are floats — all JSON-serialisable).
    with open(dest / "analysis.json", "w", encoding="utf-8") as fh:
        json.dump(results["analysis"], fh, indent=2)


def _write_manifest(config: RunnerConfig, manifest: dict) -> Path:
    """Write the per-run manifest under outputs/, keyed by run id."""
    config.outputs_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = config.outputs_dir / f"manifest_{manifest['run_id']}.json"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    return manifest_path


# ---------------------------------------------------------------------------
# E. Orchestration entry point
# ---------------------------------------------------------------------------

def run(config: RunnerConfig | None = None) -> dict:
    """
    Execute the full drop-in run. Returns the run manifest dict.

    A manifest is produced for every attempt. On failure, state is not updated,
    the incoming workbook is not archived, and no promoted output directory is
    left behind.
    """
    config = config or default_config()
    config.ensure_directories()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    manifest = {
        "run_id": run_id,
        "status": "failed",
        "current_snapshot": None,
        "previous_snapshot": None,
        "output_directory": None,
        "stages_completed": [],
        "generated_artefacts": [],
        "warnings": [],
        "errors": [],
        "started_at": _now_iso(),
    }

    temp_dir = config.outputs_dir / f".tmp_{run_id}"

    try:
        # 3. Discover current snapshot.
        current = config.weekly_snapshot_workbook

        manifest["current_snapshot"] = str(current)
        manifest["stages_completed"].append("discovery")

        # 4. Resolve previous snapshot.
        previous = current

        manifest["previous_snapshot"] = str(previous)
        manifest["stages_completed"].append("previous_resolution")

        # 5. Preflight both workbooks.
        preflight_workbook(config, previous, "previous")
        preflight_workbook(config, current, "current")
        manifest["stages_completed"].append("preflight")

        # 6-7. Analysis (2A-2F) + reporting (3A/3B).
        results = run_pipeline(config, previous, current)
        
        from src.reporting.leadership_candidates import (
            build_candidate_pool,
            load_candidate_commentary,
            build_commentary_lookup,
            enrich_candidates_with_commentary,
            candidates_with_meaningful_commentary,
            rank_candidates_for_leadership,
        )

        current_sheet_name = find_latest_snapshot_sheets(current)[1]

        current_vendors = _extract (
            config,
            current,
            current_sheet_name,

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

        # 8b. Assemble the weekly update from the just-written 3A/3B artefacts
        # (3D.1). Runs after Executive Summary + Key Movements are on disk.
        assemble_weekly_update(
            output_dir=temp_dir,
            run_id=run_id,
            previous_snapshot=str(previous),
            current_snapshot=str(current),
            generated_timestamp=_now_iso(),
        )
        manifest["stages_completed"].append("weekly_update")

        # 8c. Assemble leadership insights from the just-written 3A/3B artefacts
        # (3D.2). Reuses existing outputs only; no new analytics.
        generate_leadership_insights(
            executive_summary_path=temp_dir / "executive_summary.txt",
            key_movements_path=temp_dir / "key_movements.txt",
            output_path=temp_dir / "leadership_insights.txt",
            ranked_candidates=ranked_candidates,
        )
        manifest["stages_completed"].append("leadership_insights")

        # 8d. Assemble risks & watchouts from existing reporting artefacts
        # (3D.3). Reuses existing outputs only; no new analytics.
        generate_risks_watchouts(
            leadership_insights_path=temp_dir / "leadership_insights.txt",
            key_movements_path=temp_dir / "key_movements.txt",
            output_path=temp_dir / "risks_watchouts.txt",
            ranked_candidates=ranked_candidates,
        )
        manifest["stages_completed"].append("risks_watchouts")

        # 8e. Assemble the full reporting package from the five artefacts
        # (3D.4). Runs after risks_watchouts, before promotion. The weekly
        # update artefact is passed by the name the runner produces it under.
        generate_reporting_package(
            executive_summary_path=temp_dir / "executive_summary.txt",
            key_movements_path=temp_dir / "key_movements.txt",
            weekly_update_path=temp_dir / "weekly_update.md",
            leadership_insights_path=temp_dir / "leadership_insights.txt",
            risks_watchouts_path=temp_dir / "risks_watchouts.txt",
            output_path=temp_dir / "reporting_package.txt",
        )
        manifest["stages_completed"].append("reporting_package")

        # 8f. Generate leadership email
        generate_leadership_email (
            leadership_insights_path = temp_dir / "leadership_insights.txt",
            risks_watchouts_path = temp_dir / "risks_watchouts.txt",
            output_path=temp_dir / "leadership_email.txt",
        )

        manifest["stages_completed"].append("leadership_email")

        # 8g. Assemble the promotion package (3D.5): validate + copy the existing
        # reporting artefacts into promotion_package/ with a metadata manifest.
        # Runs after reporting_package, before promotion. Packaging only.
        generate_promotion_package(
            source_dir=temp_dir,
            run_id=run_id,
            generated_at=_now_iso(),
        )
        manifest["stages_completed"].append("promotion_package")

        # Record the generated artefacts (sorted for deterministic manifests).
        manifest["generated_artefacts"] = sorted(
            p.name for p in temp_dir.iterdir() if p.is_file()
        )

        # 9. Promote temp output to outputs/<run-id> only after success.
        final_output = config.outputs_dir / run_id
        if final_output.exists():
            shutil.rmtree(final_output)
        shutil.move(str(temp_dir), str(final_output))
        manifest["output_directory"] = str(final_output)
        manifest["stages_completed"].append("promote")

        # 10. Archive the processed current snapshot.
        archived = config.archive_dir / current.name
        if archived.exists():
            archived = config.archive_dir / f"{current.stem}_{run_id}{current.suffix}"
        shutil.move(str(current), str(archived))
        manifest["stages_completed"].append("archive")

        # 11. Update last-successful-run state.
        write_state(config, archived, run_id)
        manifest["stages_completed"].append("state_update")

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
            worksheet_override=args.worksheet,
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
        print(f"  Worksheet:         {config.snapshot_worksheet}")
        print(f"  Current snapshot:  {manifest['current_snapshot']}")
        print(f"  Previous snapshot: {manifest['previous_snapshot']}")
        print(f"  Output directory:  {manifest['output_directory']}")
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
