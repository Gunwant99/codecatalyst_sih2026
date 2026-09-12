
"""
MPLADS AI Investigator — V4 data layer
Builds a unified project investigation dataset from the new MPLADS exports.

Expected source files in ../data/:
- recommended works JSONL/CSV export
- completed works JSONL/CSV export
- expenditures JSONL/CSV export
- MP summary JSONL/CSV export

The script also works with the current 44,028-row mplads_data.csv as a fallback
for completed-work fields when the new completed export is not present.

IMPORTANT:
- It does not modify the existing risk engine or frontend.
- It preserves source-data gaps instead of inventing values.
- Duplicate recommended rows are collapsed to one Work ID and recorded in
  recommendation_duplicate_count.
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT = DATA_DIR / "investigation_projects_v4.csv"


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def load_any(path):
    """Load normal CSV or the portal's one-JSON-object-per-line CSV export."""
    with open(path, encoding="utf-8", errors="replace") as f:
        first = f.readline().strip()

    if first.startswith("{"):
        return load_jsonl(path)
    return pd.read_csv(path, low_memory=False)


def find_source(kind):
    patterns = {
        "recommended": ["*recommended*.csv"],
        "completed": ["*completed*.csv", "mplads_data.csv"],
        "expenditure": ["*expenditure*.csv"],
        "mp_summary": ["*mp_summary*.csv", "*summary*.csv"],
    }

    candidates = []
    for p in patterns[kind]:
        candidates.extend(DATA_DIR.glob(p))

    # Prefer the new portal JSONL-style exports by inspecting keys.
    for path in candidates:
        try:
            sample = load_any(path).head(1)
            cols = set(sample.columns)
            if kind == "recommended" and "workId" in cols and "sanctionedAmount" in cols:
                return path
            if kind == "completed" and "workId" in cols and "finalAmount" in cols:
                return path
            if kind == "expenditure" and "workId" in cols and "expenditureAmount" in cols:
                return path
            if kind == "mp_summary" and "mpName" in cols and "allocatedAmount" in cols:
                return path
        except Exception:
            pass

    # Fallback to legacy completed dataset.
    if kind == "completed":
        legacy = DATA_DIR / "mplads_data.csv"
        if legacy.exists():
            return legacy
        if kind == "mp_summary":
            fallback = DATA_DIR / "summaries.csv"
            if fallback.exists():
                return fallback

    return None


def date_value(series):
    return pd.to_datetime(
        series.map(lambda x: x.get("$date") if isinstance(x, dict) else x),
        errors="coerce",
        utc=True,
    )


def clean_text(s):
    return s.fillna("").astype(str).str.strip()


