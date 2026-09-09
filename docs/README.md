# Documentation

# IT Simplification Weekly Leadership Email Automation

## Purpose

Generate a weekly leadership email for Matt Toohey and Lewis Lee that highlights:

- material week-on-week movement
- significant cost-out improvement
- significant cost-out deterioration
- material financial exposure
- vendor renewals requiring attention
- blocked decisions and dependencies
- leadership-relevant risks and watchouts

The weekly leadership email is the primary business deliverable.

---

## Current Architecture

### Active Pipeline

```text
analysis.json
↓
leadership candidate generation
↓
leadership_insights.txt
↓
risks_watchouts.txt
↓
leadership_email.txt
```

### Primary Artefacts

| Artefact | Purpose |
|-----------|-----------|
| analysis.json | Portfolio analysis and candidate inputs |
| leadership_insights.txt | Leadership-focused insights and financial watchouts |
| risks_watchouts.txt | Risks, watchouts and observations |
| leadership_email.txt | Final weekly leadership email |

---

## Current Status

### Completed Components

- Snapshot ingestion
- Dashboard extraction
- Contract extraction
- Weekly snapshot comparison
- Movement detection
- Commentary enrichment
- Leadership candidate generation
- Theme classification
- Leadership insights generation
- Risks and watchouts generation
- Leadership email generation
- Judgement validation

### Validation Status

The leadership judgement validation framework has been completed and approved.

Validation confirms that:

- material financial risks are surfaced
- financially significant deteriorations are not suppressed
- leadership-relevant items are promoted appropriately
- commentary remains traceable to source data
- important issues can be identified quickly from the final email

---

## Primary Output

### leadership_email.txt

The final business deliverable.

The email is intended to provide:

- what changed
- what improved
- what deteriorated
- items requiring leadership awareness
- material financial exposure
- leadership-relevant watchouts

Outputs should remain grounded in source commentary and portfolio data.

---

## Architecture Principles

- Reuse existing reporting outputs.
- Do not rebuild extraction, comparison, ranking, scoring, or classification logic.
- Turn data into leadership judgement.
- Maintain traceability to source values and commentary.
- Prefer concise executive signals over narrative expansion.
- Optimise for usefulness within approximately 30 seconds of review.

---

## Active Workstream

Documentation and Comment Cleanup

Current objective:

- remove references to retired artefacts
- align documentation with implemented architecture
- improve maintainability
- avoid behavioural changes

Documentation should reflect the active delivery path and current runtime behaviour.

---

## Retired Artefacts

The following artefacts have been removed from the active leadership-email pipeline:

- executive_summary.txt
- key_movements.txt
- reporting_package.txt
- promotion_package/

These artefacts may remain in historical documentation but should not be described as part of the current runtime architecture.
