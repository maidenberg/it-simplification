"""
test_reporting_package.py — Tests for Reporting Package Assembly (Milestone 3D.4).

Standard-library unittest (no external test dependency).

Run:
    python -m unittest tests.test_reporting_package
    (or)  python tests/test_reporting_package.py
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.reporting.reporting_package import (
    generate_reporting_package,
    ReportingPackageError,
    REPORTING_PACKAGE_FILENAME,
    EMPTY_PLACEHOLDER,
)

EXEC = "EXEC line 1\nEXEC line 2"
MOVES = "MOVES line 1\nMOVES line 2"
WEEKLY = "WEEKLY body"
LEADERSHIP = "LEADERSHIP body"
RISKS = "RISKS body"


class ReportingPackageTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="rp_"))
        self.paths = {
            "exec": self.tmp / "executive_summary.txt",
            "moves": self.tmp / "key_movements.txt",
            "weekly": self.tmp / "weekly_update.md",
            "leadership": self.tmp / "leadership_insights.txt",
            "risks": self.tmp / "risks_watchouts.txt",
            "out": self.tmp / REPORTING_PACKAGE_FILENAME,
        }

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed(self, exec_c=EXEC, moves_c=MOVES, weekly_c=WEEKLY,
              leadership_c=LEADERSHIP, risks_c=RISKS):
        self.paths["exec"].write_text(exec_c, encoding="utf-8")
        self.paths["moves"].write_text(moves_c, encoding="utf-8")
        self.paths["weekly"].write_text(weekly_c, encoding="utf-8")
        self.paths["leadership"].write_text(leadership_c, encoding="utf-8")
        self.paths["risks"].write_text(risks_c, encoding="utf-8")

    def _generate(self):
        return generate_reporting_package(
            self.paths["exec"], self.paths["moves"], self.paths["weekly"],
            self.paths["leadership"], self.paths["risks"], self.paths["out"],
        )


class TestNormalGeneration(ReportingPackageTestBase):
    def test_file_generated(self):
        self._seed()
        out = self._generate()
        self.assertTrue(out.exists())
        self.assertEqual(out.name, REPORTING_PACKAGE_FILENAME)

    def test_title_and_headings(self):
        self._seed()
        text = self._generate().read_text(encoding="utf-8")
        self.assertTrue(text.startswith("IT SIMPLIFICATION WEEKLY REPORT"))
        for heading in ("EXECUTIVE SUMMARY", "KEY MOVEMENTS", "WEEKLY UPDATE",
                        "LEADERSHIP INSIGHTS", "RISKS & WATCHOUTS", "END OF REPORT"):
            self.assertIn(heading, text)

    def test_fixed_section_order(self):
        self._seed()
        text = self._generate().read_text(encoding="utf-8")
        order = ["EXECUTIVE SUMMARY", "KEY MOVEMENTS", "WEEKLY UPDATE",
                 "LEADERSHIP INSIGHTS", "RISKS & WATCHOUTS", "END OF REPORT"]
        positions = [text.index(s) for s in order]
        self.assertEqual(positions, sorted(positions))

    def test_verbatim_source_preservation(self):
        self._seed()
        text = self._generate().read_text(encoding="utf-8")
        for content in (EXEC, MOVES, WEEKLY, LEADERSHIP, RISKS):
            self.assertIn(content, text)

    def test_deterministic_output(self):
        self._seed()
        first = self._generate().read_text(encoding="utf-8")
        second = self._generate().read_text(encoding="utf-8")
        self.assertEqual(first, second)


class TestEmptyPlaceholders(ReportingPackageTestBase):
    def test_empty_executive_summary(self):
        self._seed(exec_c="   \n  ")
        text = self._generate().read_text(encoding="utf-8")
        # Placeholder appears under the Executive Summary section.
        exec_idx = text.index("EXECUTIVE SUMMARY")
        moves_idx = text.index("KEY MOVEMENTS")
        self.assertIn(EMPTY_PLACEHOLDER, text[exec_idx:moves_idx])

    def test_empty_key_movements(self):
        self._seed(moves_c="")
        text = self._generate().read_text(encoding="utf-8")
        moves_idx = text.index("KEY MOVEMENTS")
        weekly_idx = text.index("WEEKLY UPDATE")
        self.assertIn(EMPTY_PLACEHOLDER, text[moves_idx:weekly_idx])

    def test_empty_weekly_update(self):
        self._seed(weekly_c="\n\n")
        text = self._generate().read_text(encoding="utf-8")
        weekly_idx = text.index("WEEKLY UPDATE")
        leadership_idx = text.index("LEADERSHIP INSIGHTS")
        self.assertIn(EMPTY_PLACEHOLDER, text[weekly_idx:leadership_idx])

    def test_empty_leadership_insights(self):
        self._seed(leadership_c="")
        text = self._generate().read_text(encoding="utf-8")
        leadership_idx = text.index("LEADERSHIP INSIGHTS")
        risks_idx = text.index("RISKS & WATCHOUTS")
        self.assertIn(EMPTY_PLACEHOLDER, text[leadership_idx:risks_idx])

    def test_empty_risks_watchouts(self):
        self._seed(risks_c="   ")
        text = self._generate().read_text(encoding="utf-8")
        risks_idx = text.index("RISKS & WATCHOUTS")
        end_idx = text.index("END OF REPORT")
        self.assertIn(EMPTY_PLACEHOLDER, text[risks_idx:end_idx])


class TestMissingFiles(ReportingPackageTestBase):
    def test_missing_executive_summary(self):
        self._seed()
        self.paths["exec"].unlink()
        with self.assertRaises(ReportingPackageError) as ctx:
            self._generate()
        self.assertIn("executive summary", str(ctx.exception))
        self.assertIn(str(self.paths["exec"]), str(ctx.exception))

    def test_missing_key_movements(self):
        self._seed()
        self.paths["moves"].unlink()
        with self.assertRaises(ReportingPackageError) as ctx:
            self._generate()
        self.assertIn("key movements", str(ctx.exception))

    def test_missing_weekly_update(self):
        self._seed()
        self.paths["weekly"].unlink()
        with self.assertRaises(ReportingPackageError) as ctx:
            self._generate()
        self.assertIn("weekly update", str(ctx.exception))

    def test_missing_leadership_insights(self):
        self._seed()
        self.paths["leadership"].unlink()
        with self.assertRaises(ReportingPackageError) as ctx:
            self._generate()
        self.assertIn("leadership insights", str(ctx.exception))

    def test_missing_risks_watchouts(self):
        self._seed()
        self.paths["risks"].unlink()
        with self.assertRaises(ReportingPackageError) as ctx:
            self._generate()
        self.assertIn("risks & watchouts", str(ctx.exception))


class TestContentEdgeCases(ReportingPackageTestBase):
    def test_utf8_source_content(self):
        self._seed(exec_c="Café — naïve €1,234.56 — 日本語")
        text = self._generate().read_text(encoding="utf-8")
        self.assertIn("Café — naïve €1,234.56 — 日本語", text)

    def test_source_without_trailing_newline(self):
        self._seed(moves_c="no trailing newline")
        text = self._generate().read_text(encoding="utf-8")
        self.assertIn("no trailing newline", text)

    def test_internal_blank_line_preservation(self):
        self._seed(leadership_c="line A\n\nline B")
        text = self._generate().read_text(encoding="utf-8")
        self.assertIn("line A\n\nline B", text)

    def test_output_replacement_without_stale_content(self):
        self._seed(exec_c="FIRST CONTENT")
        self._generate()
        # Regenerate with different content; stale content must not remain.
        self._seed(exec_c="SECOND CONTENT")
        text = self._generate().read_text(encoding="utf-8")
        self.assertIn("SECOND CONTENT", text)
        self.assertNotIn("FIRST CONTENT", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
