from dataclasses import dataclass
from src.reporting.dashboard_status import get_actionable_statuses


@dataclass
class LeadershipCandidate:
    vendor: str
    contract: str
    v1_budget: float
    renewal_price: float
    costout: float
    commentary: str = ""


def get_leadership_candidates(
    contracts,
    budget_threshold: float = 50_000,
    costout_threshold: float = 20_000,
):
    """
    Return financially material contracts only.
    """

    candidates = []

    for contract in contracts:
        if (
            contract.v1_budget >= budget_threshold
            or abs(contract.costout) >= costout_threshold
        ):
            candidates.append(
                LeadershipCandidate(
                    vendor=contract.vendor,
                    contract=contract.contract,
                    v1_budget=contract.v1_budget,
                    renewal_price=contract.renewal_price,
                    costout=contract.costout,
                )
            )

    return candidates

def build_candidate_pool(
    current_snapshot_df,
    budget_threshold: float = 50_000,
    costout_threshold: float = 10_000,
):
    candidates = []

    for _, row in current_snapshot_df.iterrows():

        try:
            v1_budget = float(row.get("V1 budget", 0) or 0)
        except Exception:
            v1_budget = 0

        try:
            renewal_price = float(row.get("Renewal price", 0) or 0)
        except Exception:
            renewal_price = 0

        try:
            costout = float(row.get("Costout", 0) or 0)
        except Exception:
            costout = 0

        if (
            v1_budget >= budget_threshold
            or abs(costout) >= costout_threshold
        ):
            candidates.append(
                LeadershipCandidate(
                    vendor=str(row.get("Vendor", "")),
                    contract=str(row.get("Contract", "")).replace (
                        "[No Contract] ",
                        ""
                    ),
                    v1_budget=v1_budget,
                    renewal_price=renewal_price,
                    costout=costout,
                )
            )

    return candidates

def load_candidate_commentary(path):
    return get_actionable_statuses(path)

def build_commentary_lookup(commentary_df):
    lookup = {}

    for _, row in commentary_df.iterrows():
        key = (
            str(row["Vendor"]).strip(),
            str(row["Contract"]).strip(),
        )

        lookup[key] = row["latest_commentary"]

    return lookup

def enrich_candidates_with_commentary(
    candidates,
    commentary_lookup,
):
    for candidate in candidates:
        key = (
            candidate.vendor.strip(),
            candidate.contract.strip(),
        )

        candidate.commentary = commentary_lookup.get(key, "")

    return candidates

def candidates_with_meaningful_commentary(candidates):
    return [
        candidate
        for candidate in candidates
        if (
            candidate.commentary
            or candidate.costout < -30000
            or candidate.costout > 30000
        )
    ]

def executive_relevance_score(candidate):
    """
    Higher score = more likely Lewis wants airtime.
    """

    score = 0

    commentary = candidate.commentary.lower()

    # Major wins

    if "renewed" in commentary:
        score += 100

    if "approved" in commentary:
        score += 80

    if "commercials approved" in commentary:
        score += 120

    # Risks

    if "no progress" in commentary:
        score += 150

    if "no update" in commentary:
        score += 150

    if "under discussion" in commentary:
        score += 90

    if "awaiting" in commentary:
        score += 110

    if "signature" in commentary:
        score += 100

    if "approval" in commentary:
        score += 100

    if "commercial" in commentary:
        score += 150

    if "working on it" in commentary:
        score += 60

    if "renewed for 2 years" in commentary:
        score += 75

    # Financial significance

    if candidate.costout > 0:
        score += min (candidate.costout / 1000, 100)

    if candidate.costout < 0:
        score += min (abs(candidate.costout) / 1000, 200)

    return score

def rank_candidates_for_leadership(candidates):
    """
    Rank candidates by executive relevance.
    """

    ranked = sorted(
        candidates,
        key=executive_relevance_score,
        reverse=True,
    )

    for candidate in ranked[:20]:
        print (
            f"SCORE={executive_relevance_score(candidate):.1f} | "
            f"{candidate.vendor} | "
            f"{candidate.contract} | "
            f"{candidate.commentary}"
        )

    return ranked

def classify_leadership_theme(candidate):

    commentary = candidate.commentary.lower()

    if "renewed" in commentary:
        return "major_win"

    if "approved" in commentary:
        return "major_win"

    if "no progress" in commentary:
        return "risk"

    if "no update" in commentary:
        return "risk"

    if "approval" in commentary:
        return "decision_required"

    if "signature" in commentary:
        return "decision_required"

    if "awaiting" in commentary:
        return "decision_required"

    if candidate.costout < -30000:
        return "financial_risk"

    if candidate.costout > 30000:
        return "financial_win"

    if "under discussion" in commentary:
        return "risk"

    if "working on it" in commentary:
        return "risk"

    print (
        candidate.contract,
        "->",
        commentary,
    )
    return "general"