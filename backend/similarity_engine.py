import pandas as pd
from pathlib import Path
from rapidfuzz import fuzz


# ========================================
# LOAD DATA
# ========================================

csv_path = Path(__file__).parent.parent / "data" / "mplads_data.csv"
df = pd.read_csv(csv_path)


# ========================================
# CLEAN TEXT
# ========================================

def clean_text(text):
    if pd.isna(text):
        return ""

    return str(text).lower().strip()


# ========================================
# DESCRIPTION QUALITY
# ========================================

def description_quality(text):
    """
    Checks whether a project description contains
    enough information to be useful for similarity analysis.
    """

    text = clean_text(text)

    if not text:
        return 0

    words = text.split()

    # Very short descriptions are unreliable
    if len(words) <= 2:
        return 0.25

    if len(words) <= 5:
        return 0.50

    if len(words) <= 8:
        return 0.75

    return 1.0


# ========================================
# FIND SIMILAR PROJECTS
# ========================================

def find_similar_projects(work_id, top_n=5):

    target_rows = df[df["Work ID"] == work_id]

    if target_rows.empty:
        return []

    target = target_rows.iloc[0]

    target_description = clean_text(target["Work Description"])

    target_state = target["State"]
    target_house = target["House"]
    target_category = target["Category"]
    target_constituency = target["Constituency"]

    target_amount = target["Final Amount (₹)"]

    results = []

    # ====================================
    # FIRST FILTER
    # Compare only projects from same
    # house + state + category
    # ====================================

    candidates = df[
        (df["House"] == target_house) &
        (df["State"] == target_state) &
        (df["Category"] == target_category)
    ]

    for _, row in candidates.iterrows():

        if row["Work ID"] == work_id:
            continue

        description = clean_text(row["Work Description"])

        if not description or not target_description:
            continue

        # --------------------------------
        # Text similarity
        # --------------------------------

        text_similarity = fuzz.token_set_ratio(
            target_description,
            description
        )

        # --------------------------------
        # Description quality
        # --------------------------------

        target_quality = description_quality(
            target_description
        )

        candidate_quality = description_quality(
            description
        )

        quality_factor = min(
            target_quality,
            candidate_quality
        )

        # Reduce similarity when descriptions
        # are too short/generic
        adjusted_text_similarity = (
            text_similarity * quality_factor
        )

        # --------------------------------
        # Context signals
        # --------------------------------

        same_state = True
        same_house = True
        same_category = True

        same_constituency = (
            row["Constituency"] == target_constituency
        )

        # --------------------------------
        # Contextual score
        # --------------------------------

        score = adjusted_text_similarity * 0.60

        score += 10  # Same State
        score += 10  # Same House
        score += 10  # Same Category

        if same_constituency:
            score += 10

        # --------------------------------
        # Amount difference
        # --------------------------------

        row_amount = row["Final Amount (₹)"]

        if target_amount > 0:

            amount_difference_percent = (
                abs(row_amount - target_amount)
                / target_amount
            ) * 100

        else:
            amount_difference_percent = 0

        results.append({
            "Work ID": row["Work ID"],
            "Similarity Score": round(score, 2),
            "Text Similarity": round(text_similarity, 2),
            "Adjusted Text Similarity": round(
                adjusted_text_similarity, 2
            ),
            "Description Quality": round(
                candidate_quality, 2
            ),
            "Same State": same_state,
            "Same House": same_house,
            "Same Category": same_category,
            "Same Constituency": same_constituency,
            "Amount Difference %": round(
                amount_difference_percent, 2
            ),
            "Amount": row_amount,
            "Constituency": row["Constituency"],
            "State": row["State"],
            "House": row["House"],
            "Category": row["Category"],
            "Description": row["Work Description"]
        })

    # ====================================
    # SORT
    # ====================================

    results = sorted(
        results,
        key=lambda x: x["Similarity Score"],
        reverse=True
    )

    return results[:top_n]


# ========================================
# TEST
# ========================================

if __name__ == "__main__":

    target_work_id = 134703

    print("\n========================================")
    print(" MPLADS CONTEXTUAL SIMILARITY ENGINE")
    print("========================================")

    target = df[df["Work ID"] == target_work_id].iloc[0]

    print("\nTarget Work ID:", target_work_id)

    print("Description:")
    print(target["Work Description"])

    print("\nState:", target["State"])
    print("House:", target["House"])
    print("Category:", target["Category"])
    print("Constituency:", target["Constituency"])
    print("Amount: ₹{:,.2f}".format(
        target["Final Amount (₹)"]
    ))

    print("\nSimilar projects:")

    similar_projects = find_similar_projects(
        target_work_id,
        top_n=5
    )

    for i, project in enumerate(
        similar_projects,
        start=1
    ):

        print(f"\n{i}. Work ID: {project['Work ID']}")

        print(
            f"   Contextual Score: "
            f"{project['Similarity Score']}%"
        )

        print(
            f"   Text Similarity: "
            f"{project['Text Similarity']}%"
        )

        print(
            f"   Adjusted Text Similarity: "
            f"{project['Adjusted Text Similarity']}%"
        )

        print(
            f"   Description Quality: "
            f"{project['Description Quality']}"
        )

        print(
            f"   Same Constituency: "
            f"{project['Same Constituency']}"
        )

        print(
            f"   Amount Difference: "
            f"{project['Amount Difference %']}%"
        )

        print(
            f"   Amount: "
            f"₹{project['Amount']:,.2f}"
        )

        print(
            f"   Description: "
            f"{project['Description']}"
        )

    print("\n========================================")
    print(" SIMILARITY ANALYSIS COMPLETE")
    print("========================================")