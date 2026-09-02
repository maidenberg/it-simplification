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
import sys
import re
from datetime import datetime

sys.path.append(
    str(Path(__file__).resolve().parents[1] / "src")
)

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

def find_latest_snapshot_sheets(filepath: str | Path) -> tuple[str, str]:
    """Return the previous and current snapshot worksheet names."""
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Input file not found: {filepath}")

    with pd.ExcelFile(filepath, engine="openpyxl") as workbook:
        snapshot_sheets = []

        for sheet_name in workbook.sheet_names:
            match = re.fullmatch(r"Snapshot (\d{1,2})-(\d{1,2})", sheet_name.strip())
            if match:
                day = int(match.group(1))
                month = int(match.group(2))
                snapshot_sheets.append(
                    (datetime(2000, month, day), sheet_name)
            )

    if len(snapshot_sheets) < 2:
        raise ValueError(
            f"At least two 'Snapshot D-M' worksheets are required in {filepath}."
        )

    snapshot_sheets.sort(key=lambda item: item[0])

    previous_sheet = snapshot_sheets[-2][1]
    current_sheet = snapshot_sheets[-1][1]

    return previous_sheet, current_sheet

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

        section_name = ""

        if pos > 0:
            section_name = str(
                snapshot_df.iloc[pos - 1, 0]
            ).strip()
        
        # Detected header row -> column names for this block.
        block_columns = snapshot_df.iloc[pos].tolist()

        # Make duplicate column names unique by appending _2, _3, ... to the
        # second and later occurrences of each name.
        block_columns = _dedupe_columns(block_columns)

        print(f"  Block {i + 1} columns: {block_columns}")

        if "cost-out to date" in section_name.lower():
            continue
        
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

    # Keep valid vendor rows even when Contract is blank. For comparison purposes,
    # use a stable vendor-based identifier so financially valid movements are not
    # silently discarded.
    blank_tokens = {"", "nan", "none", "nat"}
    rows_before = len(combined)
    if combined.shape[1] >= 2:
        vendor = combined.iloc[:, 0].astype(str).str.strip()
        contract = combined.iloc[:, 1].astype(str).str.strip()
	
        vendor_blank = (
        combined.iloc[:, 0].isna()
        | vendor.str.lower().isin(blank_tokens)
        )
        contract_blank = (
            combined.iloc[:, 1].isna()
            | contract.str.lower().isin(blank_tokens)
        )
        
        # Rows without a vendor are not usable.
        combined = combined[~vendor_blank].copy()

        # Preserve blank-contract rows using the vendor as a stable identifier.
        vendor = combined.iloc[:, 0].astype(str).str.strip()
        contract = combined.iloc[:, 1].astype(str).str.strip()
        contract_blank = (
            combined.iloc[:, 1].isna()
            | contract.str.lower().isin(blank_tokens)
        )
        combined.loc[contract_blank, combined.columns[1]] = (
            "[No Contract] " + vendor[contract_blank]
        )

    rows_after = len(combined)

    print(f"Rows before cleanup: {rows_before}")
    print(f"Rows after cleanup (blank/null Contract removed): {rows_after}")

    print(f"Extracted columns: {list(combined.columns)}")

    print(f"\nTotal extracted rows: {len(combined)}")

    # Count remaining rows with a blank/null Vendor (Contract already cleaned).
    if combined.shape[1] >= 2:
        vendor = combined.iloc[:, 0].astype(str).str.strip()
        vendor_blank = combined.iloc[:, 0].isna() | vendor.str.lower().isin(blank_tokens)
        print(f"Rows with blank/null Vendor (after cleanup): {int(vendor_blank.sum())}")
    else:
        print("Combined DataFrame has fewer than 2 columns; cannot count blanks.")

    return combined


def _contract_set(df: pd.DataFrame) -> set:
    """
    Return the unique set of non-blank contract identifiers from a cleaned
    vendor DataFrame.

    The Contract column is located by name ("Contract") when present, otherwise
    by position (the second column). Blank/null values are excluded.

    Parameters
    ----------
    df : pd.DataFrame
        A cleaned vendor snapshot (from extract_vendor_data).

    Returns
    -------
    set
        Unique contract identifiers.
    """
    if df.shape[1] < 2:
        return set()

    if "Contract" in df.columns:
        contract = df["Contract"]
    else:
        contract = df.iloc[:, 1]

    blank_tokens = {"", "nan", "none", "nat"}
    values = contract.astype(str).str.strip()
    mask = contract.notna() & ~values.str.lower().isin(blank_tokens)
    return set(values[mask])


