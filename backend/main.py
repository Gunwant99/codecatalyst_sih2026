from agent import investigate_with_agent, get_agent_trace
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
import pandas as pd
import ast
from pathlib import Path

from similarity_engine import find_similar_projects
from risk_engine_v4_optimized import load_v4_data, prepare_scored_dataframe

app = FastAPI(
    title="MPLADS AI Risk Investigator",
    description="AI-powered risk analysis and investigation assistant for MPLADS",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent

# Keep the existing V3 dataset available for backward compatibility.
DATA_PATH = BASE_DIR / "data" / "risk_scored_projects.csv"
df = pd.read_csv(DATA_PATH)

# New V4 lifecycle intelligence dataset.
V4_DATA_PATH = BASE_DIR / "data" / "investigation_projects_v4.csv"
v4_df = prepare_scored_dataframe(load_v4_data(V4_DATA_PATH))


def parse_bool(value):
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
    if pd.isna(value):
        return []
    try:
        reasons = ast.literal_eval(str(value))
        if isinstance(reasons, list):
            return [str(reason) for reason in reasons]
        return [str(reasons)]
    except Exception:
        return [str(value)]


def split_reasons(value):
    if pd.isna(value):
        return []
    return [x.strip() for x in str(value).split(" | ") if x.strip()]


def clean_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def v4_project(work_id):
    project = v4_df[v4_df["Work ID"] == work_id]
    if project.empty:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.iloc[0]


def lifecycle_project_dict(row):
    result = {}
    for key, value in row.to_dict().items():
        result[key] = clean_value(value)
    return result


@app.get("/")
def root():
    return {
        "message": "MPLADS AI Risk Investigator API is running",
        "version": "2.0.0",
        "v4_projects_loaded": len(v4_df),
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "projects_loaded": len(df),
        "v4_projects_loaded": len(v4_df),
        "v4_status": "ready",
    }


# =========================================================
# DASHBOARD
# =========================================================

@app.get("/dashboard")
def dashboard():
    risk_counts = (
        df["risk_level"].fillna("LOW").astype(str).str.upper().value_counts()
    )

    total_projects = len(df)
    low_count = int(risk_counts.get("LOW", 0))
    medium_count = int(risk_counts.get("MEDIUM", 0))
    high_count = int(risk_counts.get("HIGH", 0))

    total_amount = pd.to_numeric(
        df["Final Amount (₹)"], errors="coerce"
    ).fillna(0).sum()

    projects_with_images = sum(parse_bool(v) for v in df["Has Images"])
    projects_without_images = total_projects - projects_with_images

    queue = df.sort_values(
        ["risk_score", "Final Amount (₹)"],
        ascending=[False, False]
    ).head(10)

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
            "risk_level": str(row.get("risk_level", "LOW")).upper(),
            "risk_reasons": parse_risk_reasons(row.get("risk_reasons", "[]")),
        })

    state_counts = (
        df["State"].fillna("Unknown").astype(str).value_counts().head(10)
    )

    state_distribution = [
        {"state": str(state), "projects": int(count)}
        for state, count in state_counts.items()
    ]

    # New V4 lifecycle summary.
    v4_risk_counts = (
        v4_df["Risk_Level"].fillna("LOW").astype(str).str.upper().value_counts()
    )

    pending_projects = int(
        pd.to_numeric(v4_df.get("Pending_Payment_Count"), errors="coerce")
        .fillna(0).gt(0).sum()
    )
    missing_expenditure = int(
        v4_df["Financial_Reconciliation_Flag"]
        .fillna("")
        .eq("Expenditure record unavailable")
        .sum()
    )
    financial_mismatch = int(
        v4_df["Financial_Reconciliation_Flag"]
        .fillna("")
        .eq("Expenditure differs from final amount")
        .sum()
    )
    missing_sanction = int(
        v4_df["Timeline_Flag"]
        .fillna("")
        .eq("Sanction date unavailable")
        .sum()
    )

    return {
        "summary": {
            "total_projects": total_projects,
            "total_amount": float(total_amount),
            "low_risk": low_count,
            "medium_risk": medium_count,
            "high_risk": high_count,
            "projects_with_images": projects_with_images,
            "projects_without_images": projects_without_images,
        },
        "risk_distribution": [
            {"level": "LOW", "count": low_count},
            {"level": "MEDIUM", "count": medium_count},
            {"level": "HIGH", "count": high_count},
        ],
        "state_distribution": state_distribution,
        "investigation_queue": investigation_queue,
        "v4_lifecycle_summary": {
            "projects": len(v4_df),
            "low_priority": int(v4_risk_counts.get("LOW", 0)),
            "medium_priority": int(v4_risk_counts.get("MEDIUM", 0)),
            "high_priority": int(v4_risk_counts.get("HIGH", 0)),
            "pending_payment_projects": pending_projects,
            "missing_expenditure_records": missing_expenditure,
            "financial_mismatch_projects": financial_mismatch,
            "missing_sanction_dates": missing_sanction,
        },
    }


