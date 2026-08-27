# Documentation

# IT Simplification Automation

## Purpose

Automate weekly IT Simplification leadership reporting by analysing cost-out data and generating executive-ready communications.

Target outputs:

- Executive Summary
- Key Metrics
- Highlights
- Risks and Watchouts
- Next Steps

## Current Status

### Working Components

#### ingest.py

Responsible for:

- Loading vendor data from Excel
- Validating required fields
- Normalising column names
- Converting data types

Current workbook configuration:

- Source workbook: Fake vendor data.xlsx
- Source sheet: Fake Simplified View

Additional transformations:

- Maps workbook column names to internal schema
- Derives quarter from contract expiry date
- Converts Finalised? values (Y/blank) into booleans

#### communications_engine.py

Responsible for:

- Portfolio metrics
- Executive Summary generation
- Highlights generation
- Risk generation
- Next Steps generation

#### generate_drafts.py

CLI entry point that:

1. Loads source data
2. Runs analysis
3. Generates markdown output

Output:

output/drafts.md

---

## Current Architecture

Excel Workbook
    ↓
ingest.py
    ↓
communications_engine.py
    ↓
generate_drafts.py
    ↓
drafts.md

---

## Known Limitations

Current solution is a single-snapshot reporting engine.

It generates reporting from one dataset only.

The following capability is not yet implemented:

Snapshot Wk 1
      ↓
Compare
      ↓
Snapshot Wk 2
      ↓
Movement Analysis
      ↓
Leadership Update

---

## Priority Backlog

### High Priority

Implement snapshot comparison engine.

Required outputs:

- New opportunities identified
- Savings finalised this week
- Cost-out movement
- Budget movement
- Vendor status changes
- Weekly leadership insights

### Medium Priority

Improve narrative quality:

- Executive Summary
- Risks
- Leadership commentary

### Low Priority

Enhance report formatting and output options.

---

## Recovery Notes (August 2026)

MVP recovery completed:

- Fixed workbook ingestion
- Added worksheet selection
- Added column mappings
- Derived quarter field
- Fixed Finalised? value handling
- Restored successful draft generation

Current state:

✅ MVP operational
✅ Draft generation operational
❌ Snapshot comparison not yet implemented