def _costout_by_contract(df: pd.DataFrame) -> dict:
    """
    Return a mapping of contract identifier -> primary Costout (numeric).

    The Contract column is located by name ("Contract") when present, otherwise
    by position (the second column). The primary Costout column is the one named
    exactly "Costout" (not the deduped summary copy "Costout_2"). Costout values
    are coerced to numeric; non-numeric/blank values become 0.0.

    Parameters
    ----------
    df : pd.DataFrame
        A cleaned vendor snapshot (from extract_vendor_data).

    Returns
    -------
    dict
        Mapping of contract identifier to its numeric primary Costout.
    """
    if df.shape[1] < 2 or "Costout" not in df.columns:
        return {}

    contract = df["Contract"] if "Contract" in df.columns else df.iloc[:, 1]
    costout = pd.to_numeric(df["Costout"], errors="coerce").fillna(0.0)

    blank_tokens = {"", "nan", "none", "nat"}
    keys = contract.astype(str).str.strip()
    mask = contract.notna() & ~keys.str.lower().isin(blank_tokens)

    return dict(zip(keys[mask], costout[mask]))


def compare_snapshots(previous_df: pd.DataFrame, current_df: pd.DataFrame) -> dict:
    """
    Compare two cleaned vendor snapshots at the contract level.

    Builds a unique set of contracts for each snapshot, identifies which
    contracts were added, removed, or remained present, and — for contracts
    present in both — detects changes in the primary Costout value.

    Movement classification, summaries, insights and totals are intentionally
    not implemented in this milestone.

    Parameters
    ----------
    previous_df : pd.DataFrame
        The previous week's cleaned vendor snapshot (from extract_vendor_data).
    current_df : pd.DataFrame
        The current week's cleaned vendor snapshot (from extract_vendor_data).

    Returns
    -------
    dict
        Record counts, count delta, and contract-level added/removed/unchanged
        results.
    """
    previous_contracts = _contract_set(previous_df)
    current_contracts = _contract_set(current_df)

    added_contracts = sorted(current_contracts - previous_contracts)
    removed_contracts = sorted(previous_contracts - current_contracts)
    unchanged_contracts = current_contracts & previous_contracts

    # Detect Costout changes for contracts present in both snapshots.
    previous_costout = _costout_by_contract(previous_df)
    current_costout = _costout_by_contract(current_df)

    changed_contracts = []
    increase_count = 0
    decrease_count = 0
    for contract in sorted(unchanged_contracts):
        prev_val = float(previous_costout.get(contract, 0.0))
        curr_val = float(current_costout.get(contract, 0.0))
        delta = curr_val - prev_val
        if delta != 0:
            if delta > 0:
                movement_type = "increase"
                increase_count += 1
            elif delta < 0:
                movement_type = "decrease"
                decrease_count += 1
            else:
                movement_type = "unchanged"
            changed_contracts.append({
                "contract": contract,
                "previous_costout": prev_val,
                "current_costout": curr_val,
                "delta": delta,
                "movement_type": movement_type,
            })

    # Portfolio-level aggregation of Costout movements.
    total_positive_delta = sum(
        r["delta"] for r in changed_contracts if r["movement_type"] == "increase"
    )
    total_negative_delta = sum(
        r["delta"] for r in changed_contracts if r["movement_type"] == "decrease"
    )
    net_delta = total_positive_delta + total_negative_delta

    # Top movers: increases largest-first, decreases most-negative-first.
    top_increases = sorted(
        (r for r in changed_contracts if r["movement_type"] == "increase"),
        key=lambda r: r["delta"],
        reverse=True,
    )
    top_decreases = sorted(
        (r for r in changed_contracts if r["movement_type"] == "decrease"),
        key=lambda r: r["delta"],
    )

    return {
        "previous_count": len(previous_df),
        "current_count": len(current_df),
        "count_delta": len(current_df) - len(previous_df),
        "added_contracts": added_contracts,
        "removed_contracts": removed_contracts,
        "added_count": len(added_contracts),
        "removed_count": len(removed_contracts),
        "unchanged_count": len(unchanged_contracts),
        "changed_contracts": changed_contracts,
        "changed_count": len(changed_contracts),
        "increase_count": increase_count,
        "decrease_count": decrease_count,
        "total_positive_delta": float(total_positive_delta),
        "total_negative_delta": float(total_negative_delta),
        "net_delta": float(net_delta),
        "top_increases": top_increases,
        "top_decreases": top_decreases,
    }


