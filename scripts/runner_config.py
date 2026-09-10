"""
runner_config.py — Runtime configuration for the drop-in snapshot runner
(Milestone 3C.1).

This module holds *runtime* configuration only: output locations, workbook
locations, and worksheet settings used by the weekly snapshow runner. It deliberately contains no
business rules (no contract matching, costout, movement, aggregation or
reporting logic) — those live in the existing, unchanged pipeline modules.

The configuration is expressed as a dataclass so tests can override any path or
value without touching the pipeline.
"""

from dataclasses import dataclass
from pathlib import Path


# Repository root is two levels up from this file (scripts/ -> repo root).
_REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class RunnerConfig:
    """Runtime configuration for the weekly snapshot runner."""

    # Base data directory and its sub-folders.
    data_dir: Path = _REPO_ROOT / "data"
    outputs_dir: Path = _REPO_ROOT / "data" / "outputs"
    weekly_snapshot_workbook: Path = _REPO_ROOT / "data" / "Weekly snapshots.xlsx"

    # Worksheet the pipeline reads from a dropped workbook. This is a runtime
    # input, not a business rule. The existing pipeline reads a named worksheet,
    # so the runner must be told which one to use. Default is the sheet the
    # pipeline treats as the "current" snapshot.
    snapshot_worksheet: str = "Live dashboard"

    def ensure_directories(self) -> None:
        self.outputs_dir.mkdir(parents=True, exist_ok=True)


def default_config() -> RunnerConfig:
    """Return the default runtime configuration."""
    return RunnerConfig()
