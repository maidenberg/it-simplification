"""
compare_snapshots.py — Snapshot comparison module for the IT Simplification
Communications Engine.

Responsibility:
    Load individual weekly snapshot worksheets so they can be compared
    week-on-week. Each snapshot is stored as a separate worksheet within the
    workbook (e.g. "Snapshot Wk 1", "Snapshot Wk 2"), so load_snapshot targets
    a specific sheet by name.

    Vendor-data parsing (locating the vendor table, normalising columns/types)
    and comparison logic (deltas, movements, newly finalised items) are
    intentionally not implemented yet.
"""

from pathlib import Path

import pandas as pd


def load_snapshot(filepath: str | Path, sheet_name: str) -> pd.DataFrame:
    """
    Load a single snapshot worksheet from an Excel workbook.

    Reads the specified worksheet as-is and prints the resulting DataFrame
    shape. Vendor-data parsing (header offset, column mapping, type coercion)
    is intentionally not performed yet.

    Parameters
    ----------
    filepath : str or Path
        Path to the .xlsx workbook containing the snapshot worksheets.
    sheet_name : str
        Name of the worksheet to load (e.g. "Snapshot Wk 1").

    Returns
    -------
    pd.DataFrame
        The raw contents of the specified worksheet.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Input file not found: {filepath}")

    df = pd.read_excel(filepath, sheet_name=sheet_name, engine="openpyxl")

    print(f"Loaded worksheet '{sheet_name}' with shape {df.shape}")

    return df


def _dedupe_columns(columns: list) -> list:
    """
    Return a copy of ``columns`` with duplicate names made unique.

    The first occurrence of a name is kept as-is; the second and later
    occurrences get a numeric suffix, e.g. "V1 budget", "V1 budget_2",
    "V1 budget_3".

    Parameters
    ----------
    columns : list
        The raw column labels detected from a block's header row.

    Returns
    -------
    list
        Column labels with duplicates disambiguated by a numeric suffix.
    """
    seen: dict = {}
    result = []
    for name in columns:
        count = seen.get(name, 0) + 1
        seen[name] = count
        if count == 1:
            result.append(name)
        else:
            result.append(f"{name}_{count}")
    return result


def extract_vendor_data(snapshot_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract and combine all vendor tables from a raw snapshot DataFrame.

    The snapshot is a dashboard layout, so vendor data is split across several
    blocks. Each block begins with a header row whose first two columns read
    "Vendor" and "Contract". For each detected header this function captures the
    rows below it, stopping at the row before the next header (or the end of the
    DataFrame for the final block), ignores blank rows, applies the detected
    header row as that block's column names, and concatenates all blocks into a
    single DataFrame.

    Blocks may have slightly different headers (for example, one block includes
    a "Contract date" column). Concatenation aligns by column name and fills any
    missing columns with NaN.

    A block's header row can also repeat the same label (for example the vendor
    detail columns and a trailing summary repeat "V1 budget", "Renewal price"
    and "Costout"). Duplicate names within a block are made unique by appending
    a numeric suffix (e.g. "V1 budget", "V1 budget_2") before the block
    DataFrame is created.

    Because load_snapshot uses the sheet's first row as the DataFrame header,
    spreadsheet columns A and B correspond to the DataFrame's first two columns
    by position (iloc[:, 0] and iloc[:, 1]), not by name.

    Comparison logic is intentionally not performed.

    Parameters
    ----------
    snapshot_df : pd.DataFrame
        The raw DataFrame returned by load_snapshot().

    Returns
    -------
    pd.DataFrame
        A single DataFrame combining all vendor blocks, using each block's
        detected header row for column names.
    """
    if snapshot_df.shape[1] < 2:
        print("DataFrame has fewer than 2 columns; cannot locate vendor tables.")
        return pd.DataFrame()

    col_a = snapshot_df.iloc[:, 0].astype(str).str.strip()
    col_b = snapshot_df.iloc[:, 1].astype(str).str.strip()

    # Positional index (0-based) of each header row within the DataFrame.
    header_positions = [
        pos for pos in range(len(snapshot_df))
        if col_a.iloc[pos] == "Vendor" and col_b.iloc[pos] == "Contract"
    ]

    if not header_positions:
        print("Found 0 vendor-table header row(s); nothing to extract.")
        return pd.DataFrame()

    total_rows = len(snapshot_df)
    blocks = []

    for i, pos in enumerate(header_positions):
        # Block body runs from the row after the header to the row before the
        # next header (or the end of the DataFrame for the final block).
        start = pos + 1
        end = header_positions[i + 1] if i + 1 < len(header_positions) else total_rows

        # Detected header row -> column names for this block.
        block_columns = snapshot_df.iloc[pos].tolist()

        # Make duplicate column names unique by appending _2, _3, ... to the
        # second and later occurrences of each name.
        block_columns = _dedupe_columns(block_columns)

        print(f"  Block {i + 1} columns: {block_columns}")

        block = snapshot_df.iloc[start:end].copy()
        block.columns = block_columns

        # Ignore blank rows (all cells NaN/empty).
        block = block.dropna(how="all")
        block = block[~(block.astype(str).apply(lambda s: s.str.strip()).eq("").all(axis=1))]

        if not block.empty:
            blocks.append(block)

    if not blocks:
        combined = pd.DataFrame()
    else:
        combined = pd.concat(blocks, ignore_index=True)

    # Remove rows where Contract (second column by position) is blank/null.
    blank_tokens = {"", "nan", "none", "nat"}
    rows_before = len(combined)
    if combined.shape[1] >= 2:
        contract = combined.iloc[:, 1].astype(str).str.strip()
        contract_blank = combined.iloc[:, 1].isna() | contract.str.lower().isin(blank_tokens)
        combined = combined[~contract_blank].reset_index(drop=True)
    rows_after = len(combined)

    print(f"Rows before cleanup: {rows_before}")
    print(f"Rows after cleanup (blank/null Contract removed): {rows_after}")

    print(f"Extracted columns: {list(combined.columns)}")

    print("\nFirst 20 rows:")
    print(combined.head(20))

    print("\nLast 20 rows:")
    print(combined.tail(20))

    print(f"\nTotal extracted rows: {len(combined)}")

    # Count remaining rows with a blank/null Vendor (Contract already cleaned).
    if combined.shape[1] >= 2:
        vendor = combined.iloc[:, 0].astype(str).str.strip()
        vendor_blank = combined.iloc[:, 0].isna() | vendor.str.lower().isin(blank_tokens)
        print(f"Rows with blank/null Vendor (after cleanup): {int(vendor_blank.sum())}")
    else:
        print("Combined DataFrame has fewer than 2 columns; cannot count blanks.")

    return combined


