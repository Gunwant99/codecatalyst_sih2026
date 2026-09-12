"""
MPLADS AI INVESTIGATOR — V4 OPTIMIZED RISK INTELLIGENCE ENGINE

Uses the unified V4 lifecycle dataset:
    data/investigation_projects_v4.csv

This version is designed for the full 116k+ project dataset.
Peer statistics are calculated once and then applied vectorially,
instead of scanning the entire dataframe for every project.

IMPORTANT:
Scores are investigation-priority indicators, NOT fraud probabilities
and do not establish fraud/corruption/wrongdoing.
"""

from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "investigation_projects_v4.csv"

HIGH_THRESHOLD = 50
MEDIUM_THRESHOLD = 25

PEER_KEYS = ["State", "House", "Category"]


def load_v4_data(path=DATA_PATH):
    df = pd.read_csv(path, low_memory=False)

    required = ["Work ID", "State", "House", "Category", "Final Amount (₹)"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    numeric_cols = [
        "Work ID",
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
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Normalize peer keys so missing values don't create misleading groups.
    for col in PEER_KEYS:
        df[col] = df[col].fillna("Unknown").astype(str).str.strip()

    return df


def _description_quality(text):
    """Simple evidence-quality indicator, not a project-quality score."""
    text = "" if pd.isna(text) else str(text).strip()
    words = text.split()
    if not text or len(text) < 25 or len(words) < 5:
        return 0.35
    if len(text) < 60 or len(words) < 10:
        return 0.65
    return 1.0


def build_peer_stats(df):
    """
    Calculate contextual cost statistics once.

    Peer definition:
        State + House + Category

    Median is used because it is robust to extreme project values.
    """
    amounts = pd.to_numeric(df["Final Amount (₹)"], errors="coerce")
    valid = df.loc[amounts.gt(0), PEER_KEYS + ["Final Amount (₹)"]].copy()

    peer = (
        valid.groupby(PEER_KEYS, dropna=False)["Final Amount (₹)"]
        .agg(peer_median="median", peer_count="count")
        .reset_index()
    )
    return peer


def prepare_scored_dataframe(df):
    """Vectorized scoring for the complete dataset."""
    out = df.copy()

    peer = build_peer_stats(out)
    out = out.merge(peer, on=PEER_KEYS, how="left")

    amount = pd.to_numeric(out["Final Amount (₹)"], errors="coerce")
    out["Amount_Ratio_to_Peer_Median"] = np.where(
        out["peer_median"].gt(0),
        amount / out["peer_median"],
        np.nan,
    )

    # ------------------------------------------------------------
    # Base score
    # ------------------------------------------------------------
    out["Risk_Score"] = 0
    out["Risk_Reasons"] = ""
    out["Risk_Dimensions"] = ""

    def add_points(mask, points, reason, dimension):
        nonlocal out
        out.loc[mask, "Risk_Score"] += points

        current = out.loc[mask, "Risk_Reasons"].fillna("")
        out.loc[mask, "Risk_Reasons"] = np.where(
            current.eq(""),
            reason,
            current + " | " + reason,
        )

        current_dim = out.loc[mask, "Risk_Dimensions"].fillna("")
        out.loc[mask, "Risk_Dimensions"] = np.where(
            current_dim.eq(""),
            dimension,
            current_dim + " | " + dimension,
        )

    # ------------------------------------------------------------
    # 1. Contextual cost anomaly
    # ------------------------------------------------------------
    ratio = out["Amount_Ratio_to_Peer_Median"]

    add_points(
        ratio.ge(5),
        30,
        "Final amount is ≥5× the contextual peer median",
        "Cost context",
    )
    add_points(
        ratio.ge(3) & ratio.lt(5),
        20,
        "Final amount is 3–5× the contextual peer median",
        "Cost context",
    )
    add_points(
        ratio.ge(2) & ratio.lt(3),
        10,
        "Final amount is 2–3× the contextual peer median",
        "Cost context",
    )
    add_points(
        ratio.ge(1.5) & ratio.lt(2),
        5,
        "Final amount is 1.5–2× the contextual peer median",
        "Cost context",
    )

    add_points(
        amount.ge(3_000_000),
        3,
        "Project has a high final value (≥ ₹30 lakh)",
        "Project value",
    )

    # ------------------------------------------------------------
    # 2. Evidence quality
    # ------------------------------------------------------------
    if "Has Images" in out.columns:
        no_images = ~out["Has Images"].fillna(False).astype(bool)
        add_points(
            no_images,
            2,
            "Image evidence is unavailable",
            "Evidence",
        )

    if "Work Description" in out.columns:
        quality = out["Work Description"].map(_description_quality)
        add_points(
            quality.lt(0.65),
            3,
            "Project description contains limited information",
            "Evidence",
        )

    # ------------------------------------------------------------
    # 3. Financial reconciliation
    # ------------------------------------------------------------
    if "Financial_Reconciliation_Flag" in out.columns:
        fin = out["Financial_Reconciliation_Flag"].fillna("").astype(str)

        add_points(
            fin.eq("Expenditure record unavailable"),
            4,
            "Expenditure record is unavailable for reconciliation",
            "Financial",
        )
        add_points(
            fin.eq("Expenditure differs from final amount"),
            8,
            "Aggregated expenditure differs from final amount",
            "Financial",
        )

    if "Sanction_minus_Recommended" in out.columns:
        sanction_gap = pd.to_numeric(
            out["Sanction_minus_Recommended"], errors="coerce"
        )
        add_points(
            sanction_gap.abs().gt(1),
            3,
            "Sanctioned amount differs from recommended amount",
            "Financial",
        )

    # ------------------------------------------------------------
    # 4. Payment
    # ------------------------------------------------------------
    if "Pending_Payment_Count" in out.columns:
        pending = pd.to_numeric(out["Pending_Payment_Count"], errors="coerce").fillna(0)
        add_points(
            pending.gt(0),
            3,
            "One or more payment transactions are in-progress",
            "Payment",
        )

    # ------------------------------------------------------------
    # 5. Timeline
    # ------------------------------------------------------------
    if "Timeline_Flag" in out.columns:
        timeline = out["Timeline_Flag"].fillna("").astype(str)

        add_points(
            timeline.eq("Sanction date unavailable"),
            2,
            "Sanction date is unavailable, limiting lifecycle verification",
            "Timeline",
        )
        add_points(
            timeline.eq("Date sequence needs review"),
            5,
            "Project dates have a sequence that needs review",
            "Timeline",
        )

    # ------------------------------------------------------------
    # 6. Data quality
    # ------------------------------------------------------------
    if "Recommendation Duplicate Count" in out.columns:
        dup = pd.to_numeric(
            out["Recommendation Duplicate Count"], errors="coerce"
        ).fillna(1)
        add_points(
            dup.gt(1),
            2,
            "Multiple recommendation records exist for this Work ID",
            "Data quality",
        )

    add_points(
        out["peer_count"].le(3),
        2,
        "Very small contextual comparison group",
        "Context",
    )

    # Optional V3 temporal concentration field if present.
    if "Temporal_Concentration_Count" in out.columns:
        concentration = pd.to_numeric(
            out["Temporal_Concentration_Count"], errors="coerce"
        )
        add_points(
            concentration.ge(1000),
            1,
            "High project concentration is present in the same period",
            "Context",
        )

    out["Risk_Score"] = out["Risk_Score"].clip(upper=100).astype(int)
    out["Risk_Level"] = np.select(
        [
            out["Risk_Score"].ge(HIGH_THRESHOLD),
            out["Risk_Score"].ge(MEDIUM_THRESHOLD),
        ],
        ["HIGH", "MEDIUM"],
        default="LOW",
    )

    # Human-readable compact peer context.
    out["Peer_Context"] = np.where(
        out["peer_median"].notna(),
        out["peer_median"].map(lambda x: f"₹{x:,.0f}")
        + " median across "
        + out["peer_count"].fillna(0).astype(int).astype(str)
        + " contextual peers",
        "No valid contextual peer benchmark",
    )

    return out


def score_project(df, work_id):
    """Fast single-project lookup after vectorized preparation."""
    matches = df.loc[df["Work ID"].astype(str).eq(str(work_id))]
    if matches.empty:
        raise KeyError(f"Work ID {work_id} was not found.")

    row = matches.iloc[0]

    reasons = [
        x.strip()
        for x in str(row.get("Risk_Reasons", "")).split(" | ")
        if x.strip()
    ]
    dimensions = list(dict.fromkeys(
        x.strip()
        for x in str(row.get("Risk_Dimensions", "")).split(" | ")
        if x.strip()
    ))

    return {
        "work_id": int(row["Work ID"]),
        "risk_score": int(row["Risk_Score"]),
        "risk_level": str(row["Risk_Level"]),
        "investigation_priority": str(row["Risk_Level"]),
        "reasons": reasons,
        "risk_dimensions": dimensions,
        "peer_median": (
            float(row["peer_median"]) if pd.notna(row["peer_median"]) else None
        ),
        "peer_group_size": (
            int(row["peer_count"]) if pd.notna(row["peer_count"]) else 0
        ),
        "amount_ratio_to_peer_median": (
            float(row["Amount_Ratio_to_Peer_Median"])
            if pd.notna(row["Amount_Ratio_to_Peer_Median"])
            else None
        ),
        "financial_reconciliation": str(
            row.get("Financial_Reconciliation_Flag", "Unavailable")
        ),
        "timeline_flag": str(row.get("Timeline_Flag", "Unavailable")),
        "has_pending_payment": bool(row.get("Has_Pending_Payment", False)),
        "expenditure_total": (
            float(row["Expenditure_Total"])
            if pd.notna(row.get("Expenditure_Total"))
            else None
        ),
        "final_amount": (
            float(row["Final Amount (₹)"])
            if pd.notna(row.get("Final Amount (₹)"))
            else None
        ),
    }


def score_all(path=DATA_PATH):
    """Return the complete scored V4 dataframe."""
    df = load_v4_data(path)
    return prepare_scored_dataframe(df)


if __name__ == "__main__":
    print("=" * 70)
    print("MPLADS AI INVESTIGATOR — V4 OPTIMIZED RISK INTELLIGENCE")
    print("=" * 70)

    df = load_v4_data()
    print(f"Loaded projects : {len(df):,}")

    result = prepare_scored_dataframe(df)

    print(f"Projects scored : {len(result):,}")
    print()
    print("Risk distribution:")
    print(result["Risk_Level"].value_counts().reindex(
        ["LOW", "MEDIUM", "HIGH"], fill_value=0
    ).to_string())

    print()
    print("Top 10 investigation-priority projects:")
    print(
        result.sort_values(
            ["Risk_Score", "Work ID"],
            ascending=[False, True]
        )[["Work ID", "Risk_Score", "Risk_Level", "Peer_Context"]]
        .head(10)
        .to_string(index=False)
    )

    print()
    for work_id in [193991, 193990]:
        if work_id in set(result["Work ID"].astype(int)):
            item = score_project(result, work_id)
            print(f"Work ID {work_id}:")
            print(f"  Score : {item['risk_score']}/100")
            print(f"  Level : {item['risk_level']}")
            print(f"  Reasons: {item['reasons']}")

    print()
    print("V4 scoring complete.")
    print("Scores are investigation-priority indicators, not fraud findings.")
    print("=" * 70)