# =========================================================
# EXISTING V3 PROJECT ENDPOINTS
# =========================================================

@app.get("/projects")
def get_projects(limit: int = 20):
    limit = max(1, min(limit, 100))
    projects = df.sort_values(
        ["risk_score", "Final Amount (₹)"],
        ascending=[False, False]
    ).head(limit)

    return {
        "total_projects": len(df),
        "returned_projects": len(projects),
        "projects": [
            {key: clean_value(value) for key, value in row.to_dict().items()}
            for _, row in projects.iterrows()
        ],
    }


@app.get("/projects/{work_id}")
def get_project(work_id: int):
    project = df[df["Work ID"] == work_id]
    if project.empty:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": {
        key: clean_value(value)
        for key, value in project.iloc[0].to_dict().items()
    }}


@app.get("/projects/{work_id}/similar")
def get_similar_projects(work_id: int, limit: int = 5):
    project = df[df["Work ID"] == work_id]
    if project.empty:
        raise HTTPException(status_code=404, detail="Project not found")

    limit = max(1, min(limit, 20))
    results = find_similar_projects(work_id, top_n=limit)

    return {
        "work_id": work_id,
        "similar_projects": results
    }


# =========================================================
# V4 FINANCIAL TRAIL
# =========================================================

@app.get("/projects/{work_id}/financial")
def get_financial_trail(work_id: int):
    row = v4_project(work_id)

    return {
        "work_id": work_id,
        "financial_trail": {
            "recommended_amount": clean_value(row.get("Recommended Amount (₹)")),
            "sanctioned_amount": clean_value(row.get("Sanctioned Amount (₹)")),
            "final_amount": clean_value(row.get("Final Amount (₹)")),
            "total_expenditure": clean_value(row.get("Expenditure_Total")),
            "sanction_minus_recommended": clean_value(
                row.get("Sanction_minus_Recommended")
            ),
            "expenditure_minus_final": clean_value(
                row.get("Expenditure_minus_Final")
            ),
            "expenditure_to_final_ratio": clean_value(
                row.get("Expenditure_to_Final_Ratio")
            ),
            "transaction_count": clean_value(row.get("Transaction_Count")),
            "vendor_count": clean_value(row.get("Vendor_Count")),
            "pending_payment_count": clean_value(
                row.get("Pending_Payment_Count")
            ),
            "successful_payment_count": clean_value(
                row.get("Successful_Payment_Count")
            ),
            "last_expenditure_date": clean_value(
                row.get("Last_Expenditure_Date")
            ),
            "has_expenditure_record": clean_value(
                row.get("Has_Expenditure_Record")
            ),
            "has_pending_payment": clean_value(
                row.get("Has_Pending_Payment")
            ),
            "reconciliation": clean_value(
                row.get("Financial_Reconciliation_Flag")
            ),
        }
    }


# =========================================================
# V4 TIMELINE
# =========================================================

@app.get("/projects/{work_id}/timeline")
def get_project_timeline(work_id: int):
    row = v4_project(work_id)

    return {
        "work_id": work_id,
        "timeline": {
            "recommendation_date": clean_value(row.get("Recommendation Date")),
            "sanction_date": clean_value(row.get("Sanction Date")),
            "completion_date": clean_value(row.get("Completed Date")),
            "recommendation_to_sanction_days": clean_value(
                row.get("Recommendation_to_Sanction_Days")
            ),
            "sanction_to_completion_days": clean_value(
                row.get("Sanction_to_Completion_Days")
            ),
            "work_stage": clean_value(row.get("Work Stage")),
            "is_completed": clean_value(row.get("Is Completed")),
            "status": clean_value(row.get("Timeline_Flag")),
        }
    }


# =========================================================
# V4 MP CONTEXT
# =========================================================

@app.get("/projects/{work_id}/mp-context")
def get_mp_context(work_id: int):
    row = v4_project(work_id)

    fields = {
        "mp_name": "MP Name",
        "constituency": "Constituency",
        "state": "State",
        "house": "House",
        "allocated_amount": "MP Allocated Amount (₹)",
        "total_expenditure": "MP Total Expenditure (₹)",
        "utilization_percent": "MP Utilization %",
        "completion_rate_percent": "MP Completion Rate %",
        "completed_works": "MP Completed Works",
        "recommended_works": "MP Recommended Works",
        "pending_payments": "MP Pending Payments",
        "unpaid_vendor_balance": "MP Unpaid Vendor Balance (₹)",
        "transaction_count": "MP Transaction Count",
    }

    return {
        "work_id": work_id,
        "mp_context": {
            key: clean_value(row.get(column))
            for key, column in fields.items()
        }
    }


# =========================================================
# V4 INVESTIGATION
# =========================================================

