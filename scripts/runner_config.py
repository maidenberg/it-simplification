"""
runner_config.py — Runtime configuration for the drop-in snapshot runner
(Milestone 3C.1).

This module holds *runtime* configuration only: directory locations, allowed
Excel extensions, the temporary lock-file prefix to ignore, and the worksheet
name the runner reads from each dropped workbook. It deliberately contains no
business rules (no contract matching, costout, movement, aggregation or
reporting logic) — those live in the existing, unchanged pipeline modules.

The configuration is expressed as a dataclass so tests can override any path or
value without touching the pipeline.
"""

from dataclasses import dataclass, field
from pathlib import Path


# Repository root is two levels up from this file (scripts/ -> repo root).
_REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class RunnerConfig:
    """Runtime paths and file rules for the weekly snapshot runner."""

    # Base data directory and its sub-folders.
    data_dir: Path = _REPO_ROOT / "data"
    incoming_dir: Path = _REPO_ROOT / "data" / "incoming"
    archive_dir: Path = _REPO_ROOT / "data" / "archive"
    outputs_dir: Path = _REPO_ROOT / "data" / "outputs"
    state_dir: Path = _REPO_ROOT / "data" / "state"

    # Machine-readable last-successful-run state file.
    state_filename: str = "last_successful_run.json"

    # File-eligibility rules.
    allowed_extensions: tuple = (".xlsx",)
    lock_file_prefix: str = "~$"

    # Worksheet the pipeline reads from a dropped workbook. This is a runtime
    # input, not a business rule. The existing pipeline reads a named worksheet,
    # so the runner must be told which one to use. Default is the sheet the
    # pipeline treats as the "current" snapshot.
    snapshot_worksheet: str = "Live dashboard"

    @property
    def state_file(self) -> Path:
        """Full path to the last-successful-run state file."""
        return self.state_dir / self.state_filename

    def ensure_directories(self) -> None:
        """Create the configured runtime directories if they do not exist."""
        for directory in (
            self.incoming_dir,
            self.archive_dir,
            self.outputs_dir,
            self.state_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def default_config() -> RunnerConfig:
    """Return the default runtime configuration."""
    return RunnerConfig()
