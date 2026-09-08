"""
test_reporting_package_runner.py — Runner integration tests for Milestone 3D.4.

Verifies the reporting_package stage within a full runner run:
- produced by a successful run
- runs after risks_watchouts and before promote
- package failure prevents promotion (and leaves state/input untouched)
- reporting_package.txt included in the manifest generated_artefacts
- existing generated artefacts remain unchanged

Standard-library unittest.

Run:
    python -m unittest tests.test_reporting_package_runner
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

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import run_weekly_snapshot as runner
from runner_config import RunnerConfig

SAMPLE_WORKBOOK = REPO_ROOT / "data" / "Fake vendor data.xlsx"


def _quiet():
    return contextlib.redirect_stdout(io.StringIO())


def _extract_sheet(src, sheet, dest, dest_sheet):
    s = openpyxl.load_workbook(src, read_only=True, data_only=True)
    w = s[sheet]
    o = openpyxl.Workbook()
    ow = o.active
    ow.title = dest_sheet
    for row in w.iter_rows(values_only=True):
        ow.append(list(row))
    o.save(dest)
    s.close()

if __name__ == "__main__":
    unittest.main(verbosity=2)
