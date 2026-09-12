"""
MPLADS AI INVESTIGATOR — V4 RISK INTELLIGENCE ENGINE

Purpose:
    Explainable investigation-priority scoring using the V4 lifecycle dataset.

Important:
    This is NOT a fraud classifier and does NOT establish fraud/corruption.
    Scores indicate which projects may deserve closer human verification.

Expected input:
    data/investigation_projects_v4.csv

Design:
    - Preserves the existing V3 contextual cost signal.
    - Adds financial reconciliation, timeline, payment, evidence and data-quality signals.
    - Uses contextual peer statistics rather than a single national threshold.
    - Returns transparent reasons for every score.
"""

from pathlib import Path
import math
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "investigation_projects_v4.csv"

# Investigation-priority bands.
HIGH_THRESHOLD = 50
MEDIUM_THRESHOLD = 25


def _num(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _bool(value):
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _text_quality(value):
    text = "" if pd.isna(value) else str(value).strip()
    if not text:
        return 0.0
    words = text.split()
    # Conservative description-quality proxy; it is an evidence-quality
    # indicator, not a measure of project quality.
    if len(text) < 25 or len(words) < 5:
        return 0.35
    if len(text) < 60 or len(words) < 10:
        return 0.65
    return 1.0


def load_v4_data(path=DATA_PATH):
    df = pd.read_csv(path, low_memory=False)

    required = [
        "Work ID",
        "State",
        "House",
        "Category",
        "Final Amount (₹)",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            "V4 dataset is missing required columns: " + ", ".join(missing)
        )

    for col in [
        "Final Amount (₹)",
        "Recommended Amount (₹)",
        "Sanctioned Amount (₹)",
        "Expenditure_Total",
        "Expenditure_minus_Final",
        "Expenditure_to_Final_Ratio",
        "Sanction_minus_Recommended",
        "Recommendation_to_Sanction_Days",
        "Sanction_to_Completion_Days",
        "Pending_Payment_Count",
        "Transaction_Count",
        "Vendor_Count",
        "Recommendation Duplicate Count",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def _peer_group(df, row):
    """State + House + Category peer group, matching the V3 philosophy."""
    mask = (
        df["State"].fillna("").astype(str).eq(str(row.get("State", "")))
        & df["House"].fillna("").astype(str).eq(str(row.get("House", "")))
        & df["Category"].fillna("").astype(str).eq(str(row.get("Category", "")))
    )
    return df.loc[mask].copy()


def _cost_signal(df, row):
    amount = _num(row.get("Final Amount (₹)"))
    if amount is None or amount <= 0:
        return 0, None, None, None

    peers = _peer_group(df, row)
    peer_amounts = pd.to_numeric(peers["Final Amount (₹)"], errors="coerce").dropna()
    peer_amounts = peer_amounts[peer_amounts > 0]

    if len(peer_amounts) == 0:
        return 0, None, 0, None

    median = float(peer_amounts.median())
    ratio = amount / median if median else None
    group_size = int(len(peer_amounts))

    # Keep the V3-style contextual thresholds.
    points = 0
    if ratio is not None:
        if ratio >= 5:
            points = 30
        elif ratio >= 3:
            points = 20
        elif ratio >= 2:
            points = 10
        elif ratio >= 1.5:
            points = 5

    return points, median, group_size, ratio


def score_project(df, work_id):
    matches = df.loc[df["Work ID"].astype(str) == str(work_id)]
    if matches.empty:
        raise KeyError(f"Work ID {work_id} was not found in the V4 dataset.")

    row = matches.iloc[0]
    score = 0
    reasons = []
    categories = []

    # ------------------------------------------------------------
    # 1. CONTEXTUAL COST
    # ------------------------------------------------------------
    pts, peer_median, peer_count, amount_ratio = _cost_signal(df, row)
    score += pts

    if pts:
        categories.append("Cost context")
        if amount_ratio is not None and peer_median is not None:
            reasons.append(
                f"Project amount is {amount_ratio:.1f}× the contextual peer median "
                f"(peer group: {peer_count:,} projects)."
            )

    amount = _num(row.get("Final Amount (₹)"))
    if amount is not None and amount >= 3_000_000:
        score += 3
        categories.append("Project value")
        reasons.append("Project has a high final value (≥ ₹30 lakh).")

    # ------------------------------------------------------------
    # 2. EVIDENCE QUALITY
    # ------------------------------------------------------------
    if "Has Images" in row and not _bool(row.get("Has Images")):
        score += 2
        categories.append("Evidence")
        reasons.append("Image evidence is unavailable.")

    quality = _text_quality(row.get("Work Description"))
    if quality < 0.65:
        points = 3 if quality <= 0.35 else 2
        score += points
        categories.append("Evidence")
        reasons.append("Project description contains limited information.")

    # ------------------------------------------------------------
    # 3. FINANCIAL RECONCILIATION
    # ------------------------------------------------------------
    fin_flag = str(row.get("Financial_Reconciliation_Flag", "")).strip()

    if fin_flag == "Expenditure record unavailable":
        score += 4
        categories.append("Financial")
        reasons.append("Expenditure record is unavailable for reconciliation.")
    elif fin_flag == "Expenditure differs from final amount":
        diff = _num(row.get("Expenditure_minus_Final"))
        score += 8
        categories.append("Financial")
        if diff is not None:
            reasons.append(
                f"Aggregated expenditure differs from the final amount by "
                f"₹{abs(diff):,.0f}."
            )
        else:
            reasons.append("Aggregated expenditure differs from the final amount.")

    sanction_gap = _num(row.get("Sanction_minus_Recommended"))
    if sanction_gap is not None and abs(sanction_gap) > 1:
        score += 3
        categories.append("Financial")
        direction = "higher" if sanction_gap > 0 else "lower"
        reasons.append(
            f"Sanctioned amount is ₹{abs(sanction_gap):,.0f} {direction} "
            f"than the recommended amount."
        )

    # ------------------------------------------------------------
    # 4. PAYMENT STATUS
    # ------------------------------------------------------------
    pending_count = _num(row.get("Pending_Payment_Count"))
    if pending_count is not None and pending_count > 0:
        score += 3
        categories.append("Payment")
        reasons.append(
            f"{int(pending_count):,} payment transaction(s) are marked in-progress."
        )

    # ------------------------------------------------------------
    # 5. TIMELINE
    # ------------------------------------------------------------
    timeline_flag = str(row.get("Timeline_Flag", "")).strip()

    if timeline_flag == "Sanction date unavailable":
        score += 2
        categories.append("Timeline")
        reasons.append("Sanction date is unavailable, limiting lifecycle verification.")
    elif timeline_flag == "Date sequence needs review":
        score += 5
        categories.append("Timeline")
        reasons.append("Project dates have a sequence that needs review.")

    # We deliberately do not award points merely because a project took
    # a long time; future peer-duration benchmarking can be added here.

    # ------------------------------------------------------------
    # 6. DATA QUALITY
    # ------------------------------------------------------------
    duplicate_count = _num(row.get("Recommendation Duplicate Count"))
    if duplicate_count is not None and duplicate_count > 1:
        score += 2
        categories.append("Data quality")
        reasons.append(
            f"{int(duplicate_count):,} recommendation record(s) exist for this Work ID."
        )

    if peer_count is not None and peer_count <= 3:
        score += 2
        categories.append("Context")
        reasons.append("Very small contextual comparison group.")

    # Optional temporal concentration signal retained from V3 if present.
    concentration = _num(row.get("Temporal_Concentration_Count"))
    if concentration is not None and concentration >= 1000:
        score += 1
        categories.append("Context")
        reasons.append("High project concentration is present in the same period.")

    score = int(min(score, 100))

    if score >= HIGH_THRESHOLD:
        level = "HIGH"
    elif score >= MEDIUM_THRESHOLD:
        level = "MEDIUM"
    else:
        level = "LOW"

    # Remove duplicate dimension names while preserving order.
    dimensions = list(dict.fromkeys(categories))

    return {
        "work_id": int(row["Work ID"]),
        "risk_score": score,
        "risk_level": level,
        "investigation_priority": level,
        "reasons": reasons,
        "risk_dimensions": dimensions,
        "peer_median": peer_median,
        "peer_group_size": peer_count,
        "amount_ratio_to_peer_median": amount_ratio,
        "financial_reconciliation": fin_flag or "Unavailable",
        "timeline_flag": timeline_flag or "Unavailable",
        "has_pending_payment": _bool(row.get("Has_Pending_Payment")),
        "expenditure_total": _num(row.get("Expenditure_Total")),
        "final_amount": amount,
    }


def score_all(path=DATA_PATH):
    df = load_v4_data(path)
    results = []

    for work_id in df["Work ID"].dropna().unique():
        try:
            results.append(score_project(df, work_id))
        except Exception:
            # One malformed row should not stop the full screening run.
            continue

    return pd.DataFrame(results)


if __name__ == "__main__":
    df = load_v4_data()
    result = score_all()

    print("=" * 70)
    print("MPLADS AI INVESTIGATOR — V4 RISK INTELLIGENCE")
    print("=" * 70)
    print(f"Projects scored : {len(result):,}")
    print()
    print(result["risk_level"].value_counts().sort_index().to_string())
    print()
    print("Top 10 investigation-priority projects:")
    print(
        result.sort_values(["risk_score", "work_id"], ascending=[False, True])
        [["work_id", "risk_score", "risk_level"]]
        .head(10)
        .to_string(index=False)
    )
    print()
    print("NOTE: Scores are investigation-priority indicators, not fraud findings.")
