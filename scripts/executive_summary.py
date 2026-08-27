"""
executive_summary.py — Executive Summary Renderer (Milestone 3A).

Responsibility:
    Convert the movement-analysis result produced by compare_snapshots() into a
    deterministic executive-summary text block. This is a pure reporting layer.
    Its only responsibilities are field mapping, currency formatting, fixed
    section ordering, and top-mover rendering.

    No business logic is added here: no insights, commentary, recommendations,
    risks, watchouts, narrative, trend analysis, or extra calculations. Every
    value is taken directly from the supplied analysis result.

Input mapping:
    compare_snapshots() returns snake_case keys. This renderer maps them to the
    reporting fields:
        contracts_compared    <- previous_count
        changed_contracts     <- changed_count
        increase_count        <- increase_count
        decrease_count        <- decrease_count
        total_positive_delta  <- total_positive_delta
        total_negative_delta  <- total_negative_delta
        net_delta             <- net_delta
        top movers            <- top_increases followed by top_decreases
                                 (each already ranked by the analysis layer;
                                 no re-ranking is performed)
"""

SEPARATOR = "=" * 50


def _format_currency(value: float) -> str:
    """Format a value as currency with a thousands separator and 2 decimals."""
    return f"{float(value):,.2f}"


def _format_mover(mover: dict) -> str:
    """Render a single top-mover record as 'Contract: $delta'."""
    return f"{mover['contract']}: ${_format_currency(mover['delta'])}"


def _top_movers(analysis: dict) -> list:
    """
    Build the ordered top-movers list, preserving the analysis-layer ranking.

    Increases (already sorted largest-first) precede decreases (already sorted
    most-negative-first). No re-sorting is applied.
    """
    return list(analysis.get("top_increases", [])) + list(analysis.get("top_decreases", []))


def generate_executive_summary(analysis: dict) -> str:
    """
    Render the deterministic executive summary from a movement-analysis result.

    Parameters
    ----------
    analysis : dict
        The result object returned by compare_snapshots().

    Returns
    -------
    str
        The formatted executive summary with fixed section ordering.
    """
    contracts_compared = analysis["previous_count"]
    changed_contracts = analysis["changed_count"]
    increase_count = analysis["increase_count"]
    decrease_count = analysis["decrease_count"]
    total_positive_delta = _format_currency(analysis["total_positive_delta"])
    total_negative_delta = _format_currency(analysis["total_negative_delta"])
    net_delta = _format_currency(analysis["net_delta"])

    movers = _top_movers(analysis)

    lines = [
        SEPARATOR,
        "IT SIMPLIFICATION WEEKLY MOVEMENT SUMMARY",
        SEPARATOR,
        "",
        f"Contracts compared: {contracts_compared}",
        f"Contracts with movement: {changed_contracts}",
        "",
        f"Increases: {increase_count}",
        f"Decreases: {decrease_count}",
        "",
        f"Total positive delta: ${total_positive_delta}",
        f"Total negative delta: ${total_negative_delta}",
        "",
        f"Net delta: ${net_delta}",
        "",
        "Top Movements",
        "-------------",
        "",
    ]

    for i in range(3):
        if i < len(movers):
            lines.append(f"{i + 1}. {_format_mover(movers[i])}")
        else:
            lines.append(f"{i + 1}.")

    return "\n".join(lines)


def _format_signed_mover(mover: dict) -> str:
    """
    Render a mover as 'Contract Name (+$X.XX)' or 'Contract Name (-$X.XX)'.

    The sign reflects the delta supplied by the analysis layer; currency is
    formatted with a thousands separator and 2 decimals using the magnitude.
    """
    delta = float(mover["delta"])
    sign = "-" if delta < 0 else "+"
    magnitude = _format_currency(abs(delta))
    return f"{mover['contract']} ({sign}${magnitude})"


def generate_key_movements(analysis: dict) -> str:
    """
    Render the deterministic "Key Movements" section from a movement-analysis
    result.

    This is a pure presentation layer: it renders the movers already ranked by
    the analysis layer. No business logic, insights, commentary, or additional
    calculation is performed. The mover order is exactly as supplied
    (top_increases followed by top_decreases).

    Parameters
    ----------
    analysis : dict
        The result object returned by compare_snapshots().

    Returns
    -------
    str
        The formatted Key Movements section.
    """
    movers = _top_movers(analysis)

    lines = [
        "KEY MOVEMENTS",
        "-------------",
        "",
    ]

    for i in range(3):
        if i < len(movers):
            lines.append(f"{i + 1}. {_format_signed_mover(movers[i])}")
        else:
            lines.append(f"{i + 1}.")

    return "\n".join(lines)


if __name__ == "__main__":
    # Sample output using the current validated dataset.
    import io
    import contextlib
    from pathlib import Path
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from compare_snapshots import load_snapshot, extract_vendor_data, compare_snapshots

    filepath = "data/Fake vendor data.xlsx"

    # Suppress upstream extraction/diagnostic prints for a clean sample.
    with contextlib.redirect_stdout(io.StringIO()):
        previous = extract_vendor_data(load_snapshot(filepath, "Snapshot Wk 1"))
        current = extract_vendor_data(load_snapshot(filepath, "Snapshot Wk 2"))
        analysis = compare_snapshots(previous, current)

    print(generate_executive_summary(analysis))
    print()
    print(generate_key_movements(analysis))
