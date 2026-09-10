"""
leadership_insights.py — Leadership Insights assembly.

Builds leadership_insights.txt from ranked leadership candidates and delivery metrics.

Produces themed executive insights including:

    - Major Commercial Win
    - Executive Watchout
    - Decision Required
    - Financial Watchout
    - Delivery Progress

Contains no analytics, ranking, or cost calculations. Inputs are provided by the leadership-candidate generation layer.
"""

import re
from pathlib import Path
from src.reporting.leadership_candidates import (
    classify_leadership_theme,
)


class LeadershipInsightsError(Exception):
    """Raised when a required input artefact is missing or unreadable."""


def _read_required(path, label: str) -> str:
    """Read a required artefact, failing fast if it is missing."""
    path = Path(path)
    if not path.exists():
        raise LeadershipInsightsError(
            f"Required {label} artefact not found: {path}. "
            f"Leadership insights cannot be generated."
        )
    return path.read_text(encoding="utf-8")

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
    major_win: str | None,
    risk: str | None,
    decision_required: str | None,
    financial: str | None,
    delivery_progress: str | None = None,
    portfolio_message: str | None = None,
) -> str:
    """Render the fixed five-insight document. Fixed wording and ordering."""
    
    sections = ["Leadership Insights", ""]

    if major_win:
        sections.extend ([
            "MAJOR COMMERCIAL WIN",
            major_win,
            "",
    ])

    if risk:
        sections.extend ([
            "EXECUTIVE WATCHOUT",
            risk,
            "",
    ])

    if decision_required:
            sections.extend ([
            "DECISION REQUIRED",
            decision_required,
            "",
    ])

    if financial:
            sections.extend ([
            "FINANCIAL WATCHOUT",
            financial,
            "",
    ])

    if delivery_progress:
        sections.extend ([
            "DELIVERY PROGRESS",
            delivery_progress,
            "",
    ])

    if portfolio_message:
        sections.extend ([
            "PORTFOLIO MESSAGE",
            portfolio_message,
            "",
    ]) 

    return "\n".join(sections)

def generate_leadership_insights(
    output_path,
    ranked_candidates=None,
    identified_costout=None,
    finalised_costout=None,
) -> Path:
    """
    Generate leadership_insights.txt from existing reporting artefacts.

    Consumes the ranked leadership candidates produced by the active
    leadership-email pipeline and renders leadership-relevant insights
    without performing additional ranking, scoring, or analysis.

    Parameters
    ----------
    output_path : str or Path
        Path to write leadership_insights.txt.

    ranked_candidates : list, optional
        Ranked leadership candidates supplied by the upstream
        candidate-generation process.

    identified_costout : float, optional
        Portfolio identified cost-out value.

    finalised_costout : float, optional
        Finalised portfolio cost-out value.

    Returns
    -------
    Path
        The output path written.

    Raises
    ------
    LeadershipInsightsError
        If either required input artefact is missing.
    """
    if ranked_candidates:
        by_theme = {}

        for candidate in ranked_candidates:
            theme = classify_leadership_theme(candidate)

            if theme not in by_theme:
                by_theme[theme] = candidate

    delivery_progress = None

    if (
        identified_costout is not None
        and finalised_costout is not None
    ):
        delivery_progress = generate_delivery_progress (
            identified_costout = identified_costout,
            finalised_costout = finalised_costout,
        )
    
    major_win = None
    risk = None
    decision_required = None
    financial = None
    portfolio_message = None

    if ranked_candidates:

        financial_risk_candidates = [
            candidate
            for candidate in ranked_candidates
            if classify_leadership_theme(candidate) == "financial_risk"
        ]

        major_win_candidate = by_theme.get("major_win")
        risk_candidate = by_theme.get("risk")
        decision_candidate = by_theme.get("decision_required")

        financial_candidate = (
            by_theme.get("financial_risk")
            or by_theme.get("financial_win")
        )

        if major_win_candidate:
            major_win = (
                f"{major_win_candidate.vendor}\n"
                f"{major_win_candidate.commentary}.\n"
                f"This represents a positive commercial outcome."
            )

        if risk_candidate:
            risk = (
                
                f"{risk_candidate.vendor}\n"
                f"{risk_candidate.commentary}."
            )

        if decision_candidate:
            decision_required = (
                f"{decision_candidate.vendor}\n"
                f"{decision_candidate.commentary}.\n"
                f"Progress is dependent on a pending approval or decision."
            )

        financial_risk_candidates = sorted (
            financial_risk_candidates,
            key=lambda c: abs(c.costout),
            reverse=True,
        )
        
        additional_financial_risks = []

        for candidate in financial_risk_candidates[1:]:

            if candidate.commentary:

                additional_financial_risks.append (
                    f"• {candidate.vendor}\n"
                    f"{candidate.commentary}\n"
                    f"Financial impact currently reflected: "
                    f"${abs(candidate.costout):,.0f}"
            )

            else:

                additional_financial_risks.append (
                    f"• {candidate.vendor}\n"
                    f"Financial impact currently reflected: "
                    f"${abs(candidate.costout):,.0f}"
                )

        if financial_candidate:

            if financial_candidate.commentary:
                financial = (
                    f"{financial_candidate.vendor}\n"
                    f"{financial_candidate.commentary}.\n"
                    f"Financial impact is currently estimated at "
                    f"${abs(financial_candidate.costout):,.0f}."
            )

            else:
                financial = (
                    f"{financial_candidate.vendor}\n"
                    f"Approximately ${abs(financial_candidate.costout):,.0f} "
                    f"of additional cost is currently reflected in the position."
            )

            if additional_financial_risks:
                financial += (
                    "\n\nOther material financial risks:\n\n"
                    + "\n\n".join (additional_financial_risks)
                )

    document = render_leadership_insights(
        major_win = major_win,
        risk = risk,
        decision_required = decision_required,
        financial = financial,
        delivery_progress = delivery_progress,
        portfolio_message = portfolio_message,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path
