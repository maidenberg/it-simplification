# TODO:
# Join LeadershipCandidate objects to
# get_actionable_statuses() output
# using Vendor + Contract.

from dataclasses import dataclass
from reporting.dashboard_status import get_actionable_statuses


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
                    contract=str(row.get("Contract", "")),
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
        if candidate.commentary
    ]