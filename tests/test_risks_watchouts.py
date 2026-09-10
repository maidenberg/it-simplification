"""
test_risks_watchouts.py — Tests for Risks & Watchouts (Milestone 3D.3).

Standard-library unittest (no external test dependency).

Run:
    python -m unittest tests.test_risks_watchouts
    (or)  python tests/test_risks_watchouts.py
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.reporting.risks_watchouts import (
    generate_risks_watchouts,
    RisksWatchoutsError,
    NO_RISKS,
    NO_WATCHOUTS,
    NO_OBSERVATIONS,
)

# Leadership insights containing pre-labelled entries (preferred approach).
LEADERSHIP_LABELLED = "\n".join([
    "Leadership Insights",
    "",
    "RISK: Vendor X contract lapses next week.",
    "WATCHOUT: Concentration in top vendor.",
    "OBSERVATION: 142 contracts under review.",
])


LEADERSHIP_ARTEFACT = "\n".join([
    "Leadership Insights",
    "",
    "1. Portfolio review covered 142 contracts.",
    "",
    "2. Portfolio net movement for the reporting period was $24,750.09.",
    "",
    "3. Largest portfolio movement was Example Contract 028 (+$16,764.09).",
    "",
    "4. Second largest portfolio movement was Example Contract 034 (+$7,489.00).",
    "",
    "5. Top two ranked movements were Example Contract 028 and Example Contract 034.",
])

# Only positive movers -> watchouts populated, no risks.
MOVES_POSITIVE_ONLY = "\n".join([
    "KEY MOVEMENTS",
    "-------------",
    "",
    "1. Example Contract 028 (+$16,764.09)",
    "2. Example Contract 034 (+$7,489.00)",
    "3. Example Contract 023 (+$497.00)",
])

# Includes a negative mover -> risks populated.
MOVES_WITH_NEGATIVE = "\n".join([
    "KEY MOVEMENTS",
    "-------------",
    "",
    "1. Example Contract 028 (+$16,764.09)",
    "2. Example Contract 099 (-$5,560.00)",
])

# No ranked movers -> neither risks nor watchouts.
MOVES_EMPTY = "\n".join([
    "KEY MOVEMENTS",
    "-------------",
    "",
    "1.",
    "2.",
    "3.",
])


class RisksWatchoutsTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="rw_"))
        self.leadership_path = self.tmp / "leadership_insights.txt"
        self.out_path = self.tmp / "risks_watchouts.txt"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed(self, leadership=LEADERSHIP_ARTEFACT, moves=MOVES_POSITIVE_ONLY):
        self.leadership_path.write_text(leadership, encoding="utf-8")
    
    def _generate(self):
        return generate_risks_watchouts(
            self.leadership_path, self.out_path
        )


class TestStructure(RisksWatchoutsTestBase):
    def test_file_generation_and_sections(self):
        self._seed()
        out = self._generate()
        self.assertTrue(out.exists())
        text = out.read_text(encoding="utf-8")
        for section in ("IT SIMPLIFICATION RISKS & WATCHOUTS", "RISKS",
                        "WATCHOUTS", "DATA OBSERVATIONS", "END OF REPORT"):
            self.assertIn(section, text)
        positions = [text.index(s) for s in (
            "RISKS", "WATCHOUTS", "DATA OBSERVATIONS", "END OF REPORT")]
        self.assertEqual(positions, sorted(positions))


class TestEmptyPlaceholders(RisksWatchoutsTestBase):
    def test_no_risks_placeholder(self):
        # Positive-only movers => no risks.
        self._seed(moves=MOVES_POSITIVE_ONLY)
        text = self._generate().read_text(encoding="utf-8")
        self.assertIn(NO_RISKS, text)

    def test_no_watchouts_placeholder(self):
        # Empty movers => no watchouts (and no risks).
        self._seed(moves=MOVES_EMPTY)
        text = self._generate().read_text(encoding="utf-8")
        self.assertIn(NO_WATCHOUTS, text)
        self.assertIn(NO_RISKS, text)

    def test_no_observations_placeholder(self):
        # Leadership insights without insight 1/2 lines => no observations.
        self._seed(leadership="Leadership Insights\n\n(no numbered facts)",
                   moves=MOVES_POSITIVE_ONLY)
        text = self._generate().read_text(encoding="utf-8")
        self.assertIn(NO_OBSERVATIONS, text)


class TestPreferredLabelledApproach(RisksWatchoutsTestBase):
    def test_prelabelled_entries_take_precedence(self):
        # When leadership_insights carries labelled entries, they are used
        # verbatim in preference to any fallback derivation.
        self._seed(leadership=LEADERSHIP_LABELLED, moves=MOVES_WITH_NEGATIVE)
        text = self._generate().read_text(encoding="utf-8")
        self.assertIn("Vendor X contract lapses next week.", text)
        self.assertIn("Concentration in top vendor.", text)
        self.assertIn("142 contracts under review.", text)
        # Fallback derivation is NOT used when labelled entries exist.
        self.assertNotIn("Negative movement:", text)
        self.assertNotIn("Significant movement:", text)


class TestDeterminism(RisksWatchoutsTestBase):
    def test_deterministic_output(self):
        self._seed(moves=MOVES_WITH_NEGATIVE)
        first = self._generate().read_text(encoding="utf-8")
        second = self._generate().read_text(encoding="utf-8")
        self.assertEqual(first, second)


class TestFailureHandling(RisksWatchoutsTestBase):
    def test_missing_leadership_raises(self):
        with self.assertRaises(RisksWatchoutsError) as ctx:
            self._generate()
        self.assertIn("leadership insights", str(ctx.exception))
        self.assertFalse(self.out_path.exists())

if __name__ == "__main__":
    unittest.main(verbosity=2)
