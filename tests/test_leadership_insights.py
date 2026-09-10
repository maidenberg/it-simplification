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
)


class LeadershipInsightsTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="li_"))
        self.out_path = self.tmp / "leadership_insights.txt"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _generate(self):
        return generate_leadership_insights(self.out_path)

class TestFileGeneration(LeadershipInsightsTestBase):
    def test_file_generation(self):
        out = self._generate()
        self.assertEqual(out, self.out_path)
        self.assertTrue(self.out_path.exists())

    def test_exact_insight_count(self):
        text = self._generate().read_text(encoding="utf-8")
        
        self.assertTrue(text.startswith("Leadership Insights"))


class TestDeterminism(LeadershipInsightsTestBase):
    def test_deterministic_output(self):
        first = self._generate().read_text(encoding="utf-8")
        second = self._generate().read_text(encoding="utf-8")
        self.assertEqual(first, second)

if __name__ == "__main__":
    unittest.main(verbosity=2)
