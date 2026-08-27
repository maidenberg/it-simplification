"""
promotion_package.py — Promotion Package assembly (Milestone 3D.5).

Packaging/distribution only. Validates the reporting artefacts already produced
by the pipeline, copies them unchanged into a `promotion_package/` directory, and
writes a metadata-only manifest.json.

No analytics, calculations, movement detection, or reporting logic are performed
or duplicated here. Files are copied byte-for-byte.
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


class PromotionPackageError(Exception):
    """Raised when a required artefact is missing or empty."""


PROMOTION_PACKAGE_DIRNAME = "promotion_package"
PROMOTION_MANIFEST_FILENAME = "manifest.json"

# Reporting artefacts to package, in a fixed order.
REQUIRED_ARTEFACTS = [
    "executive_summary.txt",
    "key_movements.txt",
    "weekly_update.md",
    "leadership_insights.txt",
    "risks_watchouts.txt",
    "reporting_package.txt",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_promotion_package(
    source_dir,
    run_id: str,
    package_dir=None,
    generated_at: str | None = None,
) -> Path:
    """
    Build the promotion package from existing reporting artefacts.

    Validates that every required artefact exists and is non-empty, copies each
    unchanged into `package_dir` (default: source_dir/promotion_package), and
    writes a metadata-only manifest.json.

    Parameters
    ----------
    source_dir : str or Path
        Directory containing the existing reporting artefacts.
    run_id : str
        Run identifier recorded in the manifest.
    package_dir : str or Path, optional
        Destination package directory. Defaults to source_dir/promotion_package.
    generated_at : str, optional
        Timestamp recorded in the manifest. Defaults to current UTC time. Provide
        a fixed value for deterministic output.

    Returns
    -------
    Path
        Path to the created promotion_package directory.

    Raises
    ------
    PromotionPackageError
        If a required artefact is missing or empty (message identifies it).
    """
    source_dir = Path(source_dir)

    # 1 + 2. Validate existence and non-emptiness (in fixed order).
    for name in REQUIRED_ARTEFACTS:
        artefact = source_dir / name
        if not artefact.exists():
            raise PromotionPackageError(
                f"Required reporting artefact not found: {artefact}"
            )
        if artefact.stat().st_size == 0:
            raise PromotionPackageError(
                f"Required reporting artefact is empty: {artefact}"
            )

    # 3. Create the promotion_package directory. If it already exists, replace
    # it so no stale content remains.
    package_dir = Path(package_dir) if package_dir else source_dir / PROMOTION_PACKAGE_DIRNAME
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)

    # 4. Copy all reporting artefacts unchanged.
    for name in REQUIRED_ARTEFACTS:
        shutil.copy2(source_dir / name, package_dir / name)

    # 5. Metadata-only manifest.
    manifest = {
        "run_id": run_id,
        "generated_at": generated_at if generated_at is not None else _now_iso(),
        "files": list(REQUIRED_ARTEFACTS),
    }
    with open(package_dir / PROMOTION_MANIFEST_FILENAME, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    return package_dir
