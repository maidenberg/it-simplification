"""
reporting_package.py — Reporting Package Assembly (Milestone 3D.4).

Assembles a single deterministic weekly leadership report, reporting_package.txt,
from the five existing reporting artefacts. This is assembly only: content from
each artefact is preserved verbatim (whitespace normalised only at section
boundaries). No interpretation, parsing, ranking, filtering, summarising, or
deduplication is performed, and no new analytics are introduced.
"""

from pathlib import Path


class ReportingPackageError(Exception):
    """Raised when a required reporting artefact is missing."""


REPORTING_PACKAGE_FILENAME = "reporting_package.txt"

EMPTY_PLACEHOLDER = "No content available."

# Section (heading, underline) in fixed package order, paired with the parameter
# they read from. Underlines match the fixed output structure.
_SECTIONS = [
    ("EXECUTIVE SUMMARY", "================="),
    ("KEY MOVEMENTS", "============="),
    ("WEEKLY UPDATE", "============="),
    ("LEADERSHIP INSIGHTS", "==================="),
    ("RISKS & WATCHOUTS", "================="),
]


def _read_section_content(path, label: str) -> str:
    """
    Read one required artefact.

    Missing file -> ReportingPackageError (identifying the path). Empty or
    whitespace-only file -> the deterministic placeholder. Otherwise the content
    is returned with only leading/trailing whitespace stripped (boundary
    normalisation); internal blank lines are preserved verbatim.
    """
    path = Path(path)
    if not path.exists():
        raise ReportingPackageError(
            f"Required {label} artefact not found: {path}"
        )
    content = path.read_text(encoding="utf-8")
    if content.strip() == "":
        return EMPTY_PLACEHOLDER
    return content.strip("\n").strip()


def generate_reporting_package(
    executive_summary_path,
    key_movements_path,
    weekly_update_path,
    leadership_insights_path,
    risks_watchouts_path,
    output_path,
) -> Path:
    """
    Assemble reporting_package.txt from the five required reporting artefacts.

    Files are validated and read in package-section order. Each artefact's
    content is inserted verbatim under its fixed heading, with whitespace
    normalised only at section boundaries.

    Raises
    ------
    ReportingPackageError
        If a required artefact is missing (message identifies the path).

    Returns
    -------
    Path
        The output path written.
    """
    # Validate + read in package section order.
    ordered_inputs = [
        (executive_summary_path, "executive summary"),
        (key_movements_path, "key movements"),
        (weekly_update_path, "weekly update"),
        (leadership_insights_path, "leadership insights"),
        (risks_watchouts_path, "risks & watchouts"),
    ]
    contents = [_read_section_content(path, label) for path, label in ordered_inputs]

    lines = ["IT SIMPLIFICATION WEEKLY REPORT", ""]
    for (heading, underline), content in zip(_SECTIONS, contents):
        lines.append(heading)
        lines.append(underline)
        lines.append(content)
        lines.append("")
    lines.append("END OF REPORT")
    lines.append("")

    document = "\n".join(lines)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Overwrite any existing file so no stale content remains.
    output_path.write_text(document, encoding="utf-8")
    return output_path