@app.get("/investigate/{work_id}")
def investigate_project(work_id: int, similar_limit: int = 5):
    # V4 project and risk.
    row = v4_project(work_id)

    risk_score = int(clean_value(row.get("Risk_Score")) or 0)
    risk_level = str(clean_value(row.get("Risk_Level")) or "LOW").upper()

    risk_reasons = split_reasons(row.get("Risk_Reasons", ""))

    has_images = parse_bool(row.get("Has Images", False))
    evidence_status = (
        "Image evidence available"
        if has_images
        else "No image evidence available"
    )

    similar_limit = max(1, min(similar_limit, 20))
    similar_projects = find_similar_projects(
        work_id,
        top_n=similar_limit
    )

    recommended_actions = [
        "Review the project amount against contextual comparable projects."
    ]

    if row.get("Financial_Reconciliation_Flag") == "Expenditure record unavailable":
        recommended_actions.append(
            "Verify the project's expenditure/payment records."
        )

    if row.get("Financial_Reconciliation_Flag") == "Expenditure differs from final amount":
        recommended_actions.append(
            "Reconcile aggregated expenditure against the final project amount."
        )

    if row.get("Has_Pending_Payment") is True:
        recommended_actions.append(
            "Review the in-progress payment transactions and supporting records."
        )

    if row.get("Timeline_Flag") != "Chronology consistent":
        recommended_actions.append(
            "Verify the recommendation, sanction and completion dates."
        )

    if not has_images:
        recommended_actions.append(
            "Verify supporting evidence because no image evidence is available."
        )

    if similar_projects:
        recommended_actions.append(
            "Compare project scope and administrative context with comparable projects."
        )

    if not recommended_actions:
        recommended_actions.append(
            "Routine verification may be sufficient based on available automated indicators."
        )

    priority = {
        "HIGH": "High investigation priority",
        "MEDIUM": "Medium investigation priority",
        "LOW": "Low investigation priority",
    }.get(risk_level, "Low investigation priority")

    return {
        "investigation": {
            "work_id": work_id,
            "priority": priority,
            "risk": {
                "score": risk_score,
                "level": risk_level,
                "reasons": risk_reasons,
                "dimensions": split_reasons(row.get("Risk_Dimensions", "")),
                "peer_median": clean_value(row.get("peer_median")),
                "peer_group_size": clean_value(row.get("peer_count")),
                "amount_ratio_to_peer_median": clean_value(
                    row.get("Amount_Ratio_to_Peer_Median")
                ),
            },
            "project": {
                "description": clean_value(row.get("Work Description")),
                "category": clean_value(row.get("Category")),
                "mp_name": clean_value(row.get("MP Name")),
                "constituency": clean_value(row.get("Constituency")),
                "state": clean_value(row.get("State")),
                "house": clean_value(row.get("House")),
                "amount": clean_value(row.get("Final Amount (₹)")),
            },
            "evidence": {
                "has_images": has_images,
                "status": evidence_status,
                "data_quality": clean_value(row.get("Data_Quality_Flag")),
            },
            "financial": {
                "recommended_amount": clean_value(row.get("Recommended Amount (₹)")),
                "sanctioned_amount": clean_value(row.get("Sanctioned Amount (₹)")),
                "final_amount": clean_value(row.get("Final Amount (₹)")),
                "total_expenditure": clean_value(row.get("Expenditure_Total")),
                "expenditure_minus_final": clean_value(row.get("Expenditure_minus_Final")),
                "sanction_minus_recommended": clean_value(
                    row.get("Sanction_minus_Recommended")
                ),
                "reconciliation": clean_value(
                    row.get("Financial_Reconciliation_Flag")
                ),
                "pending_payment_count": clean_value(
                    row.get("Pending_Payment_Count")
                ),
                "transaction_count": clean_value(row.get("Transaction_Count")),
                "vendor_count": clean_value(row.get("Vendor_Count")),
            },
            "timeline": {
                "recommendation_date": clean_value(row.get("Recommendation Date")),
                "sanction_date": clean_value(row.get("Sanction Date")),
                "completion_date": clean_value(row.get("Completed Date")),
                "recommendation_to_sanction_days": clean_value(
                    row.get("Recommendation_to_Sanction_Days")
                ),
                "sanction_to_completion_days": clean_value(
                    row.get("Sanction_to_Completion_Days")
                ),
                "status": clean_value(row.get("Timeline_Flag")),
            },
            "mp_context": {
                "allocated_amount": clean_value(row.get("MP Allocated Amount (₹)")),
                "total_expenditure": clean_value(row.get("MP Total Expenditure (₹)")),
                "utilization_percent": clean_value(row.get("MP Utilization %")),
                "completion_rate_percent": clean_value(row.get("MP Completion Rate %")),
                "completed_works": clean_value(row.get("MP Completed Works")),
                "recommended_works": clean_value(row.get("MP Recommended Works")),
                "pending_payments": clean_value(row.get("MP Pending Payments")),
                "unpaid_vendor_balance": clean_value(
                    row.get("MP Unpaid Vendor Balance (₹)")
                ),
            },
            "similar_projects": similar_projects,
            "recommended_verification": recommended_actions,
            "disclaimer": (
                "Automated indicators identify projects for closer review. "
                "They do not establish fraud, corruption, overpricing, or wrongdoing."
            ),
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
        "response": response,
        "trace": get_agent_trace()
    }
