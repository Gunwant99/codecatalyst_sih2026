import pandas as pd
from pathlib import Path

csv_path = Path(__file__).parent.parent / "data" / "mplads_data.csv"

df = pd.read_csv(csv_path)

print("\n========================================")
print(" MPLADS CONTEXT PROFILE")
print("========================================")

# ----------------------------------------
# 1. Projects by House
# ----------------------------------------

print("\n1. PROJECTS BY HOUSE")
print("----------------------------------------")

print(df["House"].value_counts())

# ----------------------------------------
# 2. State + House
# ----------------------------------------

print("\n2. PROJECTS BY STATE + HOUSE")
print("----------------------------------------")

state_house = (
    df.groupby(["State", "House"])
      .size()
      .sort_values(ascending=False)
)

print(state_house.head(20))

# ----------------------------------------
# 3. House + Category
# ----------------------------------------

print("\n3. PROJECTS BY HOUSE + CATEGORY")
print("----------------------------------------")

house_category = (
    df.groupby(["House", "Category"], dropna=False)
      .size()
      .sort_values(ascending=False)
)

print(house_category)

# ----------------------------------------
# 4. State + Category
# ----------------------------------------

print("\n4. PROJECTS BY STATE + CATEGORY")
print("----------------------------------------")

state_category = (
    df.groupby(["State", "Category"], dropna=False)
      .size()
      .sort_values(ascending=False)
)

print(state_category.head(30))

# ----------------------------------------
# 5. Amount by House
# ----------------------------------------

print("\n5. AMOUNT STATISTICS BY HOUSE")
print("----------------------------------------")

house_amount = (
    df.groupby("House")["Final Amount (₹)"]
      .agg(["count", "median", "mean", "max"])
)

print(house_amount)

# ----------------------------------------
# 6. Amount by Category
# ----------------------------------------

print("\n6. AMOUNT STATISTICS BY CATEGORY")
print("----------------------------------------")

category_amount = (
    df.groupby("Category", dropna=False)["Final Amount (₹)"]
      .agg(["count", "median", "mean", "max"])
)

print(category_amount)

print("\n========================================")
print(" CONTEXT PROFILE COMPLETE")
print("========================================")