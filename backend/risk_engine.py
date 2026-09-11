import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# 1. LOAD DATA
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "mplads_data.csv"

df = pd.read_csv(CSV_PATH)


# ============================================================
# 2. CLEAN DATA
# ============================================================

df["Final Amount (₹)"] = pd.to_numeric(
    df["Final Amount (₹)"],
    errors="coerce"
).fillna(0)

df["Completed Date"] = pd.to_datetime(
    df["Completed Date"],
    errors="coerce"
)

for column in [
    "Work Description",
    "Category",
    "State",
    "House",
    "Constituency"
]:
    df[column] = df[column].fillna("Unknown").astype(str)


# ============================================================
# 3. COST ANOMALY
# ============================================================

# Compare against projects with the same:
# State + House + Category

group_cols = [
    "State",
    "House",
    "Category"
]

group_median = (
    df.groupby(group_cols)["Final Amount (₹)"]
      .transform("median")
)

group_median = group_median.replace(0, np.nan)

df["amount_ratio"] = (
    df["Final Amount (₹)"] / group_median
)

df["amount_ratio"] = (
    df["amount_ratio"]
    .replace([np.inf, -np.inf], np.nan)
    .fillna(1)
)


# Cost anomaly score
#
# 1.5x median  -> 5 points
# 2x median    -> 10 points
# 3x median    -> 20 points
# 5x median    -> 30 points

df["cost_risk"] = np.select(
    [
        df["amount_ratio"] >= 5,
        df["amount_ratio"] >= 3,
        df["amount_ratio"] >= 2,
        df["amount_ratio"] >= 1.5
    ],
    [
        30,
        20,
        10,
        5
    ],
    default=0
)


# ============================================================
# 4. HIGH VALUE PROJECT
# ============================================================

# High value alone is NOT treated as suspicious.
# It only adds a small review signal.

df["high_value_signal"] = np.where(
    df["Final Amount (₹)"] >= 3000000,
    3,
    0
)


# ============================================================
# 5. EVIDENCE AVAILABILITY
# ============================================================

# Missing images are NOT evidence of fraud.
# Maximum contribution = 2 points.

df["evidence_signal"] = np.where(
    df["Has Images"] == False,
    2,
    0
)


# ============================================================
# 6. DESCRIPTION QUALITY
# ============================================================

def description_quality(text):

    words = str(text).strip().split()

    if len(words) == 0:
        return 0

    if len(words) <= 2:
        return 0

    if len(words) <= 5:
        return 1

    if len(words) <= 8:
        return 2

    return 3


df["description_quality"] = (
    df["Work Description"]
    .apply(description_quality)
)

df["description_signal"] = (
    3 - df["description_quality"]
)


# ============================================================
# 7. CONSTITUENCY CONTEXT
# ============================================================

df["constituency_project_count"] = (
    df.groupby(
        ["State", "House", "Constituency"]
    )["Work ID"]
    .transform("count")
)


# Very small groups provide limited statistical context.
# Maximum contribution = 2.

df["constituency_signal"] = np.where(
    df["constituency_project_count"] <= 3,
    2,
    0
)


# ============================================================
# 8. TEMPORAL CONTEXT
# ============================================================

df["completion_year"] = (
    df["Completed Date"].dt.year
)

df["year_project_count"] = (
    df.groupby(
        ["State", "House", "completion_year"]
    )["Work ID"]
    .transform("count")
    .fillna(0)
)

# Temporal concentration is only a weak signal.

df["temporal_signal"] = np.where(
    df["year_project_count"] >= 1000,
    1,
    0
)


# ============================================================
# 9. BASE RISK SCORE
# ============================================================

df["risk_score"] = (
    df["cost_risk"]
    + df["high_value_signal"]
    + df["evidence_signal"]
    + df["description_signal"]
    + df["constituency_signal"]
    + df["temporal_signal"]
)


df["risk_score"] = np.clip(
    df["risk_score"],
    0,
    100
)


# ============================================================
# 10. RISK LEVEL
# ============================================================

def get_risk_level(score):

    if score >= 40:
        return "HIGH"

    elif score >= 20:
        return "MEDIUM"

    else:
        return "LOW"


df["risk_level"] = (
    df["risk_score"]
    .apply(get_risk_level)
)


# ============================================================
# 11. GENERATE EXPLANATIONS
# ============================================================

def generate_reasons(row):

    reasons = []

    if row["cost_risk"] >= 20:
        reasons.append(
            "Strong cost anomaly compared with contextual projects"
        )

    elif row["cost_risk"] >= 10:
        reasons.append(
            "Moderate cost anomaly compared with contextual projects"
        )

    elif row["cost_risk"] >= 5:
        reasons.append(
            "Amount is above the contextual project baseline"
        )

    if row["high_value_signal"] > 0:
        reasons.append(
            "High-value project"
        )

    if row["evidence_signal"] > 0:
        reasons.append(
            "Image evidence is unavailable"
        )

    if row["description_signal"] >= 2:
        reasons.append(
            "Project description contains limited information"
        )

    if row["constituency_signal"] > 0:
        reasons.append(
            "Very small constituency comparison group"
        )

    if row["temporal_signal"] > 0:
        reasons.append(
            "High project concentration in the same period"
        )

    if not reasons:
        reasons.append(
            "No major automated risk indicators detected"
        )

    return reasons


df["risk_reasons"] = (
    df.apply(generate_reasons, axis=1)
)


# ============================================================
# 12. SUMMARY
# ============================================================

print("\n========================================")
print(" MPLADS AI RISK ENGINE V3")
print("========================================")

print(
    f"\nTotal projects: {len(df):,}"
)

print("\nRisk distribution:")

print(
    df["risk_level"]
    .value_counts()
)


print("\nRisk score statistics:")

print(
    df["risk_score"]
    .describe()
)


# ============================================================
# 13. TOP INVESTIGATION PRIORITY
# ============================================================

columns_to_show = [
    "Work ID",
    "Work Description",
    "Category",
    "MP Name",
    "Constituency",
    "State",
    "House",
    "Final Amount (₹)",
    "Has Images",
    "risk_score",
    "risk_level",
    "risk_reasons"
]

print(
    "\nTop 20 investigation-priority projects:"
)

top_projects = (
    df.sort_values(
        "risk_score",
        ascending=False
    )[columns_to_show]
    .head(20)
)

print(
    top_projects.to_string(
        index=False
    )
)


# ============================================================
# 14. SAVE RESULTS
# ============================================================

OUTPUT_PATH = (
    BASE_DIR /
    "data" /
    "risk_scored_projects.csv"
)

df[columns_to_show].to_csv(
    OUTPUT_PATH,
    index=False
)

print("\n========================================")
print("Risk-scored dataset saved to:")
print(OUTPUT_PATH)
print("========================================")