"""
risks_watchouts.py 

Builds risks_watchouts.txt from existing leadership artefacts.

Primary input: leadership_insights.txt  
Optional input: ranked leadership candidates

No new analytics, recalculation, scoring, or ranking is performed.

Produces:

    RISKS            
    WATCHOUTS        
    DATA OBSERVATIONS

Deterministic: identical inputs always produce identical output.
"""

import re
from pathlib import Path


class RisksWatchoutsError(Exception):
    """Raised when a required input artefact is missing or unreadable."""


RISKS_WATCHOUTS_FILENAME = "risks_watchouts.txt"

NO_RISKS = "No risks identified."
NO_WATCHOUTS = "No watchouts identified."
NO_OBSERVATIONS = "No data observations identified."

def _read_required(path, label: str) -> str:
    """Read a required artefact, failing fast if it is missing."""
    path = Path(path)
    if not path.exists():
        raise RisksWatchoutsError(
            f"Required {label} artefact not found: {path}. "
            f"Risks & watchouts cannot be generated."
        )
    return path.read_text(encoding="utf-8")


def _parse_insight_line(leadership_text: str, prefix: str) -> str | None:
    """Return a leadership-insights insight line body by its numbered prefix."""
    for line in leadership_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped
    return None


# Preferred approach: pre-labelled entries already present in leadership_insights.
# A line labelled "RISK:", "WATCHOUT:" or "OBSERVATION:" (case-insensitive) is
# lifted verbatim (value after the label) into the corresponding section.
_LABELS = {
    "risk": "RISK:",
    "watchout": "WATCHOUT:",
    "observation": "OBSERVATION:",
}


def _extract_labelled(leadership_text: str, label: str) -> list[str]:
    """
    Return entries pre-labelled with `label` in leadership_insights, verbatim.

    Matching is exact (case-insensitive) on the label prefix; only the text
    already present after the label is returned. No derivation is performed.
    """
    entries = []
    lowered = label.lower()
    for line in leadership_text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(lowered):
            value = stripped[len(label):].strip()
            if value:
                entries.append(value)
    return entries


def _build_observations(leadership_text: str) -> list[str]:
    """Data observations sourced verbatim from leadership-insights facts."""
    observations = []
    covered = _parse_insight_line(leadership_text, "1.")
    net = _parse_insight_line(leadership_text, "2.")
    if covered:
        observations.append(covered)
    if net:
        observations.append(net)
    return observations


def _render_section(title: str, underline: str, entries: list[str],
                    placeholder: str) -> list[str]:
    """Render a titled section with entries or a deterministic placeholder."""
    lines = [title, underline]
    if entries:
        
        for entry in entries:
           lines.append(entry)
           lines.append("")
    else:
        lines.append(placeholder)
    return lines


def render_risks_watchouts(risks: list[str], watchouts: list[str],
                           observations: list[str]) -> str:
    """Render the fixed-format document. Fixed ordering; deterministic."""
    lines = ["IT SIMPLIFICATION RISKS & WATCHOUTS", ""]
    lines += _render_section("RISKS", "------", risks, NO_RISKS)
    lines.append("")
    lines += _render_section("WATCHOUTS", "---------", watchouts, NO_WATCHOUTS)
    lines.append("")
    lines += _render_section("DATA OBSERVATIONS", "-----------------",
                             observations, NO_OBSERVATIONS)
    lines.append("")
    lines.append("END OF REPORT")
    lines.append("")
    return "\n".join(lines)


def generate_risks_watchouts(
    leadership_insights_path,
    output_path,
    ranked_candidates=None,
) -> Path:

    """
    Generate risks_watchouts.txt from existing reporting artefacts.

    Parameters
    ----------
    leadership_insights_path : str or Path
        Path to the existing leadership_insights.txt artefact (primary).
    ranked_candidates : list, optional
        Ranked leadership candidates supplied by the updstream candidate generation process.
    output_path : str or Path
        Path to write risks_watchouts.txt.

    Returns
    -------
    Path
        The output path written.

    Raises
    ------
    RisksWatchoutsError
        If either required input artefact is missing.
    """
    leadership_text = _read_required(leadership_insights_path, "leadership insights")

    # Preferred approach: use pre-labelled entries from leadership_insights.
    labelled_risks = _extract_labelled(leadership_text, _LABELS["risk"])
    labelled_watchouts = _extract_labelled(leadership_text, _LABELS["watchout"])
    labelled_observations = _extract_labelled(leadership_text, _LABELS["observation"])

    # Fallback per section when no pre-labelled entries exist for that section.
    risks = labelled_risks if labelled_risks else []
    if labelled_watchouts:
        watchouts = labelled_watchouts

    elif ranked_candidates:

        watchouts = []

        for candidate in ranked_candidates[1:10]:

            commentary = candidate.commentary.lower()

            if (
                "no progress" in commentary
                or "no update" in commentary
                or "awaiting" in commentary
                or "approval" in commentary
                or "working on it" in commentary
                or "under discussion" in commentary
            ):
                watchouts.append(
                    f"{candidate.vendor}\n"
                    f"{candidate.commentary}"
                    )

            else:
                continue
    
    else:
        watchouts = []

    observations = (
        labelled_observations if labelled_observations
        else _build_observations(leadership_text)
    )

    document = render_risks_watchouts(risks, watchouts, observations)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path
