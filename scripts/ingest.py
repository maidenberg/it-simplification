"""
ingest.py — Data ingestion module for the IT Simplification Communications Engine.

Responsibility:
    Read an Excel (.xlsx) file containing vendor data, validate its structure
    against the expected data model, normalise column names and types, and
    return a clean pandas DataFrame ready for analysis.
"""

from pathlib import Path

import pandas as pd


# Expected columns mapped to their normalised snake_case names.
EXPECTED_COLUMNS = {
    "vendor": "vendor",
    "category": "category",
    "budget": "budget",
    "renewal price": "renewal_price",
    "cost out": "cost_out",
    "finalised": "finalised",
    "quarter": "quarter",
}

VALID_CATEGORIES = {"licensing", "consumption", "microsoft", "new spend"}
VALID_QUARTERS = {"q1", "q2", "q3", "q4"}


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase and strip column headers, then map to snake_case names."""
    df.columns = df.columns.str.strip().str.lower()

    missing = set(EXPECTED_COLUMNS.keys()) - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(sorted(missing))}"
        )

    df = df.rename(columns=EXPECTED_COLUMNS)
    return df


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce columns to their expected types."""
    # Numeric columns
    for col in ("budget", "renewal_price", "cost_out"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Boolean-like finalised column
    df["finalised"] = (
        df["finalised"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"yes": True, "true": True, "1": True, "y": True, "no": False, "false": False, "0": False, "n": False, "nan": False})
    )

    # Categorical columns — lowercase for consistent comparison
    df["category"] = df["category"].astype(str).str.strip().str.lower()
    df["quarter"] = df["quarter"].astype(str).str.strip().str.lower()

    return df


def _drop_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows where vendor is missing or empty (trailing blank rows)."""
    df = df[df["vendor"].notna() & (df["vendor"].astype(str).str.strip() != "")]
    return df.reset_index(drop=True)


def load_vendor_data(filepath: str | Path) -> pd.DataFrame:
    """
    Load and validate vendor data from an Excel file.

    Parameters
    ----------
    filepath : str or Path
        Path to the .xlsx file containing vendor data.

    Returns
    -------
    pd.DataFrame
        Validated DataFrame with normalised column names and types.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If required columns are missing from the spreadsheet.
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Input file not found: {filepath}")

    if not filepath.suffix.lower() == ".xlsx":
        raise ValueError(f"Expected an .xlsx file, got: {filepath.suffix}")

    df = pd.read_excel(
        filepath,
        sheet_name="Simplified view",
        engine="openpyxl")

    df = df.rename (
        columns={
            "Vendor": "vendor",
            "Category": "category",
            "V1 budget": "budget",
            "Renewal price": "renewal price",
            "Costout": "cost out",
            "Finalised?": "finalised"
        }
    )

    df["quarter"] = (
        "Q"
        + pd.to_datetime(
            df["When contract is up"],
            errors="coerce"
        ).dt.quarter.astype(str)
    )
    
    df = _normalise_columns(df)
    df = _drop_empty_rows(df)
    df = _coerce_types(df)

    return df
