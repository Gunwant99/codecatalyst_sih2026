import pandas as pd
from pathlib import Path

# Load dataset
csv_path = Path(__file__).parent.parent / "data" / "mplads_data.csv"
df = pd.read_csv(csv_path)

print("\n========================================")
print(" MPLADS DATA PROFILE")
print("========================================")

# ----------------------------------------
# 1. Basic information
# ----------------------------------------

print("\n1. BASIC DATA")
print("----------------------------------------")
print("Total projects:", len(df))
print("Total states:", df["State"].nunique())
print("Total categories:", df["Category"].nunique())
print("Total constituencies:", df["Constituency"].nunique())

# ----------------------------------------
# 2. Categories
# ----------------------------------------

print("\n2. PROJECTS BY CATEGORY")
print("----------------------------------------")
print(df["Category"].value_counts(dropna=False))

# ----------------------------------------
# 3. States
# ----------------------------------------

print("\n3. TOP STATES BY PROJECT COUNT")
print("----------------------------------------")
print(df["State"].value_counts().head(15))

# ----------------------------------------
# 4. Constituencies
# ----------------------------------------

print("\n4. TOP CONSTITUENCIES")
print("----------------------------------------")
print(df["Constituency"].value_counts().head(15))

# ----------------------------------------
# 5. Project amount statistics
# ----------------------------------------

print("\n5. PROJECT AMOUNT STATISTICS")
print("----------------------------------------")

print("Minimum amount:",
      df["Final Amount (₹)"].min())

print("Maximum amount:",
      df["Final Amount (₹)"].max())

print("Average amount:",
      round(df["Final Amount (₹)"].mean(), 2))

print("Median amount:",
      df["Final Amount (₹)"].median())

print("\nAmount percentiles:")
print(
    df["Final Amount (₹)"]
    .quantile([0.50, 0.75, 0.90, 0.95, 0.99])
)

# ----------------------------------------
# 6. Projects without images
# ----------------------------------------

print("\n6. IMAGE EVIDENCE")
print("----------------------------------------")
print(df["Has Images"].value_counts(dropna=False))

# ----------------------------------------
# 7. Data quality checks
# ----------------------------------------

print("\n7. DATA QUALITY")
print("----------------------------------------")

print("Missing descriptions:",
      df["Work Description"].isna().sum())

print("Missing categories:",
      df["Category"].isna().sum())

print("Missing constituency:",
      df["Constituency"].isna().sum())

# ----------------------------------------
# 8. Suspicious constituency values
# ----------------------------------------

print("\n8. POSSIBLE CONSTITUENCY DATA ISSUES")
print("----------------------------------------")

print(
    df["Constituency"]
    .value_counts()
    .loc[lambda x: x.index.astype(str).str.contains(
        "Rajya Sabha|Sitting|Unknown|N/A",
        case=False,
        na=False
    )]
)

print("\n========================================")
print(" PROFILE COMPLETE")
print("========================================")