def compare_snapshots(previous_df: pd.DataFrame, current_df: pd.DataFrame) -> dict:
    """
    Compare two vendor-data snapshots.

    Returns each cleaned vendor snapshot's record count and the delta between
    them. Vendor additions and costout changes are intentionally not
    implemented yet.

    Parameters
    ----------
    previous_df : pd.DataFrame
        The previous week's cleaned vendor snapshot (from extract_vendor_data).
    current_df : pd.DataFrame
        The current week's cleaned vendor snapshot (from extract_vendor_data).

    Returns
    -------
    dict
        A dictionary with each snapshot's record count and the count delta.
    """
    return {
        "previous_count": len(previous_df),
        "current_count": len(current_df),
        "count_delta": len(current_df) - len(previous_df),
    }


if __name__ == "__main__":
    # Temporary manual test harness.
    # Loads the two snapshot worksheets and prints the comparison result.
    # Defaults target the sample workbook so this runs out of the box;
    # pass a workbook path and two sheet names to compare different snapshots.
    import sys

    filepath = sys.argv[1] if len(sys.argv) > 1 else "data/Fake vendor data.xlsx"
    previous_sheet = sys.argv[2] if len(sys.argv) > 2 else "Snapshot Wk 1"
    current_sheet = sys.argv[3] if len(sys.argv) > 3 else "Snapshot Wk 2"

    previous_df = load_snapshot(filepath, previous_sheet)
    current_df = load_snapshot(filepath, current_sheet)

    print(f"\n[{previous_sheet}] extracted vendor data:")
    previous_vendors = extract_vendor_data(previous_df)

    print(f"\n[{current_sheet}] extracted vendor data:")
    current_vendors = extract_vendor_data(current_df)

    result = compare_snapshots(previous_vendors, current_vendors)
    print(f"\n{result}")
