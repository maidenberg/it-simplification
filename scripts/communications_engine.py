"""
communications_engine.py — Analysis and content structuring module.

Responsibility:
    Accept a validated DataFrame of vendor data, perform portfolio-level and
    vendor-level analysis, and produce a structured dictionary containing the
    five sections of the weekly update:

        - executive_summary
        - metrics
        - highlights
        - risks
        - next_steps

    Vendor-level analysis is internal — it feeds the highlights and risks
    sections but is not exposed as separate communications.
"""

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class WeeklyUpdate:
    """Structured content for a single weekly IT Simplification update."""

    executive_summary: str = ""
    metrics: dict = field(default_factory=dict)
    highlights: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal analysis helpers
# ---------------------------------------------------------------------------

def _calculate_metrics(df: pd.DataFrame) -> dict:
    """Compute portfolio-level metrics from vendor data."""
    total_savings = df["cost_out"].sum()
    finalised_savings = df.loc[df["finalised"] == True, "cost_out"].sum()  # noqa: E712
    savings_pipeline = df.loc[df["finalised"] == False, "cost_out"].sum()  # noqa: E712
    total_budget = df["budget"].sum()
    total_renewal = df["renewal_price"].sum()
    vendor_count = df["vendor"].nunique()

    return {
        "total_savings_identified": total_savings,
        "finalised_savings": finalised_savings,
        "savings_pipeline": savings_pipeline,
        "total_budget": total_budget,
        "total_renewal_price": total_renewal,
        "vendor_count": vendor_count,
    }


def _identify_highlights(df: pd.DataFrame, top_n: int = 5) -> list[str]:
    """
    Identify the top achievements for the highlights section.

    Rules:
    - Finalised items with the largest cost_out values are key achievements.
    - Large unfinalised opportunities that are notable are also highlighted.
    """
    highlights = []

    # Top finalised savings (key achievements)
    finalised = df[df["finalised"] == True].sort_values("cost_out", ascending=False)  # noqa: E712
    for _, row in finalised.head(3).iterrows():
        highlights.append(
            f"{row['vendor']} — ${row['cost_out']:,.0f} savings finalised ({row['category']})"
        )

    # Largest pipeline opportunities not yet finalised
    pipeline = df[df["finalised"] == False].sort_values("cost_out", ascending=False)  # noqa: E712
    for _, row in pipeline.head(top_n - len(highlights)).iterrows():
        highlights.append(
            f"{row['vendor']} — ${row['cost_out']:,.0f} opportunity identified ({row['category']})"
        )

    return highlights[:top_n]


def _identify_risks(df: pd.DataFrame) -> list[str]:
    """
    Identify items to flag in the risks section.

    Rules:
    - Unfinalised items where cost_out is high relative to the portfolio
      represent execution risk (savings may not be realised).
    - Items with zero cost_out but significant budget may indicate
      unexplored opportunity or data gaps.
    """
    risks = []

    # Large unfinalised items — execution risk
    pipeline = df[df["finalised"] == False].sort_values("cost_out", ascending=False)  # noqa: E712
    total_pipeline = pipeline["cost_out"].sum()

    for _, row in pipeline.iterrows():
        if total_pipeline > 0 and row["cost_out"] / total_pipeline > 0.25:
            risks.append(
                f"{row['vendor']} — ${row['cost_out']:,.0f} not yet finalised "
                f"(represents significant pipeline concentration)"
            )

    # Vendors with budget but no identified savings
    no_savings = df[(df["cost_out"] == 0) & (df["budget"] > 0)]
    if len(no_savings) > 0:
        vendor_names = ", ".join(no_savings["vendor"].tolist()[:3])
        risks.append(
            f"{len(no_savings)} vendor(s) with budget but no identified savings: {vendor_names}"
        )

    if not risks:
        risks.append("No significant risks identified this period.")

    return risks


def _generate_executive_summary(metrics: dict) -> str:
    """Produce a one-paragraph executive summary from calculated metrics."""
    total = metrics["total_savings_identified"]
    finalised = metrics["finalised_savings"]
    pipeline = metrics["savings_pipeline"]
    vendors = metrics["vendor_count"]

    finalised_pct = (finalised / total * 100) if total > 0 else 0

    summary = (
        f"The IT Simplification program has identified ${total:,.0f} in total savings "
        f"across {vendors} vendors. "
        f"${finalised:,.0f} ({finalised_pct:.0f}%) has been finalised, "
        f"with ${pipeline:,.0f} remaining in the pipeline. "
    )

    if finalised_pct >= 75:
        summary += "The program is well advanced with the majority of savings confirmed."
    elif finalised_pct >= 50:
        summary += "Good progress continues with over half of identified savings confirmed."
    else:
        summary += "Focus remains on converting pipeline opportunities into confirmed savings."

    return summary


def _default_next_steps() -> list[str]:
    """
    Provide placeholder next steps.

    Note: Next steps are forward-looking and cannot be derived from the data.
    These are placeholders for the reviewer to complete.
    """
    return [
        "Continue vendor negotiations for pipeline items.",
        "Review unfinalised opportunities for Q-on-Q progress.",
        "[To be completed by reviewer]",
    ]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def generate_weekly_update(df: pd.DataFrame) -> WeeklyUpdate:
    """
    Analyse vendor data and produce structured content for the weekly update.

    Parameters
    ----------
    df : pd.DataFrame
        Validated vendor data (output from ingest.load_vendor_data).

    Returns
    -------
    WeeklyUpdate
        Dataclass containing executive_summary, metrics, highlights, risks,
        and next_steps — ready for rendering by the draft generator.
    """
    metrics = _calculate_metrics(df)
    highlights = _identify_highlights(df)
    risks = _identify_risks(df)
    executive_summary = _generate_executive_summary(metrics)
    next_steps = _default_next_steps()

    return WeeklyUpdate(
        executive_summary=executive_summary,
        metrics=metrics,
        highlights=highlights,
        risks=risks,
        next_steps=next_steps,
    )
