"""
weekly_update.py — Weekly Update Assembly (Milestone 3D.1).

Deterministically assembles a single `weekly_update.md` artefact from the report
outputs already produced by the pipeline. This module performs no calculations,
no analytics, and no content generation: it reads the existing executive-summary
and key-movements artefacts, inserts them verbatim into a fixed template with run
metadata, and writes the result.

It does not modify extraction, comparison, movement classification, or reporting
generation logic.
"""

from pathlib import Path


class WeeklyUpdateError(Exception):
    """Raised when a required input artefact is missing."""


WEEKLY_UPDATE_FILENAME = "weekly_update.md"


def _read_required(path: Path, label: str) -> str:
    """Read a required artefact, failing fast with a clear message if absent."""
    path = Path(path)
    if not path.exists():
        raise WeeklyUpdateError(
            f"Required {label} artefact not found: {path}. "
            f"Weekly update assembly cannot proceed."
        )
    return path.read_text(encoding="utf-8")


def render_weekly_update(
    executive_summary_content: str,
    key_movements_content: str,
    run_id: str,
    previous_snapshot: str,
    current_snapshot: str,
    generated_timestamp: str,
) -> str:
    """
    Render the weekly update markdown from content and metadata.

    Content is inserted verbatim. The template and section order are fixed.
    """
    return "\n".join([
        "# Weekly IT Simplification Update",
        "",
        "## Run Information",
        "",
        f"Run ID: {run_id}",
        "",
        f"Previous Snapshot: {previous_snapshot}",
        "",
        f"Current Snapshot: {current_snapshot}",
        "",
        f"Generated: {generated_timestamp}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        executive_summary_content,
        "",
        "---",
        "",
        "## Key Movements",
        "",
        key_movements_content,
        "",
    ])


def assemble_weekly_update(
    output_dir: Path,
    run_id: str,
    previous_snapshot: str,
    current_snapshot: str,
    generated_timestamp: str,
    executive_summary_filename: str = "executive_summary.txt",
    key_movements_filename: str = "key_movements.txt",
) -> Path:
    """
    Assemble weekly_update.md from existing artefacts in `output_dir`.

    Reads the executive-summary and key-movements artefacts that the pipeline has
    already written into `output_dir`, inserts them verbatim into the fixed
    template with the supplied run metadata, and writes weekly_update.md into the
    same directory.

    Parameters
    ----------
    output_dir : Path
        Directory containing the existing report artefacts; the weekly update is
        written here too.
    run_id, previous_snapshot, current_snapshot, generated_timestamp : str
        Run metadata for the Run Information section.
    executive_summary_filename, key_movements_filename : str
        Names of the existing artefacts to read.

    Returns
    -------
    Path
        Path to the written weekly_update.md.

    Raises
    ------
    WeeklyUpdateError
        If either required input artefact is missing.
    """
    output_dir = Path(output_dir)

    exec_content = _read_required(
        output_dir / executive_summary_filename, "executive summary"
    )
    moves_content = _read_required(
        output_dir / key_movements_filename, "key movements"
    )

    document = render_weekly_update(
        executive_summary_content=exec_content,
        key_movements_content=moves_content,
        run_id=run_id,
        previous_snapshot=previous_snapshot,
        current_snapshot=current_snapshot,
        generated_timestamp=generated_timestamp,
    )

    destination = output_dir / WEEKLY_UPDATE_FILENAME
    destination.write_text(document, encoding="utf-8")
    return destination
