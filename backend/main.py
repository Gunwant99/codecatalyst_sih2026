from agent import investigate_with_agent
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
import pandas as pd
import ast
from pathlib import Path

from similarity_engine import find_similar_projects


app = FastAPI(
    title="MPLADS AI Risk Investigator",
    description="AI-powered risk analysis and investigation assistant for MPLADS",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# LOAD DATA
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "risk_scored_projects.csv"

df = pd.read_csv(DATA_PATH)


# =========================================================
# HELPERS
# =========================================================

def parse_bool(value):
    """Safely convert CSV boolean-like values to a real bool."""
    if pd.isna(value):
        return False

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    return str(value).strip().lower() in {
        "true", "1", "yes", "y", "available"
    }


def parse_risk_reasons(value):
    """Convert stored risk-reason strings into a Python list."""
    if pd.isna(value):
        return []

    try:
        reasons = ast.literal_eval(str(value))

        if isinstance(reasons, list):
            return [str(reason) for reason in reasons]

        return [str(reasons)]

    except Exception:
        return [str(value)]


def clean_value(value):
    """Make pandas values JSON-safe."""
    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


def serialize_project(row):
    """Return a clean project dictionary for the frontend."""
    result = {}

    for key, value in row.to_dict().items():
        result[key] = clean_value(value)

    return result


# =========================================================
# BASIC ENDPOINTS
# =========================================================

@app.get("/")
def root():
    return {
        "message": "MPLADS AI Risk Investigator API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "projects_loaded": len(df)
    }


# =========================================================
# DASHBOARD
# =========================================================

@app.get("/dashboard")
def dashboard():
    """
    National dashboard statistics.

    All counts and totals are calculated deterministically from
    the risk-scored dataset. No AI is involved in these figures.
    """

    total_projects = len(df)

    risk_counts = (
        df["risk_level"]
        .fillna("LOW")
        .astype(str)
        .str.upper()
        .value_counts()
    )

    low_count = int(risk_counts.get("LOW", 0))
    medium_count = int(risk_counts.get("MEDIUM", 0))
    high_count = int(risk_counts.get("HIGH", 0))

    total_amount = pd.to_numeric(
        df["Final Amount (₹)"],
        errors="coerce"
    ).fillna(0).sum()

    projects_with_images = sum(
        parse_bool(value)
        for value in df["Has Images"]
    )

    projects_without_images = total_projects - projects_with_images

    # Top investigation queue.
    # Sort by risk score first, then amount.
    queue = (
        df.sort_values(
            ["risk_score", "Final Amount (₹)"],
            ascending=[False, False]
        )
        .head(10)
    )

    investigation_queue = []

    for _, row in queue.iterrows():
        investigation_queue.append({
            "work_id": clean_value(row.get("Work ID")),
            "description": clean_value(row.get("Work Description")),
            "state": clean_value(row.get("State")),
            "constituency": clean_value(row.get("Constituency")),
            "house": clean_value(row.get("House")),
            "category": clean_value(row.get("Category")),
            "amount": clean_value(row.get("Final Amount (₹)")),
            "risk_score": float(row.get("risk_score", 0)),
            "risk_level": str(
                row.get("risk_level", "LOW")
            ).upper(),
            "risk_reasons": parse_risk_reasons(
                row.get("risk_reasons", "[]")
            )
        })

    # State-level project counts for the dashboard.
    state_counts = (
        df["State"]
        .fillna("Unknown")
        .astype(str)
        .value_counts()
        .head(10)
    )

    state_distribution = [
        {
            "state": str(state),
            "projects": int(count)
        }
        for state, count in state_counts.items()
    ]

    return {
        "summary": {
            "total_projects": total_projects,
            "total_amount": float(total_amount),
            "low_risk": low_count,
            "medium_risk": medium_count,
            "high_risk": high_count,
            "projects_with_images": projects_with_images,
            "projects_without_images": projects_without_images
        },
        "risk_distribution": [
            {
                "level": "LOW",
                "count": low_count
            },
            {
                "level": "MEDIUM",
                "count": medium_count
            },
            {
                "level": "HIGH",
                "count": high_count
            }
        ],
        "state_distribution": state_distribution,
        "investigation_queue": investigation_queue
    }


# =========================================================
# PROJECT ENDPOINTS
# =========================================================

@app.get("/projects")
def get_projects(limit: int = 20):
    limit = max(1, min(limit, 100))

    projects = (
        df.sort_values(
            ["risk_score", "Final Amount (₹)"],
            ascending=[False, False]
        )
        .head(limit)
    )

    return {
        "total_projects": len(df),
        "returned_projects": len(projects),
        "projects": [
            serialize_project(row)
            for _, row in projects.iterrows()
        ]
    }


@app.get("/projects/{work_id}")
def get_project(work_id: int):

    project = df[df["Work ID"] == work_id]

    if project.empty:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    return {
        "project": serialize_project(project.iloc[0])
    }


# =========================================================
# SIMILAR PROJECTS
# =========================================================

@app.get("/projects/{work_id}/similar")
def get_similar_projects(
    work_id: int,
    limit: int = 5
):

    project = df[df["Work ID"] == work_id]

    if project.empty:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    limit = max(1, min(limit, 20))

    results = find_similar_projects(
        work_id,
        top_n=limit
    )

    return {
        "work_id": work_id,
        "similar_projects": results
    }


# =========================================================
# INVESTIGATION
# =========================================================

@app.get("/investigate/{work_id}")
def investigate_project(
    work_id: int,
    similar_limit: int = 5
):

    project = df[df["Work ID"] == work_id]

    if project.empty:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    project_data = project.iloc[0].to_dict()

    # -----------------------------
    # Risk information
    # -----------------------------

    risk_score = float(
        project_data.get("risk_score", 0)
    )

    risk_level = str(
        project_data.get(
            "risk_level",
            "LOW"
        )
    ).upper()

    risk_reasons = parse_risk_reasons(
        project_data.get("risk_reasons", "[]")
    )

    # -----------------------------
    # Evidence status
    # -----------------------------

    has_images = parse_bool(
        project_data.get("Has Images", False)
    )

    if has_images:
        evidence_status = "Image evidence available"
    else:
        evidence_status = "No image evidence available"

    # -----------------------------
    # Similar projects
    # -----------------------------

    similar_limit = max(1, min(similar_limit, 20))

    similar_projects = find_similar_projects(
        work_id,
        top_n=similar_limit
    )

    # -----------------------------
    # Recommended verification
    # -----------------------------

    recommended_actions = []

    if risk_score > 0:
        recommended_actions.append(
            "Review the project amount against comparable projects."
        )

    if similar_projects:
        recommended_actions.append(
            "Compare the project scope with similar projects."
        )

    if not has_images:
        recommended_actions.append(
            "Verify supporting evidence because no image evidence is available."
        )

    if not recommended_actions:
        recommended_actions.append(
            "No major automated risk indicators detected; routine verification may be sufficient."
        )

    # -----------------------------
    # Priority
    # -----------------------------

    if risk_level == "HIGH":
        priority = "High investigation priority"
    elif risk_level == "MEDIUM":
        priority = "Medium investigation priority"
    else:
        priority = "Low investigation priority"

    # -----------------------------
    # Response
    # -----------------------------

    return {
        "investigation": {
            "work_id": work_id,

            "priority": priority,

            "risk": {
                "score": risk_score,
                "level": risk_level,
                "reasons": risk_reasons
            },

            "project": {
                "description": clean_value(
                    project_data.get("Work Description")
                ),
                "category": clean_value(
                    project_data.get("Category")
                ),
                "mp_name": clean_value(
                    project_data.get("MP Name")
                ),
                "constituency": clean_value(
                    project_data.get("Constituency")
                ),
                "state": clean_value(
                    project_data.get("State")
                ),
                "house": clean_value(
                    project_data.get("House")
                ),
                "amount": clean_value(
                    project_data.get("Final Amount (₹)")
                )
            },

            "evidence": {
                "has_images": has_images,
                "status": evidence_status
            },

            "similar_projects": similar_projects,

            "recommended_verification": recommended_actions
        }
    }


# =========================================================
# AI INVESTIGATION AGENT
# =========================================================

@app.get("/agent/investigate")
def agent_investigate(query: str):
    response = investigate_with_agent(query)
    return {
        "query": query,
        "response": response
    }
