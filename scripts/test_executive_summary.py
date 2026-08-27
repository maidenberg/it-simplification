"""
test_executive_summary.py — Unit tests for the Executive Summary Renderer (3A).

Uses the standard-library unittest framework (no external test dependency).

Run:
    python -m unittest scripts/test_executive_summary.py
    (or)  python scripts/test_executive_summary.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from executive_summary import (
    generate_executive_summary,
    generate_key_movements,
    _format_currency,
    _format_mover,
    _format_signed_mover,
    _top_movers,
)


def analysis_with_decrease() -> dict:
    """
    A fixture that includes both an increase and a decrease, to exercise the
    signed-mover rendering ('+$' and '-$').
    """
    top_increases = [
        {"contract": "Example Contract 028", "delta": 16764.09,
         "movement_type": "increase"},
        {"contract": "Example Contract 034", "delta": 7489.0,
         "movement_type": "increase"},
    ]
    top_decreases = [
        {"contract": "Example Contract 099", "delta": -5560.0,
         "movement_type": "decrease"},
    ]
    return {
        "previous_count": 142,
        "current_count": 142,
        "changed_count": 3,
        "increase_count": 2,
        "decrease_count": 1,
        "total_positive_delta": 24253.09,
        "total_negative_delta": -5560.0,
        "net_delta": 18693.09,
        "top_increases": top_increases,
        "top_decreases": top_decreases,
        "changed_contracts": top_increases + top_decreases,
    }


def validated_analysis() -> dict:
    """
    A movement-analysis fixture matching the validated Wk1 -> Wk2 dataset.

    Mirrors the real compare_snapshots() output for the sample workbook:
    142 contracts compared, 3 increases, 0 decreases, net +24,750.09.
    """
    top_increases = [
        {"contract": "Example Contract 028", "previous_costout": 0.0,
         "current_costout": 16764.09, "delta": 16764.09, "movement_type": "increase"},
        {"contract": "Example Contract 034", "previous_costout": -5560.0,
         "current_costout": 1929.0, "delta": 7489.0, "movement_type": "increase"},
        {"contract": "Example Contract 023", "previous_costout": 0.0,
         "current_costout": 497.0, "delta": 497.0, "movement_type": "increase"},
    ]
    return {
        "previous_count": 142,
        "current_count": 142,
        "changed_count": 3,
        "increase_count": 3,
        "decrease_count": 0,
        "total_positive_delta": 24750.09,
        "total_negative_delta": 0.0,
        "net_delta": 24750.09,
        "top_increases": top_increases,
        "top_decreases": [],
        "changed_contracts": list(top_increases),
    }


class TestCurrencyFormatting(unittest.TestCase):
    def test_thousands_separator_and_two_decimals(self):
        self.assertEqual(_format_currency(24750.09), "24,750.09")
        self.assertEqual(_format_currency(0), "0.00")
        self.assertEqual(_format_currency(0.0), "0.00")
        self.assertEqual(_format_currency(497), "497.00")
        self.assertEqual(_format_currency(1234567.5), "1,234,567.50")
        self.assertEqual(_format_currency(-5560), "-5,560.00")

    def test_format_mover(self):
        mover = {"contract": "Example Contract 028", "delta": 16764.09}
        self.assertEqual(_format_mover(mover), "Example Contract 028: $16,764.09")


class TestValueMapping(unittest.TestCase):
    def setUp(self):
        self.summary = generate_executive_summary(validated_analysis())

    def test_field_values(self):
        self.assertIn("Contracts compared: 142", self.summary)
        self.assertIn("Contracts with movement: 3", self.summary)
        self.assertIn("Increases: 3", self.summary)
        self.assertIn("Decreases: 0", self.summary)
        self.assertIn("Total positive delta: $24,750.09", self.summary)
        self.assertIn("Total negative delta: $0.00", self.summary)
        self.assertIn("Net delta: $24,750.09", self.summary)


class TestTopMoverOutput(unittest.TestCase):
    def setUp(self):
        self.summary = generate_executive_summary(validated_analysis())

    def test_preserves_analysis_ranking(self):
        movers = _top_movers(validated_analysis())
        self.assertEqual(
            [m["contract"] for m in movers],
            ["Example Contract 028", "Example Contract 034", "Example Contract 023"],
        )

    def test_mover_lines(self):
        self.assertIn("1. Example Contract 028: $16,764.09", self.summary)
        self.assertIn("2. Example Contract 034: $7,489.00", self.summary)
        self.assertIn("3. Example Contract 023: $497.00", self.summary)


class TestFixedSectionOrder(unittest.TestCase):
    def setUp(self):
        self.summary = generate_executive_summary(validated_analysis())

    def test_section_order(self):
        order = [
            "IT SIMPLIFICATION WEEKLY MOVEMENT SUMMARY",
            "Contracts compared:",
            "Contracts with movement:",
            "Increases:",
            "Decreases:",
            "Total positive delta:",
            "Total negative delta:",
            "Net delta:",
            "Top Movements",
            "1. ",
            "2. ",
            "3. ",
        ]
        positions = [self.summary.index(section) for section in order]
        self.assertEqual(positions, sorted(positions))

    def test_banner_present(self):
        self.assertTrue(self.summary.startswith("=" * 50))
        self.assertIn("-------------", self.summary)


class TestExactValidatedOutput(unittest.TestCase):
    def test_exact_output(self):
        summary = generate_executive_summary(validated_analysis())
        expected = "\n".join([
            "=" * 50,
            "IT SIMPLIFICATION WEEKLY MOVEMENT SUMMARY",
            "=" * 50,
            "",
            "Contracts compared: 142",
            "Contracts with movement: 3",
            "",
            "Increases: 3",
            "Decreases: 0",
            "",
            "Total positive delta: $24,750.09",
            "Total negative delta: $0.00",
            "",
            "Net delta: $24,750.09",
            "",
            "Top Movements",
            "-------------",
            "",
            "1. Example Contract 028: $16,764.09",
            "2. Example Contract 034: $7,489.00",
            "3. Example Contract 023: $497.00",
        ])
        self.assertEqual(summary, expected)


class TestKeyMovementsFormatting(unittest.TestCase):
    def test_signed_mover_increase(self):
        mover = {"contract": "Example Contract 028", "delta": 16764.09}
        self.assertEqual(
            _format_signed_mover(mover), "Example Contract 028 (+$16,764.09)"
        )

    def test_signed_mover_decrease_uses_absolute_magnitude(self):
        mover = {"contract": "Example Contract 099", "delta": -5560.0}
        self.assertEqual(
            _format_signed_mover(mover), "Example Contract 099 (-$5,560.00)"
        )

    def test_currency_thousands_separator(self):
        mover = {"contract": "X", "delta": 1234567.5}
        self.assertEqual(_format_signed_mover(mover), "X (+$1,234,567.50)")


class TestKeyMovementsRanking(unittest.TestCase):
    def test_preserves_analysis_ranking(self):
        section = generate_key_movements(analysis_with_decrease())
        # Increases first (largest-first), then decreases — exactly as supplied.
        idx_028 = section.index("Example Contract 028")
        idx_034 = section.index("Example Contract 034")
        idx_099 = section.index("Example Contract 099")
        self.assertLess(idx_028, idx_034)
        self.assertLess(idx_034, idx_099)


class TestKeyMovementsExactOutput(unittest.TestCase):
    def test_exact_output_increases_only(self):
        section = generate_key_movements(validated_analysis())
        expected = "\n".join([
            "KEY MOVEMENTS",
            "-------------",
            "",
            "1. Example Contract 028 (+$16,764.09)",
            "2. Example Contract 034 (+$7,489.00)",
            "3. Example Contract 023 (+$497.00)",
        ])
        self.assertEqual(section, expected)

    def test_exact_output_with_decrease(self):
        section = generate_key_movements(analysis_with_decrease())
        expected = "\n".join([
            "KEY MOVEMENTS",
            "-------------",
            "",
            "1. Example Contract 028 (+$16,764.09)",
            "2. Example Contract 034 (+$7,489.00)",
            "3. Example Contract 099 (-$5,560.00)",
        ])
        self.assertEqual(section, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
