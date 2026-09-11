import pandas as pd
from pathlib import Path

from similarity_engine import find_similar_projects


# =========================================================
# DATASET
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = BASE_DIR / "data" / "risk_scored_projects.csv"

df = pd.read_csv(DATA_PATH)


# =========================================================
# TOOL 1 — GET PROJECT DETAILS
# =========================================================

def get_project_details(work_id: int):

    project = df[df["Work ID"] == work_id]

    if project.empty:
        return {
            "error": f"Project {work_id} not found"
        }

    row = project.iloc[0]

    return {
        "work_id": int(row["Work ID"]),
        "description": row.get("Work Description"),
        "category": row.get("Category"),
        "mp_name": row.get("MP Name"),
        "constituency": row.get("Constituency"),
        "state": row.get("State"),
        "house": row.get("House"),
        "amount": float(row["Final Amount (₹)"]),
        "has_images": bool(row["Has Images"]),
        "risk_score": float(row["risk_score"]),
        "risk_level": row["risk_level"],
        "risk_reasons": row["risk_reasons"]
    }


# =========================================================
# TOOL 2 — SEARCH PROJECTS
# =========================================================

def search_projects(
    state=None,
    risk_level=None,
    min_amount=None,
    max_amount=None,
    has_images=None,
    limit=10
):

    results = df.copy()


    # -----------------------------------------------------
    # STATE FILTER
    # -----------------------------------------------------

    if state:

        results = results[
            results["State"]
            .astype(str)
            .str.lower()
            == state.lower()
        ]


    # -----------------------------------------------------
    # RISK LEVEL FILTER
    # -----------------------------------------------------

    if risk_level:

        results = results[
            results["risk_level"]
            .astype(str)
            .str.upper()
            == risk_level.upper()
        ]


    # -----------------------------------------------------
    # MINIMUM AMOUNT
    # -----------------------------------------------------

    if min_amount is not None:

        results = results[
            results["Final Amount (₹)"]
            >= float(min_amount)
        ]


    # -----------------------------------------------------
    # MAXIMUM AMOUNT
    # -----------------------------------------------------

    if max_amount is not None:

        results = results[
            results["Final Amount (₹)"]
            <= float(max_amount)
        ]


    # -----------------------------------------------------
    # IMAGE FILTER
    # -----------------------------------------------------

    if has_images is not None:

        results = results[
            results["Has Images"]
            == bool(has_images)
        ]


    # -----------------------------------------------------
    # SORT BY RISK
    # -----------------------------------------------------

    results = (
        results
        .sort_values("risk_score", ascending=False)
        .head(limit)
    )


    projects = []


    # -----------------------------------------------------
    # BUILD RESPONSE
    # -----------------------------------------------------

    for _, row in results.iterrows():

        projects.append({

            "work_id": int(row["Work ID"]),

            "description": row.get(
                "Work Description"
            ),

            "category": row.get(
                "Category"
            ),

            "mp_name": row.get(
                "MP Name"
            ),

            "constituency": row.get(
                "Constituency"
            ),

            "state": row.get(
                "State"
            ),

            "house": row.get(
                "House"
            ),

            "amount": float(
                row["Final Amount (₹)"]
            ),

            "has_images": bool(
                row["Has Images"]
            ),

            "risk_score": float(
                row["risk_score"]
            ),

            "risk_level": row[
                "risk_level"
            ],

            "risk_reasons": row[
                "risk_reasons"
            ]
        })


    return {

        "count": len(projects),

        "projects": projects
    }


# =========================================================
# TOOL 3 — COMPARE PROJECT WITH SIMILAR PROJECTS
# =========================================================

def compare_projects(work_id: int, limit: int = 5):

    # -----------------------------------------------------
    # GET TARGET PROJECT
    # -----------------------------------------------------

    target = df[df["Work ID"] == work_id]

    if target.empty:
        return {
            "error": f"Project {work_id} not found"
        }

    target_row = target.iloc[0]

    target_amount = float(
        target_row["Final Amount (₹)"]
    )

    # -----------------------------------------------------
    # FIND SIMILAR PROJECTS
    # -----------------------------------------------------

    similar_projects = find_similar_projects(
        work_id,
        limit
    )

    if not similar_projects:
        return {
            "target_project": {
                "work_id": work_id,
                "description": target_row["Work Description"],
                "category": target_row["Category"],
                "state": target_row["State"],
                "house": target_row["House"],
                "constituency": target_row["Constituency"],
                "amount": target_amount,
                "risk_score": float(target_row["risk_score"]),
                "risk_level": target_row["risk_level"]
            },
            "comparison_count": 0,
            "comparisons": []
        }

    comparisons = []

    # -----------------------------------------------------
    # BUILD COMPARISON
    # -----------------------------------------------------

    for project in similar_projects:

        similar_id = int(
            project["Work ID"]
        )

        comparison_amount = float(
            project["Amount"]
        )

        amount_difference = (
            target_amount - comparison_amount
        )

        if comparison_amount != 0:

            amount_difference_percent = (
                abs(amount_difference)
                / comparison_amount
            ) * 100

        else:

            amount_difference_percent = None

        comparisons.append({

            "work_id": similar_id,

            "description": project[
                "Description"
            ],

            "category": project[
                "Category"
            ],

            "state": project[
                "State"
            ],

            "house": project[
                "House"
            ],

            "constituency": project[
                "Constituency"
            ],

            "amount": comparison_amount,

            "target_amount": target_amount,

            "amount_difference": (
                amount_difference
            ),

            "amount_difference_percent": (
                round(
                    amount_difference_percent,
                    2
                )
                if amount_difference_percent
                is not None
                else None
            ),

            "similarity_score": float(
                project["Similarity Score"]
            ),

            "text_similarity": float(
                project["Text Similarity"]
            ),

            "same_state": bool(
                project["Same State"]
            ),

            "same_house": bool(
                project["Same House"]
            ),

            "same_category": bool(
                project["Same Category"]
            ),

            "same_constituency": bool(
                project["Same Constituency"]
            )
        })

    # -----------------------------------------------------
    # RETURN STRUCTURED EVIDENCE
    # -----------------------------------------------------

    return {

        "target_project": {

            "work_id": work_id,

            "description": target_row[
                "Work Description"
            ],

            "category": target_row[
                "Category"
            ],

            "state": target_row[
                "State"
            ],

            "house": target_row[
                "House"
            ],

            "constituency": target_row[
                "Constituency"
            ],

            "amount": target_amount,

            "risk_score": float(
                target_row["risk_score"]
            ),

            "risk_level": target_row[
                "risk_level"
            ]
        },

        "comparison_count": len(
            comparisons
        ),

        "comparisons": comparisons
    }