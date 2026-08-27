"""
config_loader.py — External runtime configuration loader (Milestone 3C.2).

Loads an optional JSON configuration file and merges its values into the typed
RunnerConfig object. This component contains no analysis or reporting logic; it
only reads, validates, resolves paths, and merges runtime settings.

Supported configuration keys (config/weekly_snapshot.json):
    snapshot_worksheet   : str
    incoming_directory   : str  (repo-relative or absolute path)
    archive_directory    : str
    outputs_directory    : str
    state_directory      : str
    allowed_extensions   : list[str]  (each like ".xlsx")

Validation rules:
    - The file must contain a JSON object.
    - Unknown keys are rejected with a clear message.
    - Each known key must have the correct value type.
    - Malformed JSON is rejected with a clear message.
    - Relative paths are resolved against the repository root.

Precedence is applied by the caller (run_weekly_snapshot.py):
    CLI override  >  external configuration file  >  RunnerConfig defaults.
"""

import json
from dataclasses import replace
from pathlib import Path

from runner_config import RunnerConfig


# Repository root is two levels up from this file (scripts/ -> repo root).
_REPO_ROOT = Path(__file__).resolve().parent.parent

# Default location of the external configuration file.
DEFAULT_CONFIG_PATH = _REPO_ROOT / "config" / "weekly_snapshot.json"

# Map each supported JSON key to (RunnerConfig field, expected python type,
# whether the value is a repo-relative path).
_STRING_KEYS = {"snapshot_worksheet"}
_PATH_KEYS = {
    "incoming_directory": "incoming_dir",
    "archive_directory": "archive_dir",
    "outputs_directory": "outputs_dir",
    "state_directory": "state_dir",
}
_LIST_KEYS = {"allowed_extensions"}

SUPPORTED_KEYS = set(_STRING_KEYS) | set(_PATH_KEYS) | set(_LIST_KEYS)


class ConfigError(Exception):
    """Raised when external configuration is missing content or malformed."""


def _resolve_path(value: str) -> Path:
    """Resolve a configured path against the repository root when relative."""
    path = Path(value)
    if not path.is_absolute():
        path = _REPO_ROOT / path
    return path


def _validate_types(raw: dict) -> None:
    """Validate supported keys and value types. Raise ConfigError on problems."""
    unknown = sorted(set(raw.keys()) - SUPPORTED_KEYS)
    if unknown:
        raise ConfigError(
            f"Unknown configuration key(s): {', '.join(unknown)}. "
            f"Supported keys: {', '.join(sorted(SUPPORTED_KEYS))}."
        )

    for key in _STRING_KEYS:
        if key in raw and not isinstance(raw[key], str):
            raise ConfigError(
                f"Configuration key '{key}' must be a string, got "
                f"{type(raw[key]).__name__}."
            )

    for key in _PATH_KEYS:
        if key in raw and not isinstance(raw[key], str):
            raise ConfigError(
                f"Configuration key '{key}' must be a string path, got "
                f"{type(raw[key]).__name__}."
            )

    for key in _LIST_KEYS:
        if key in raw:
            value = raw[key]
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                raise ConfigError(
                    f"Configuration key '{key}' must be a list of strings."
                )


def load_config_file(path: Path) -> dict:
    """
    Load and validate the external JSON configuration file.

    Raises
    ------
    ConfigError
        If the file does not exist, is not valid JSON, is not a JSON object,
        contains unknown keys, or has values of the wrong type.
    """
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Malformed JSON in configuration file {path}: {exc}")

    if not isinstance(raw, dict):
        raise ConfigError(
            f"Configuration file {path} must contain a JSON object at the top "
            f"level, got {type(raw).__name__}."
        )

    _validate_types(raw)
    return raw


def merge_into_config(base: RunnerConfig, raw: dict) -> RunnerConfig:
    """
    Return a new RunnerConfig with values from `raw` merged over `base`.

    Only keys present in `raw` override the base. Paths are resolved against the
    repository root. `data_dir`, `state_filename`, and `lock_file_prefix` are not
    externally configurable and are preserved from `base`.
    """
    overrides = {}

    for key in _STRING_KEYS:
        if key in raw:
            overrides[key] = raw[key]

    for key, field_name in _PATH_KEYS.items():
        if key in raw:
            overrides[field_name] = _resolve_path(raw[key])

    for key in _LIST_KEYS:
        if key in raw:
            # RunnerConfig stores allowed_extensions as a tuple.
            overrides["allowed_extensions"] = tuple(raw[key])

    return replace(base, **overrides)


def build_config(
    config_path: Path | None = None,
    worksheet_override: str | None = None,
    require_config_file: bool = False,
) -> RunnerConfig:
    """
    Build a RunnerConfig applying precedence: CLI > file > defaults.

    Parameters
    ----------
    config_path : Path or None
        Path to the external JSON config. If None, the default path is used when
        it exists; a missing default file is not an error (defaults apply).
    worksheet_override : str or None
        CLI worksheet override; takes precedence over file and defaults.
    require_config_file : bool
        If True, a missing config file raises ConfigError. Used when the operator
        explicitly passes --config.

    Raises
    ------
    ConfigError
        On any configuration validation failure.
    """
    config = RunnerConfig()  # defaults

    # Layer 2: external configuration file.
    if config_path is not None:
        # Explicit path: the file must exist and be valid.
        raw = load_config_file(config_path)
        config = merge_into_config(config, raw)
    else:
        # Implicit default path: apply only if present, else keep defaults.
        if DEFAULT_CONFIG_PATH.exists():
            raw = load_config_file(DEFAULT_CONFIG_PATH)
            config = merge_into_config(config, raw)
        elif require_config_file:
            raise ConfigError(
                f"Configuration file not found: {DEFAULT_CONFIG_PATH}"
            )

    # Layer 1: CLI override (highest precedence).
    if worksheet_override is not None:
        if not isinstance(worksheet_override, str) or worksheet_override.strip() == "":
            raise ConfigError("--worksheet override must be a non-empty string.")
        config = replace(config, snapshot_worksheet=worksheet_override)

    return config