def _validate_contract_comparison(previous_vendors, current_vendors, result) -> None:
    """
    Unit-test style validation of the contract-level comparison result.

    Verifies the structural invariants of compare_snapshots() output using the
    two loaded snapshots. Raises AssertionError on any failure.
    """
    prev_contracts = _contract_set(previous_vendors)
    curr_contracts = _contract_set(current_vendors)

    # Required keys are present.
    expected_keys = {
        "previous_count", "current_count", "count_delta",
        "added_contracts", "removed_contracts",
        "added_count", "removed_count", "unchanged_count",
    }
    assert expected_keys.issubset(result.keys()), "Result is missing required keys"

    # Counts match the DataFrames and the delta is consistent.
    assert result["previous_count"] == len(previous_vendors)
    assert result["current_count"] == len(current_vendors)
    assert result["count_delta"] == len(current_vendors) - len(previous_vendors)

    # Count fields match their list lengths.
    assert result["added_count"] == len(result["added_contracts"])
    assert result["removed_count"] == len(result["removed_contracts"])

    # Added contracts are in current but not previous.
    for c in result["added_contracts"]:
        assert c in curr_contracts and c not in prev_contracts

    # Removed contracts are in previous but not current.
    for c in result["removed_contracts"]:
        assert c in prev_contracts and c not in curr_contracts

    # Added and removed are disjoint.
    assert not (set(result["added_contracts"]) & set(result["removed_contracts"]))

    # Set-algebra sanity: unchanged + added == current unique contracts;
    # unchanged + removed == previous unique contracts.
    assert result["unchanged_count"] + result["added_count"] == len(curr_contracts)
    assert result["unchanged_count"] + result["removed_count"] == len(prev_contracts)

    # Movement classification: increases + decreases account for every change.
    assert result["increase_count"] + result["decrease_count"] == result["changed_count"]
    for record in result["changed_contracts"]:
        if record["delta"] > 0:
            assert record["movement_type"] == "increase"
        elif record["delta"] < 0:
            assert record["movement_type"] == "decrease"
        else:
            assert record["movement_type"] == "unchanged"

    # Portfolio aggregation: net_delta equals the sum of all contract deltas.
    all_deltas = sum(r["delta"] for r in result["changed_contracts"])
    assert abs(result["net_delta"] - all_deltas) < 1e-6

    # Top movers ordering.
    inc_deltas = [r["delta"] for r in result["top_increases"]]
    dec_deltas = [r["delta"] for r in result["top_decreases"]]
    assert all(r["movement_type"] == "increase" for r in result["top_increases"])
    assert all(r["movement_type"] == "decrease" for r in result["top_decreases"])
    assert inc_deltas == sorted(inc_deltas, reverse=True)  # largest increase first
    assert dec_deltas == sorted(dec_deltas)  # largest decrease (most negative) first

    print("Validation passed: contract-level comparison invariants hold.")


if __name__ == "__main__":
    # Temporary manual test harness.
    # Loads the two snapshot worksheets and prints the comparison result.
    # Defaults target the sample workbook so this runs out of the box;
    # pass a workbook path and two sheet names to compare different snapshots.
    import sys

    filepath = sys.argv[1] if len(sys.argv) > 1 else "data/Weekly snapshots.xlsx"
    if len (sys.argv) > 3:
        previous_sheet = sys.argv[2]
        current_sheet = sys.argv[3] 
    else:
        previous_sheet, current_sheet = find_latest_snapshot_sheets(filepath)

    previous_df = load_snapshot(filepath, previous_sheet)
    current_df = load_snapshot(filepath, current_sheet)

    print(f"\n[{previous_sheet}] extracted vendor data:")
    previous_vendors = extract_vendor_data(previous_df)

    print(f"\n[{current_sheet}] extracted vendor data:")
    current_vendors = extract_vendor_data(current_df)

    from reporting.leadership_candidates import (
        build_candidate_pool,
        load_candidate_commentary,
        build_commentary_lookup,
        enrich_candidates_with_commentary,
        candidates_with_meaningful_commentary,
        rank_candidates_for_leadership,
    )

    candidates = build_candidate_pool(current_vendors)

    commentary_df = load_candidate_commentary(
        "data/IT Simplification dashboard.xlsx"
    )

    commentary_lookup = build_commentary_lookup(
        commentary_df
    )

    candidates = enrich_candidates_with_commentary(
        candidates,
        commentary_lookup,
    )

    commented_candidates = (
        candidates_with_meaningful_commentary(candidates)
    )

    ranked_candidates = rank_candidates_for_leadership (
        commented_candidates
    )

    print ("\nTOP LEADERSHIP CANDIDATES")

    for candidate in ranked_candidates[:10]:
        print (
            f"{candidate.vendor} | "
            f"{candidate.contract} | "
            f"${candidate.costout:,.0f} | "
            f"{candidate.commentary}"
        )

    print (f"Leadership candidates: {len(candidates)}")

    print (f"Candidates with commentary: {len(commented_candidates)}")

    result = compare_snapshots(previous_vendors, current_vendors)

    _validate_contract_comparison(previous_vendors, current_vendors, result)