def main():
    rec_path = find_source("recommended")
    comp_path = find_source("completed")
    exp_path = find_source("expenditure")
    mp_path = find_source("mp_summary")

    missing = [
        name for name, path in {
            "recommended": rec_path,
            "completed": comp_path,
            "expenditure": exp_path,
        }.items() if path is None
    ]
    if missing:
        raise FileNotFoundError(
            "Missing required source dataset(s): " + ", ".join(missing)
        )

    rec = load_any(rec_path)
    comp = load_any(comp_path)
    exp = load_any(exp_path)
    mp = load_any(mp_path) if mp_path else pd.DataFrame()

    # -----------------------------
    # Normalize recommended works
    # -----------------------------
    rec = rec.rename(columns={
        "workId": "Work ID",
        "workDescription": "Work Description",
        "workCategory": "Category",
        "mpName": "MP Name",
        "constituency": "Constituency",
        "state": "State",
        "house": "House",
        "recommendedAmount": "Recommended Amount (₹)",
        "sanctionedAmount": "Sanctioned Amount (₹)",
        "recommendationDate": "Recommendation Date",
        "sanctionDate": "Sanction Date",
        "hasImage": "Has Images",
        "workStage": "Work Stage",
        "isCompleted": "Is Completed",
        "ida": "IDA",
    })

    for c in ["Recommended Amount (₹)", "Sanctioned Amount (₹)"]:
        rec[c] = pd.to_numeric(rec.get(c), errors="coerce")

    for c in ["Recommendation Date", "Sanction Date"]:
        if c in rec:
            rec[c] = date_value(rec[c])

    rec["Work ID"] = pd.to_numeric(rec["Work ID"], errors="coerce").astype("Int64")
    rec = rec.dropna(subset=["Work ID"]).copy()
    rec["Work ID"] = rec["Work ID"].astype(int)

    # The source contains duplicate Work IDs. Keep the latest source record
    # while retaining the duplicate count as a data-quality indicator.
    dup_counts = rec.groupby("Work ID").size().rename("Recommendation Duplicate Count")
    rec = (
        rec.sort_values(["Work ID", "Recommendation Date", "Sanction Date"])
           .drop_duplicates("Work ID", keep="last")
           .merge(dup_counts, on="Work ID", how="left")
    )

    # -----------------------------
    # Normalize completed works
    # -----------------------------
    comp = comp.rename(columns={
        "workId": "Work ID",
        "workDescription": "Work Description",
        "workCategory": "Category",
        "mpName": "MP Name",
        "constituency": "Constituency",
        "state": "State",
        "house": "House",
        "finalAmount": "Final Amount (₹)",
        "completedDate": "Completed Date",
        "hasImage": "Has Images",
        "averageRating": "Average Rating",
        "ida": "IDA",
    })

    comp["Work ID"] = pd.to_numeric(comp["Work ID"], errors="coerce").astype("Int64")
    comp = comp.dropna(subset=["Work ID"]).copy()
    comp["Work ID"] = comp["Work ID"].astype(int)
    comp["Final Amount (₹)"] = pd.to_numeric(comp["Final Amount (₹)"], errors="coerce")
    comp["Completed Date"] = date_value(comp["Completed Date"])

    # -----------------------------
    # Normalize expenditure
    # -----------------------------
    exp = exp.rename(columns={
        "workId": "Work ID",
        "mpName": "MP Name",
        "constituency": "Constituency",
        "state": "State",
        "house": "House",
        "vendor": "Vendor",
        "expenditureAmount": "Expenditure Amount (₹)",
        "expenditureDate": "Expenditure Date",
        "paymentStatus": "Payment Status",
    })

    exp["Work ID"] = pd.to_numeric(exp["Work ID"], errors="coerce").astype("Int64")
    exp = exp.dropna(subset=["Work ID"]).copy()
    exp["Work ID"] = exp["Work ID"].astype(int)
    exp["Expenditure Amount (₹)"] = pd.to_numeric(
        exp["Expenditure Amount (₹)"], errors="coerce"
    )
    exp["Expenditure Date"] = date_value(exp["Expenditure Date"])

    # Aggregate transaction-level data to project level.
    exp["is_pending"] = exp["Payment Status"].eq("Payment In-Progress")
    exp["is_success"] = exp["Payment Status"].eq("Payment Success")

    exp_agg = exp.groupby("Work ID").agg(
        Expenditure_Total=("Expenditure Amount (₹)", "sum"),
        Transaction_Count=("Work ID", "size"),
        Vendor_Count=("Vendor", "nunique"),
        Pending_Payment_Count=("is_pending", "sum"),
        Successful_Payment_Count=("is_success", "sum"),
        Last_Expenditure_Date=("Expenditure Date", "max"),
    ).reset_index()

    # -----------------------------
    # Build one project-level record
    # -----------------------------
    project = comp.merge(
        rec[
            [
                "Work ID",
                "Recommended Amount (₹)",
                "Sanctioned Amount (₹)",
                "Recommendation Date",
                "Sanction Date",
                "Work Stage",
                "Is Completed",
                "Recommendation Duplicate Count",
            ]
        ],
        on="Work ID",
        how="left",
        suffixes=("", "_rec"),
    )

    project = project.merge(exp_agg, on="Work ID", how="left")

    # -----------------------------
    # Derived, explainable indicators
    # -----------------------------
    project["Recommendation_to_Sanction_Days"] = (
        project["Sanction Date"] - project["Recommendation Date"]
    ).dt.days

    project["Sanction_to_Completion_Days"] = (
        project["Completed Date"] - project["Sanction Date"]
    ).dt.days

    project["Expenditure_minus_Final"] = (
        project["Expenditure_Total"] - project["Final Amount (₹)"]
    )

    project["Expenditure_to_Final_Ratio"] = (
        project["Expenditure_Total"] / project["Final Amount (₹)"].replace(0, np.nan)
    )

    project["Sanction_minus_Recommended"] = (
        project["Sanctioned Amount (₹)"] - project["Recommended Amount (₹)"]
    )

    project["Has_Expenditure_Record"] = project["Expenditure_Total"].notna()
    project["Has_Sanction_Record"] = project["Sanctioned Amount (₹)"].notna()
    project["Has_Pending_Payment"] = project["Pending_Payment_Count"].fillna(0).gt(0)

    # Conservative review flags. These are NOT fraud findings.
    project["Financial_Reconciliation_Flag"] = np.select(
        [
            ~project["Has_Expenditure_Record"],
            project["Expenditure_minus_Final"].abs().gt(1),
        ],
        [
            "Expenditure record unavailable",
            "Expenditure differs from final amount",
        ],
        default="Reconciled",
    )

    project["Timeline_Flag"] = np.select(
        [
            project["Sanction Date"].isna(),
            project["Recommendation_to_Sanction_Days"].lt(0),
            project["Sanction_to_Completion_Days"].lt(0),
        ],
        [
            "Sanction date unavailable",
            "Date sequence needs review",
            "Date sequence needs review",
        ],
        default="Chronology consistent",
    )

    project["Data_Quality_Flag"] = np.select(
        [
            project["Recommendation Duplicate Count"].fillna(1).gt(1),
            ~project["Has_Expenditure_Record"],
        ],
        [
            "Duplicate recommendation records present",
            "Expenditure record unavailable",
        ],
        default="No major project-level data-quality flag",
    )

    # -----------------------------
    # MP context
    # -----------------------------
    if not mp.empty:
        mp = mp.rename(columns={
            "mpName": "MP Name",
            "constituency": "Constituency",
            "state": "State",
            "house": "House",
            "allocatedAmount": "MP Allocated Amount (₹)",
            "totalExpenditure": "MP Total Expenditure (₹)",
            "utilizationPercentage": "MP Utilization %",
            "completionRate": "MP Completion Rate %",
            "completedWorksCount": "MP Completed Works",
            "recommendedWorksCount": "MP Recommended Works",
            "pendingPayments": "MP Pending Payments",
            "unpaidBalance": "MP Unpaid Vendor Balance (₹)",
            "transactionCount": "MP Transaction Count",
        })

        keep = [
            "MP Name", "Constituency", "State", "House",
            "MP Allocated Amount (₹)", "MP Total Expenditure (₹)",
            "MP Utilization %", "MP Completion Rate %",
            "MP Completed Works", "MP Recommended Works",
            "MP Pending Payments", "MP Unpaid Vendor Balance (₹)",
            "MP Transaction Count",
        ]
        keep = [c for c in keep if c in mp.columns]

        project = project.merge(
            mp[keep].drop_duplicates(
                ["MP Name", "Constituency", "State", "House"]
            ),
            on=["MP Name", "Constituency", "State", "House"],
            how="left",
        )

    # Make dates readable in CSV.
    for c in project.columns:
        if pd.api.types.is_datetime64_any_dtype(project[c]):
            project[c] = project[c].dt.strftime("%Y-%m-%d")

    project.to_csv(OUTPUT, index=False)

    print("=" * 70)
    print("MPLADS AI INVESTIGATOR — V4 DATA LAYER")
    print("=" * 70)
    print(f"Recommended source : {rec_path.name}")
    print(f"Completed source   : {comp_path.name}")
    print(f"Expenditure source : {exp_path.name}")
    print(f"MP summary source  : {mp_path.name if mp_path else 'not found'}")
    print()
    print(f"Unified projects   : {len(project):,}")
    print(f"Unique Work IDs    : {project['Work ID'].nunique():,}")
    print(f"With expenditure   : {project['Has_Expenditure_Record'].sum():,}")
    print(f"With sanction data : {project['Has_Sanction_Record'].sum():,}")
    print(f"Pending payments   : {project['Has_Pending_Payment'].sum():,}")
    print(f"Duplicate rec IDs  : {(project['Recommendation Duplicate Count'] > 1).sum():,}")
    print()
    print("Output:")
    print(OUTPUT)
    print()
    print("This is a screening/investigation dataset, not a fraud-label dataset.")
    print("=" * 70)


if __name__ == "__main__":
    main()
