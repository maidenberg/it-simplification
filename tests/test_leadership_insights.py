"""
test_leadership_insights.py — Tests for Leadership Insights (Milestone 3D.2).

Standard-library unittest (no external test dependency).

Run:
    python -m unittest tests.test_leadership_insights
    (or)  python tests/test_leadership_insights.py
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.reporting.leadership_insights import (
    generate_leadership_insights,
    LeadershipInsightsError,
    SINGLE_MOVER_FALLBACK,
)


EXEC_ARTEFACT = "\n".join([
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

MOVES_ARTEFACT = "\n".join([
    "KEY MOVEMENTS",
    "-------------",
    "",
    "1. Example Contract 028 (+$16,764.09)",
    "2. Example Contract 034 (+$7,489.00)",
    "3. Example Contract 023 (+$497.00)",
])

MOVES_SINGLE = "\n".join([
    "KEY MOVEMENTS",
    "-------------",
    "",
    "1. Example Contract 028 (+$16,764.09)",
])


class LeadershipInsightsTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="li_"))
        self.exec_path = self.tmp / "executive_summary.txt"
        self.moves_path = self.tmp / "key_movements.txt"
        self.out_path = self.tmp / "leadership_insights.txt"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed(self, exec_content=EXEC_ARTEFACT, moves_content=MOVES_ARTEFACT):
        self.exec_path.write_text(exec_content, encoding="utf-8")
        self.moves_path.write_text(moves_content, encoding="utf-8")

    def _generate(self):
        return generate_leadership_insights(
            self.exec_path, self.moves_path, self.out_path
        )


class TestFileGeneration(LeadershipInsightsTestBase):
    def test_file_generation(self):
        self._seed()
        out = self._generate()
        self.assertEqual(out, self.out_path)
        self.assertTrue(self.out_path.exists())

    def test_exact_insight_count(self):
        self._seed()
        text = self._generate().read_text(encoding="utf-8")
        for n in (1, 2, 3, 4, 5):
            self.assertIn(f"{n}. ", text)
        self.assertNotIn("6. ", text)
        self.assertTrue(text.startswith("Leadership Insights"))


class TestValueExtraction(LeadershipInsightsTestBase):
    def test_contract_count_extraction(self):
        self._seed()
        text = self._generate().read_text(encoding="utf-8")
        self.assertIn("Portfolio review covered 142 contracts.", text)

    def test_net_delta_extraction(self):
        self._seed()
        text = self._generate().read_text(encoding="utf-8")
        self.assertIn(
            "Portfolio net movement for the reporting period was $24,750.09.", text
        )

    def test_first_mover_extraction(self):
        self._seed()
        text = self._generate().read_text(encoding="utf-8")
        self.assertIn(
            "Largest portfolio movement was Example Contract 028 (+$16,764.09).", text
        )

    def test_second_mover_extraction(self):
        self._seed()
        text = self._generate().read_text(encoding="utf-8")
        self.assertIn(
            "Second largest portfolio movement was Example Contract 034 (+$7,489.00).",
            text,
        )

    def test_top_two_contract_names(self):
        self._seed()
        text = self._generate().read_text(encoding="utf-8")
        self.assertIn(
            "Top two ranked movements were Example Contract 028 and "
            "Example Contract 034.",
            text,
        )


class TestDeterminism(LeadershipInsightsTestBase):
    def test_deterministic_output(self):
        self._seed()
        first = self._generate().read_text(encoding="utf-8")
        second = self._generate().read_text(encoding="utf-8")
        self.assertEqual(first, second)


class TestFailureHandling(LeadershipInsightsTestBase):
    def test_missing_executive_summary_raises(self):
        # Only movements present.
        self.moves_path.write_text(MOVES_ARTEFACT, encoding="utf-8")
        with self.assertRaises(LeadershipInsightsError) as ctx:
            self._generate()
        self.assertIn("executive summary", str(ctx.exception))
        self.assertFalse(self.out_path.exists())

    def test_missing_key_movements_raises(self):
        # Only summary present.
        self.exec_path.write_text(EXEC_ARTEFACT, encoding="utf-8")
        with self.assertRaises(LeadershipInsightsError) as ctx:
            self._generate()
        self.assertIn("key movements", str(ctx.exception))
        self.assertFalse(self.out_path.exists())


class TestSingleMoverFallback(LeadershipInsightsTestBase):
    def test_single_mover_fallback(self):
        self._seed(moves_content=MOVES_SINGLE)
        text = self._generate().read_text(encoding="utf-8")
        # First mover present; second mover degrades to the fallback.
        self.assertIn(
            "Largest portfolio movement was Example Contract 028 (+$16,764.09).", text
        )
        self.assertIn(
            f"Second largest portfolio movement was {SINGLE_MOVER_FALLBACK}.", text
        )
        self.assertIn(
            f"Top two ranked movements were Example Contract 028 and "
            f"{SINGLE_MOVER_FALLBACK}.",
            text,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
