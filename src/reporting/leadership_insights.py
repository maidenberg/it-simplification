"""
leadership_insights.py — Leadership Insights assembly (Milestone 3D.2).

Reporting-only artefact. Builds leadership_insights.txt using ONLY values that
already exist in the reporting outputs:

    - executive_summary.txt  (3A): "Contracts compared: N", "Net delta: $X"
    - key_movements.txt      (3B): ranked movement lines "1. ..." / "2. ..."

No analytics, calculations, aggregation, or ranking logic are performed here.
Values are parsed verbatim from the two artefacts and inserted into a fixed
five-insight template. Identical inputs always produce identical output.
"""

import re
from pathlib import Path


class LeadershipInsightsError(Exception):
    """Raised when a required input artefact is missing or unreadable."""


# Fallback text used when a second ranked movement is not present.
SINGLE_MOVER_FALLBACK = "not available"


def _read_required(path, label: str) -> str:
    """Read a required artefact, failing fast if it is missing."""
    path = Path(path)
    if not path.exists():
        raise LeadershipInsightsError(
            f"Required {label} artefact not found: {path}. "
            f"Leadership insights cannot be generated."
        )
    return path.read_text(encoding="utf-8")


def _parse_line_value(text: str, label: str) -> str | None:
    """Return the value following an exact 'label' prefix, or None if absent."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(label):
            return stripped[len(label):].strip()
    return None


def _parse_ranked_movement(text: str, number: int) -> str | None:
    """Return the ranked movement entry 'N. ...' text, or None if absent."""
    pattern = re.compile(rf"^{number}\.\s+(.*\S)\s*$")
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group(1).strip()
    return None


def _contract_name(mover_text: str | None) -> str | None:
    """
    Extract the contract-name portion from a ranked movement line.

    Ranked movements look like 'Example Contract 028 (+$16,764.09)'. The contract
    name is the text before the trailing ' (...)' amount. If no amount is
    present, the whole entry is treated as the contract name.
    """
    if mover_text is None:
        return None
    return re.sub(r"\s*\([^)]*\)\s*$", "", mover_text).strip()

def generate_delivery_progress(
    identified_costout: float,
    finalised_costout: float,
) -> str:
    """
    Generate a single leadership insight describing FY27 delivery progress.
    """

    if identified_costout <= 0:
        return "No identified savings currently recorded."

    realised_pct = (
        finalised_costout / identified_costout
    ) * 100

    return (
        f"FY27 identified savings total "
        f"${identified_costout:,.0f}, "
        f"with ${finalised_costout:,.0f} converted "
        f"to realised outcomes "
        f"({realised_pct:.1f}% delivery confidence)."
    )

def render_leadership_insights(
    contracts_compared: str,
    net_delta: str,
    top_mover_1: str,
    top_mover_2: str,
    contract_1: str,
    contract_2: str,
    status_summary: str | None = None,
    delivery_progress: str | None = None,
) -> str:
    """Render the fixed five-insight document. Fixed wording and ordering."""
    return "\n".join([
        "Executive Talking Points",
        "",
        f"1. {delivery_progress if delivery_progress else f'{contracts_compared} contracts were reviewed during the reporting period.'}",
        "",
        f"2. Net portfolio movement for the week was {net_delta}.",
        "",
        f"3. The largest movement this week was {top_mover_1}.",
        "",
        f"4. The second largest movement this week was {top_mover_2}.",
        "",
        f"5. Key commercial activity this week: "
        f"{status_summary if status_summary else 'Commercial negotiations and approvals remain in progress across several opportunities.'}."
        "",
    ])


def generate_leadership_insights(
    executive_summary_path,
    key_movements_path,
    output_path,
    identified_costout=None,
    finalised_costout=None,
) -> Path:
    """
    Generate leadership_insights.txt from existing reporting artefacts.

    Reads the executive-summary and key-movements artefacts, parses the required
    values already present in them, assembles the fixed five-insight document,
    and writes it to output_path.

    Parameters
    ----------
    executive_summary_path : str or Path
        Path to the existing executive_summary.txt artefact.
    key_movements_path : str or Path
        Path to the existing key_movements.txt artefact.
    output_path : str or Path
        Path to write leadership_insights.txt.

    Returns
    -------
    Path
        The output path written.

    Raises
    ------
    LeadershipInsightsError
        If either required input artefact is missing.
    """
    exec_text = _read_required(executive_summary_path, "executive summary")
    moves_text = _read_required(key_movements_path, "key movements")

    # Values already produced upstream — parsed, never recalculated.
    contracts_compared = _parse_line_value(exec_text, "Contracts compared:")
    net_delta = _parse_line_value(exec_text, "Net delta:")

    mover_1 = _parse_ranked_movement(moves_text, 1)
    mover_2 = _parse_ranked_movement(moves_text, 2)

    # Single-mover fallback: when only one ranked movement is present, the
    # second-mover fields degrade gracefully rather than failing.
    top_mover_1 = mover_1 if mover_1 is not None else SINGLE_MOVER_FALLBACK
    top_mover_2 = mover_2 if mover_2 is not None else SINGLE_MOVER_FALLBACK

    contract_1 = _contract_name(mover_1) or SINGLE_MOVER_FALLBACK
    contract_2 = _contract_name(mover_2) or SINGLE_MOVER_FALLBACK

    delivery_progress = None

    if (
        identified_costout is not None
        and finalised_costout is not None
    ):
        delivery_progress = generate_delivery_progress (
            identified_costout = identified_costout,
            finalised_costout = finalised_costout,
        )
    
    document = render_leadership_insights(
        contracts_compared=contracts_compared if contracts_compared is not None else SINGLE_MOVER_FALLBACK,
        net_delta=net_delta if net_delta is not None else SINGLE_MOVER_FALLBACK,
        top_mover_1=top_mover_1,
        top_mover_2=top_mover_2,
        contract_1=contract_1,
        contract_2=contract_2,
        status_summary=None,
        delivery_progress=delivery_progress,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path
