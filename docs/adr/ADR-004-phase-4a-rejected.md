# ADR-004: Reject Phase 4A (Promote Validation Layer)

- Status: Accepted
- Date: 2026-08-27
- Deciders: IT Simplification project

## Context

A "Phase 4A" was proposed to add a validation layer around the runner's
`promote` stage, on the assumption that artefacts might reach promotion in an
invalid or unvalidated state.

We inspected the pipeline to test that assumption.

### What `promote` actually consumes

In `scripts/run_weekly_snapshot.py`, `promote` (stage 9) does only this:

```python
final_output = config.outputs_dir / run_id
if final_output.exists():
    shutil.rmtree(final_output)
shutil.move(str(temp_dir), str(final_output))
```

It moves the temporary output directory to `outputs/<run_id>`. It does not open,
read, parse, or inspect any artefact. Its sole input is the `temp_dir` directory.

### Validation that already runs before `promote`

Every stage before `promote` executes inside the `run()` `try:` block; any
failure raises, skips `promote`, and the `finally:` deletes `temp_dir`. So
`promote` is only reached when all prior stages succeed.

| Stage | Guarantee enforced (raises on failure) |
|-------|----------------------------------------|
| discovery | Exactly one eligible workbook (`DiscoveryError`) |
| previous_resolution | Baseline exists, on disk, distinct from current (`BaselineError`) |
| preflight | Both workbooks open, contain the worksheet, extract non-empty vendor data with a `Contract` column (`PreflightError`) |
| analysis / reporting | 2A–3B run; any exception aborts before promote |
| weekly_update | Fails fast on missing inputs (`WeeklyUpdateError`) |
| leadership_insights | Fails fast on missing inputs (`LeadershipInsightsError`) |
| risks_watchouts | Fails fast on missing inputs (`RisksWatchoutsError`) |
| reporting_package | Validates all five artefacts (`ReportingPackageError`) |
| promotion_package | Validates all six artefacts exist **and** are non-empty (`PromotionPackageError`) |

The stage immediately before `promote` — `promotion_package` (3D.5) — already
performs the strongest content-presence validation of the full output set and
fails hard before `promote` runs.

## Decision

**Phase 4A is rejected. No promote-validation stage will be added.**

A Phase 4A validator that checks artefacts before promotion would re-verify the
exact six files that `generate_promotion_package` validated one line earlier.
That duplicates existing logic, which the project's milestone constraints
explicitly prohibit, and closes no open gap:

- `promote` has no unvalidated dependency; it moves an already-built directory.
- The "nothing invalid reaches promote" invariant is enforced and tested
  (`tests/test_promotion_package.py`, `tests/test_reporting_package_runner.py`,
  `scripts/test_run_weekly_snapshot.py` failure-isolation cases).
- Failure isolation (no promote / archive / state-update on any failure; partial
  `temp_dir` cleaned in `finally`) is implemented and tested.

## Consequences

- The reporting/packaging pipeline is considered complete for this project scope.
- Recommend closing the project at the current milestone.
- Residual risks that Phase 4A would **not** have addressed, and which remain
  deliberately out of scope:
  1. **Content correctness (semantic validation).** All gates check presence and
     non-emptiness, not that report values match the analysis result. Adding this
     requires recomputation/comparison, which contradicts the project's
     reporting-only, no-analytics boundary. If ever desired, it must be an
     explicit, separately-scoped decision — not a promote gate.
  2. **Concurrency.** Concurrent runs on the same directories are not lock-guarded.
  3. **Worksheet-name coupling.** The single-snapshot-per-workbook assumption is an
     upstream (preflight) data-shape risk, not a promote concern.

## Alternatives considered

- **Add Phase 4A promote validation** — rejected: duplicates `promotion_package`
  validation, adds no coverage.
- **Add semantic (content-correctness) validation** — rejected for this scope:
  reintroduces analytics/comparison the project explicitly excludes; would be a
  new scope decision rather than a gap closure.
