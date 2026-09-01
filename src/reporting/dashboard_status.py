"""
dashboard_status.py

Utilities for extracting leadership-reporting commentary
from the IT Simplification dashboard.
"""

from pathlib import Path
import re

import pandas as pd


def load_dashboard_statuses(path: str | Path) -> pd.DataFrame:
    """
    Load the Simplified view worksheet.
    """

    return pd.read_excel(
        path,
        sheet_name="Simplified view",
        engine="openpyxl",
    )


def _ari_note_columns(df: pd.DataFrame) -> list[str]:
    """
    Return all Ari note columns ordered newest first.

    Examples:
        Ari's notes: 17/8
        Ari's notes: 24/8
        Ari's notes: 31/8
        Ari's notes: 6/9
    """

    columns = [
        column
        for column in df.columns
        if str(column).startswith("Ari's notes:")
    ]

    def sort_key(column: str) -> tuple[int, int]:
        match = re.search(r"(\d{1,2})/(\d{1,2})", column)

        if not match:
            return (0, 0)

        day = int(match.group(1))
        month = int(match.group(2))

        return (month, day)

    return sorted(
        columns,
        key=sort_key,
        reverse=True,
    )


def get_actionable_statuses(
    path: str | Path,
) -> pd.DataFrame:
    """
    Return one current commentary field per contract.

    Priority:
        newest Ari note
        -> older Ari notes
        -> Status

    Returns:
        Vendor
        Contract
        latest_commentary
    """

    df = load_dashboard_statuses(path).copy()

    note_priority = _ari_note_columns(df)

    if "Status" in df.columns:
        note_priority.append("Status")

    def select_commentary(row) -> str:
        for column in note_priority:

            if column not in row.index:
                continue

            value = str(row[column]).strip()

            if value and value.lower() != "nan":
                return value

        return ""

    df["latest_commentary"] = df.apply(
        select_commentary,
        axis=1,
    )

    return (
        df[
            [
                "Vendor",
                "Contract",
                "latest_commentary",
            ]
        ]
        .copy()
        .reset_index(drop=True)
    )

def get_noteworthy_contracts(
    path: str | Path,
    budget_threshold: float = 50000,
    variance_threshold: float = 20000,
):
    """
    Return leadership-worthy contracts.

    Current heuristic:
        - budget >= 50000
        OR
        - absolute costout >= 20000
    """

    df = load_dashboard_statuses(path).copy()

    noteworthy = (
        (
            pd.to_numeric(
                df["V1 budget"],
                errors="coerce"
            ).fillna(0) 
            >= budget_threshold
        )
        |
        (
            pd.to_numeric(
                df["Costout"], 
                errors="coerce"
            )
            .fillna(0)
            .abs()
            >= variance_threshold
        )
    )

    return df.loc[noteworthy].copy()
