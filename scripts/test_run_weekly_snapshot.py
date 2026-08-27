"""
test_run_weekly_snapshot.py — Tests for the drop-in snapshot runner (3C.1).

Standard-library unittest (no external test dependency).

Run:
    python -m unittest scripts/test_run_weekly_snapshot.py
    (or)  python scripts/test_run_weekly_snapshot.py

These tests exercise the orchestration wrapper only. They must NOT depend on any
change to the existing 2A-3B analysis/reporting logic. A golden regression test
asserts the runner reproduces the exact reports the existing functions produce
for the known Snapshot Wk 1 / Snapshot Wk 2 pair.
"""

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_weekly_snapshot as runner
from runner_config import RunnerConfig
from compare_snapshots import load_snapshot, extract_vendor_data, compare_snapshots
from executive_summary import generate_executive_summary, generate_key_movements

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_WORKBOOK = REPO_ROOT / "data" / "Fake vendor data.xlsx"


def _quiet():
    return contextlib.redirect_stdout(io.StringIO())


def _make_vendor_workbook(path: Path, sheet_name: str, contracts) -> None:
    """
    Build a minimal workbook whose `sheet_name` worksheet mimics the vendor-block
    layout the existing extractor expects: a "Vendor"/"Contract" header row
    followed by vendor rows.

    contracts: iterable of (vendor, contract, v1_budget, renewal, costout)
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    # Title banner (row 1) so header is not at the very top, matching real sheets.
    ws.append(["IT Simplification — Test Dashboard"])
    ws.append([])
    # Vendor-block header (first two columns Vendor/Contract).
    ws.append(["Vendor", "Contract", "V1 budget", "Renewal price", "Costout"])
    for row in contracts:
        ws.append(list(row))
    wb.save(path)


def _base_contracts():
    return [
        ("Vendor A", "Contract 001", 1000, 800, 200),
        ("Vendor B", "Contract 002", 5000, 5000, 0),
        ("Vendor C", "Contract 003", 3000, 2000, 1000),
    ]


class RunnerTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="runner_test_"))
        self.config = RunnerConfig(
            data_dir=self.tmp,
            incoming_dir=self.tmp / "incoming",
            archive_dir=self.tmp / "archive",
            outputs_dir=self.tmp / "outputs",
            state_dir=self.tmp / "state",
            snapshot_worksheet="Snapshot Wk 2",
        )
        self.config.ensure_directories()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed_baseline(self, contracts=None):
        """Place an archived baseline workbook and point state at it."""
        contracts = contracts or _base_contracts()
        baseline = self.config.archive_dir / "baseline.xlsx"
        _make_vendor_workbook(baseline, self.config.snapshot_worksheet, contracts)
        runner.write_state(self.config, baseline, "seed-run")
        return baseline

    def _drop_incoming(self, name="week.xlsx", contracts=None):
        contracts = contracts or _base_contracts()
        target = self.config.incoming_dir / name
        _make_vendor_workbook(target, self.config.snapshot_worksheet, contracts)
        return target


class TestDiscovery(RunnerTestBase):
    def test_exactly_one_valid_workbook(self):
        self._drop_incoming("week.xlsx")
        found = runner.discover_current_snapshot(self.config)
        self.assertEqual(found.name, "week.xlsx")

    def test_empty_incoming_directory(self):
        with self.assertRaises(runner.DiscoveryError) as ctx:
            runner.discover_current_snapshot(self.config)
        self.assertIn("No eligible workbook", str(ctx.exception))

    def test_multiple_incoming_workbooks_lists_candidates(self):
        self._drop_incoming("week_a.xlsx")
        self._drop_incoming("week_b.xlsx")
        with self.assertRaises(runner.DiscoveryError) as ctx:
            runner.discover_current_snapshot(self.config)
        msg = str(ctx.exception)
        self.assertIn("Multiple eligible workbooks", msg)
        self.assertIn("week_a.xlsx", msg)
        self.assertIn("week_b.xlsx", msg)

    def test_ignores_excel_lock_file(self):
        self._drop_incoming("week.xlsx")
        # A temporary Excel lock file should be ignored.
        (self.config.incoming_dir / "~$week.xlsx").write_text("lock")
        found = runner.discover_current_snapshot(self.config)
        self.assertEqual(found.name, "week.xlsx")


class TestPreflight(RunnerTestBase):
    def test_unreadable_or_corrupt_workbook(self):
        bad = self.config.incoming_dir / "corrupt.xlsx"
        bad.write_text("this is not a real xlsx")
        with self.assertRaises(runner.PreflightError) as ctx:
            runner.preflight_workbook(self.config, bad, "current")
        self.assertIn("unreadable or corrupt", str(ctx.exception))

    def test_missing_required_worksheet_structure(self):
        # Workbook exists and opens, but lacks the configured worksheet.
        wb_path = self.config.incoming_dir / "wrong_sheet.xlsx"
        wb = openpyxl.Workbook()
        wb.active.title = "Some Other Sheet"
        wb.save(wb_path)
        with self.assertRaises(runner.PreflightError) as ctx:
            runner.preflight_workbook(self.config, wb_path, "current")
        self.assertIn("Required worksheet", str(ctx.exception))


class TestBaselineResolution(RunnerTestBase):
    def test_missing_previous_state(self):
        current = self._drop_incoming("week.xlsx")
        with self.assertRaises(runner.BaselineError) as ctx:
            runner.resolve_previous_snapshot(self.config, current)
        self.assertIn("No previous successful snapshot", str(ctx.exception))

    def test_same_file_current_and_previous(self):
        baseline = self._seed_baseline()
        # Point the current at the exact same file as the baseline.
        with self.assertRaises(runner.BaselineError) as ctx:
            runner.resolve_previous_snapshot(self.config, baseline)
        self.assertIn("same file", str(ctx.exception))


class TestFailureIsolation(RunnerTestBase):
    def test_no_baseline_does_not_archive_or_update_state(self):
        current = self._drop_incoming("week.xlsx")
        manifest = runner.run(self.config)
        self.assertEqual(manifest["status"], "failed")
        # Incoming workbook remains.
        self.assertTrue(current.exists())
        # No state file created.
        self.assertFalse(self.config.state_file.exists())
        # No promoted output directory for this run.
        self.assertFalse((self.config.outputs_dir / manifest["run_id"]).exists())
        # Manifest still written.
        self.assertTrue(
            (self.config.outputs_dir / f"manifest_{manifest['run_id']}.json").exists()
        )

    def test_pipeline_stage_failure_preserves_state_and_input(self):
        # Seed a valid baseline + state, then break the pipeline by patching
        # compare_snapshots to raise. This proves a 2A-3B stage failure does not
        # archive the input or update state.
        self._seed_baseline()
        current = self._drop_incoming("week.xlsx")
        state_before = self.config.state_file.read_text(encoding="utf-8")

        original = runner.compare_snapshots

        def boom(previous_df, current_df):
            raise RuntimeError("simulated stage failure")

        runner.compare_snapshots = boom
        try:
            manifest = runner.run(self.config)
        finally:
            runner.compare_snapshots = original

        self.assertEqual(manifest["status"], "failed")
        self.assertTrue(current.exists())  # input not archived
        # State unchanged.
        self.assertEqual(self.config.state_file.read_text(encoding="utf-8"), state_before)
        # No promoted output.
        self.assertFalse((self.config.outputs_dir / manifest["run_id"]).exists())


class TestSuccessfulRun(RunnerTestBase):
    def test_happy_path_archives_and_updates_state(self):
        self._seed_baseline(_base_contracts())
        changed = _base_contracts()
        changed[0] = ("Vendor A", "Contract 001", 1000, 700, 300)  # costout 200 -> 300
        current = self._drop_incoming("week.xlsx", changed)

        manifest = runner.run(self.config)

        self.assertEqual(manifest["status"], "success", manifest["errors"])
        # Input archived (no longer in incoming).
        self.assertFalse(current.exists())
        self.assertTrue(any(self.config.archive_dir.glob("week*.xlsx")))
        # Output promoted with expected files.
        out = self.config.outputs_dir / manifest["run_id"]
        self.assertTrue((out / "executive_summary.txt").exists())
        self.assertTrue((out / "key_movements.txt").exists())
        self.assertTrue((out / "analysis.json").exists())
        # State updated to the archived current workbook.
        state = json.loads(self.config.state_file.read_text(encoding="utf-8"))
        self.assertIn("week", Path(state["snapshot_path"]).name)
        # No leftover temp dir.
        self.assertFalse(any(self.config.outputs_dir.glob(".tmp_*")))


class TestGoldenRegression(unittest.TestCase):
    """
    The runner must reproduce the exact reports the existing pipeline produces
    for the known Snapshot Wk 1 (previous) / Snapshot Wk 2 (current) pair.
    """

    @unittest.skipUnless(SAMPLE_WORKBOOK.exists(), "sample workbook not present")
    def test_runner_matches_existing_pipeline_output(self):
        # Golden result computed directly from the existing functions.
        with _quiet():
            prev = extract_vendor_data(load_snapshot(SAMPLE_WORKBOOK, "Snapshot Wk 1"))
            curr = extract_vendor_data(load_snapshot(SAMPLE_WORKBOOK, "Snapshot Wk 2"))
            golden_analysis = compare_snapshots(prev, curr)
        golden_exec = generate_executive_summary(golden_analysis)
        golden_keys = generate_key_movements(golden_analysis)

        # Drive the runner's pipeline invocation against the same two sheets.
        # Previous uses "Snapshot Wk 1"; current uses config default "Snapshot Wk 2".
        tmp = Path(tempfile.mkdtemp(prefix="golden_"))
        try:
            config_prev = RunnerConfig(snapshot_worksheet="Snapshot Wk 1")
            config_curr = RunnerConfig(snapshot_worksheet="Snapshot Wk 2")
            with _quiet():
                prev_vendors = runner._extract(config_prev, SAMPLE_WORKBOOK)
                curr_vendors = runner._extract(config_curr, SAMPLE_WORKBOOK)
                analysis = compare_snapshots(prev_vendors, curr_vendors)
            wrapped_exec = generate_executive_summary(analysis)
            wrapped_keys = generate_key_movements(analysis)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        self.assertEqual(wrapped_exec, golden_exec)
        self.assertEqual(wrapped_keys, golden_keys)
        self.assertEqual(analysis["net_delta"], golden_analysis["net_delta"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
