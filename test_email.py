from src.reporting.leadership_email import (
    generate_leadership_email,
)

print(
    generate_leadership_email(
        leadership_insights_path="data/outputs/20260902T045321Z-210f2573/leadership_insights.txt",
        risks_watchouts_path="data/outputs/20260902T045321Z-210f2573/risks_watchouts.txt",
    )
)