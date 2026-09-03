"""
leadership_email.py

Generate a concise leadership email from existing reporting artefacts.

Inputs:
    leadership_insights.txt
    risks_watchouts.txt

Output:
    leadership_email.txt

No analytics.
No ranking.
No scoring.
No candidate generation.

Formatting only.
"""

from pathlib import Path


class LeadershipEmailError(Exception):
    """Raised when a required email input artefact is missing."""

LEADERSHIP_EMAIL_FILENAME = "leadership_email.txt"

def _format_email_item(text: str) -> str:
    """Render vendor/commentary content onto a single line."""
    return text.replace(
        "\n",
        ": ",
    )

def _read_required(path, label: str) -> str:
    """Read a required artefact, failing fast if it is missing."""
    path = Path(path)

    if not path.exists():
        raise LeadershipEmailError(
            f"Required {label} artefact not found: {path}. "
            f"Leadership email cannot be generated."
        )

    return path.read_text(encoding="utf-8")

def render_leadership_email(
    executive_watchout: str | None,
    financial_watchout: str | None,
    watchlist: list[str],
    comparison_label: str,
) -> str:
    """Render a concise leadership email."""

    lines = [
        "Subject: IT Simplification Weekly Update",
        comparison_label,
        "",
        "Hi Lewis,",
        "",
        "Please see this week's IT Simplification watchouts and items to monitor.",
        "",
        "",
    ]

    if executive_watchout:
        lines.append ("Executive watchout:")
        lines.append("")
        formatted_watchout = _format_email_item(executive_watchout)
        lines.append(f"• {formatted_watchout}")
        lines.append("")
        lines.append("")

    if financial_watchout:
        lines.append("Financial watchout:")
        lines.append ("")
        formatted_watchout = _format_email_item (financial_watchout)
        lines.append(f"• {formatted_watchout}")
        lines.append("")
        lines.append("")
      
    if watchlist:
        lines.append("")
        lines.append("Items to monitor:")
        lines.append("")

        for item in watchlist:
            formatted_item = _format_email_item (item)
            lines.append(f"• {formatted_item}")

    lines.append("")
    lines.append("Regards,")
    lines.append("Ari's brilliant IT Simplification Automation")

    return "\n".join(lines)

def _extract_section(
    text: str,
    heading: str,
) -> str | None:
    """Extract a section body from a reporting artefact."""
    
    lines = text.splitlines()

    for i, line in enumerate(lines):
        if line.strip() == heading:

            collected = []

            for next_line in lines[i + 1:]:

                if next_line.strip().isupper():
                    break

                collected.append(next_line)

            section = "\n".join(collected).strip()

            if section:
                return section

    return None

def _extract_watchlist(
    risks_text: str,
) -> list[str]:
    """Extract watchlist entries from risks_watchouts.txt."""

    watchouts = _extract_section(
        risks_text,
        "WATCHOUTS",
    )

    if not watchouts:
        return []

    watchlist = []

    for block in watchouts.split("\n\n"):

        cleaned_lines = []

        for line in block.splitlines():

            stripped = line.strip()

            if stripped and set(stripped) == {"-"}:
                continue

            cleaned_lines.append(line)

        cleaned_block = "\n".join(cleaned_lines).strip()

        if cleaned_block:
            watchlist.append(cleaned_block)

    return watchlist

def _extract_executive_watchout(
    insights_text: str,
) -> str | None:
    """Extract the executive watchout from leadership_insights.txt."""

    return _extract_section(
        insights_text,
        "EXECUTIVE WATCHOUT",
    )

def _extract_financial_watchout(
    insights_text: str,
) -> str | None:
    """Extract the financial watchout from leadership_insights.txt."""

    return _extract_section(
        insights_text,
        "FINANCIAL WATCHOUT",
    )

def generate_leadership_email(
    leadership_insights_path,
    risks_watchouts_path,
    output_path,
    comparison_label: str,
):
    """Generate leadership email content from existing artefacts."""

    insights_text = _read_required(
        leadership_insights_path,
        "leadership insights",
    )

    risks_text = _read_required(
        risks_watchouts_path,
        "risks & watchouts",
    )

    executive_watchout = _extract_executive_watchout(
        insights_text,
    )

    financial_watchout = _extract_financial_watchout(
        insights_text,
    )

    watchlist = _extract_watchlist(
        risks_text,
    )

    email_content = render_leadership_email(
        executive_watchout=executive_watchout,
        financial_watchout=financial_watchout,
        watchlist=watchlist,
        comparison_label=comparison_label,
    )

    output_path = Path(output_path)

    output_path.write_text(
        email_content,
        encoding="utf-8",
    )

    return email_content