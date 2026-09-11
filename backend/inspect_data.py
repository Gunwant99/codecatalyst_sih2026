import pandas as pd
from pathlib import Path

# Path to the MPLADS CSV
csv_path = Path(__file__).parent.parent / "data" / "mplads_data.csv"

# Load data
df = pd.read_csv(csv_path)

print("\n========== DATASET OVERVIEW ==========")
print(f"Rows: {df.shape[0]:,}")
print(f"Columns: {df.shape[1]}")

print("\n========== COLUMN NAMES ==========")
for i, column in enumerate(df.columns, 1):
    print(f"{i}. {column}")

print("\n========== DATA TYPES ==========")
print(df.dtypes)

print("\n========== MISSING VALUES ==========")
missing = df.isnull().sum()
print(missing[missing > 0].sort_values(ascending=False))

print("\n========== FIRST 5 ROWS ==========")
print(df.head().to_string())

print("\n========== UNIQUE VALUES ==========")
for column in df.columns:
    print(f"{column}: {df[column].nunique(dropna=True):,} unique values")