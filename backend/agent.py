from groq import Groq
from dotenv import load_dotenv
import os
import json
import re
import ast
from pathlib import Path

import pandas as pd
try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None

from tools import (
    get_project_details,
    search_projects,
    compare_projects
)

from risk_engine_v4_optimized import load_v4_data, prepare_scored_dataframe



# =========================================================
# V4 INVESTIGATION DATA — CANONICAL SOURCE FOR AGENT
#
# IMPORTANT: Risk_Score / Risk_Level / Risk_Reasons / peer_median /
# peer_count / Amount_Ratio_to_Peer_Median do NOT exist in the raw
# investigation_projects_v4.csv on disk. They are computed at runtime
# by risk_engine_v4_optimized.prepare_scored_dataframe(), exactly the
# way main.py builds its own v4_df. The agent must use the SAME
# scored dataframe, or every risk_score/risk_level lookup returns
# None even though the Work ID exists in the file.
# =========================================================

_AGENT_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _AGENT_DIR.parent
_V4_CANDIDATES = [
    _PROJECT_DIR / "data" / "investigation_projects_v4.csv",
    _AGENT_DIR / "data" / "investigation_projects_v4.csv",
    Path.cwd() / "data" / "investigation_projects_v4.csv",
]
V4_DATA_PATH = next((p for p in _V4_CANDIDATES if p.exists()), _V4_CANDIDATES[0])

try:
    V4_DF = prepare_scored_dataframe(load_v4_data(V4_DATA_PATH))
    if "Work ID" in V4_DF.columns:
        V4_DF["Work ID"] = pd.to_numeric(V4_DF["Work ID"], errors="coerce")
except Exception as exc:
    print(f"[MPLADS Agent V4] FAILED TO LOAD/SCORE V4 DATA: {exc}")
    V4_DF = pd.DataFrame()

print(
    f"[MPLADS Agent V4] dataset={V4_DATA_PATH} "
    f"rows={len(V4_DF)} "
    f"has_risk_score={'YES' if 'Risk_Score' in V4_DF.columns else 'NO'} "
    f"work_193991={'YES' if not V4_DF.empty and 'Work ID' in V4_DF.columns and (V4_DF['Work ID'] == 193991).any() else 'NO'}"
)


def _v4_row(work_id):
    if V4_DF.empty or "Work ID" not in V4_DF.columns:
        return None
    try:
        wid = int(work_id)
    except Exception:
        return None
    rows = V4_DF[V4_DF["Work ID"] == wid]
    return None if rows.empty else rows.iloc[0]


def _v4_value(row, *columns):
    """
    Read a V4 value robustly even if the CSV column uses
    different capitalization, spaces, or underscores.
    """
    if row is None:
        return None

    # Exact match first
    for column in columns:
        if column in row.index:
            value = row.get(column)

            if pd.isna(value):
                continue

            if hasattr(value, "item"):
                try:
                    return value.item()
                except Exception:
                    pass

            return value

    # Normalized match: ignores case, spaces, hyphens and underscores
    def normalize(name):
        return re.sub(r"[^a-z0-9]", "", str(name).lower())

    normalized_columns = {
        normalize(col): col
        for col in row.index
    }

    for column in columns:
        actual_column = normalized_columns.get(normalize(column))

        if actual_column is None:
            continue

        value = row.get(actual_column)

        if pd.isna(value):
            continue

        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:
                pass

        return value

    return None

def _normalize_reasons(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value).strip()
    # Risk_Reasons from risk_engine_v4_optimized is a " | "-joined string,
    # not a Python-list repr, so try pipe-splitting before literal_eval.
    if " | " in text:
        return [x.strip() for x in text.split(" | ") if x.strip()]
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass
    return [text] if text else []


def _canonical_project_details(work_id):
    """Authoritative project/risk view. V4 wins whenever the Work ID exists there."""
    row = _v4_row(work_id)
    if row is None:
        # Preserve legacy support for IDs not yet present in V4.
        return get_project_details(int(work_id))

    reasons = _normalize_reasons(_v4_value(row, "risk_reasons", "Risk_Reasons", "Risk Reasons"))
    score = _v4_value(row, "risk_score", "Risk_Score", "Risk Score")
    level = _v4_value(row, "risk_level", "Risk_Level", "Risk Level")
    ratio = _v4_value(row, "Amount_Ratio_to_Peer_Median")
    peer_median = _v4_value(row, "peer_median", "Peer_Median")
    peer_count = _v4_value(row, "peer_count", "Peer_Count")

    return {
        "work_id": int(work_id),
        "project": {
            "work_id": int(work_id),
            "description": _v4_value(row, "Work Description"),
            "category": _v4_value(row, "Category"),
            "mp_name": _v4_value(row, "MP Name"),
            "constituency": _v4_value(row, "Constituency"),
            "state": _v4_value(row, "State"),
            "house": _v4_value(row, "House"),
            "final_amount": _v4_value(row, "Final Amount (₹)"),
            "completed_date": _v4_value(row, "Completed Date"),
            "has_images": _v4_value(row, "Has Images"),
        },
        "risk_score": score,
        "risk_level": level,
        "risk_reasons": reasons,
        "peer_median": peer_median,
        "peer_count": peer_count,
        "amount_ratio_to_peer_median": ratio,
    }


def get_financial_trail_v4(work_id):
    row = _v4_row(work_id)
    if row is None:
        return {"error": "Project not found in V4 investigation dataset."}
    return {
        "work_id": int(work_id),
        "recommended_amount": _v4_value(row, "Recommended Amount (₹)"),
        "sanctioned_amount": _v4_value(row, "Sanctioned Amount (₹)"),
        "final_amount": _v4_value(row, "Final Amount (₹)"),
        "total_expenditure": _v4_value(row, "Expenditure_Total"),
        "sanction_minus_recommended": _v4_value(row, "Sanction_minus_Recommended"),
        "expenditure_minus_final": _v4_value(row, "Expenditure_minus_Final"),
        "expenditure_to_final_ratio": _v4_value(row, "Expenditure_to_Final_Ratio"),
        "transaction_count": _v4_value(row, "Transaction_Count"),
        "vendor_count": _v4_value(row, "Vendor_Count"),
        "pending_payment_count": _v4_value(row, "Pending_Payment_Count"),
        "successful_payment_count": _v4_value(row, "Successful_Payment_Count"),
        "last_expenditure_date": _v4_value(row, "Last_Expenditure_Date"),
        "has_expenditure_record": _v4_value(row, "Has_Expenditure_Record"),
        "has_pending_payment": _v4_value(row, "Has_Pending_Payment"),
        "reconciliation": _v4_value(row, "Financial_Reconciliation_Flag"),
    }


def get_project_timeline_v4(work_id):
    row = _v4_row(work_id)
    if row is None:
        return {"error": "Project not found in V4 investigation dataset."}
    return {
        "work_id": int(work_id),
        "recommendation_date": _v4_value(row, "Recommendation Date"),
        "sanction_date": _v4_value(row, "Sanction Date"),
        "completion_date": _v4_value(row, "Completed Date"),
        "recommendation_to_sanction_days": _v4_value(row, "Recommendation_to_Sanction_Days"),
        "sanction_to_completion_days": _v4_value(row, "Sanction_to_Completion_Days"),
        "work_stage": _v4_value(row, "Work Stage"),
        "is_completed": _v4_value(row, "Is Completed"),
        "status": _v4_value(row, "Timeline_Flag"),
    }


def get_mp_context_v4(work_id):
    row = _v4_row(work_id)
    if row is None:
        return {"error": "Project not found in V4 investigation dataset."}
    fields = {
        "mp_name": "MP Name", "constituency": "Constituency", "state": "State", "house": "House",
        "allocated_amount": "MP Allocated Amount (₹)", "total_expenditure": "MP Total Expenditure (₹)",
        "utilization_percent": "MP Utilization %", "completion_rate_percent": "MP Completion Rate %",
        "completed_works": "MP Completed Works", "recommended_works": "MP Recommended Works",
        "pending_payments": "MP Pending Payments", "unpaid_vendor_balance": "MP Unpaid Vendor Balance (₹)",
        "transaction_count": "MP Transaction Count",
    }
    return {"work_id": int(work_id), **{k: _v4_value(row, c) for k,c in fields.items()}}


def compare_financials_v4(work_id):
    f = get_financial_trail_v4(work_id)
    return f


def _v4_compare_projects(work_id, limit=5):
    """Contextual comparables using the same V4 dataset and target amount."""
    target = _v4_row(work_id)
    if target is None:
        return {"error": "Project not found in V4 investigation dataset."}
    target_desc = str(_v4_value(target, "Work Description") or "").strip()
    target_state = _v4_value(target, "State")
    target_house = _v4_value(target, "House")
    target_category = _v4_value(target, "Category")
    target_const = _v4_value(target, "Constituency")
    target_amount = _v4_value(target, "Final Amount (₹)")
    if fuzz is None:
        return {"error": "rapidfuzz is required for contextual comparison."}

    candidates = V4_DF[(V4_DF["State"] == target_state) & (V4_DF["House"] == target_house) & (V4_DF["Category"] == target_category)].copy()
    results = []
    def quality(text):
        text = str(text or "").strip()
        words = text.split()
        if not text: return 0.0
        if len(text) < 25 or len(words) < 5: return 0.35
        if len(text) < 60 or len(words) < 10: return 0.65
        return 1.0
    tq = quality(target_desc)
    for _, row in candidates.iterrows():
        wid = _v4_value(row, "Work ID")
        if wid is None or int(wid) == int(work_id):
            continue
        desc = str(_v4_value(row, "Work Description") or "").strip()
        if not desc or not target_desc:
            continue
        text_sim = fuzz.token_set_ratio(target_desc.lower(), desc.lower())
        adj = text_sim * min(tq, quality(desc))
        same_const = _v4_value(row, "Constituency") == target_const
        score = adj * 0.60 + 30 + (10 if same_const else 0)
        amount = _v4_value(row, "Final Amount (₹)")
        diff_abs = None
        diff_pct_of_comparable = None
        if amount is not None and target_amount is not None:
            diff_abs = float(target_amount) - float(amount)
            if float(amount) != 0:
                diff_pct_of_comparable = diff_abs / float(amount) * 100
        results.append({
            "work_id": int(wid), "amount": amount, "description": desc,
            "similarity_score": round(score, 2), "text_similarity": round(text_sim, 2),
            "same_state": True, "same_house": True, "same_category": True,
            "same_constituency": same_const, "constituency": _v4_value(row, "Constituency"),
            "state": _v4_value(row, "State"), "house": _v4_value(row, "House"), "category": _v4_value(row, "Category"),
            "target_amount": target_amount, "amount_difference": diff_abs,
            "amount_difference_percent_vs_comparable": diff_pct_of_comparable,
        })
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    comps = results[:int(limit)]
    return {"target_project": {"work_id": int(work_id), "amount": target_amount, "description": target_desc, "state": target_state, "house": target_house, "category": target_category, "constituency": target_const}, "comparisons": comps}


# ---------------------------------------------------------------------------
# V4 ROUTING GUARD — stateless per-request intent + Work ID extraction
# ---------------------------------------------------------------------------
_WORK_ID_RE = re.compile(r"(?i)\b(?:work\s*id|workid|project\s*id|project)\s*[:#-]?\s*(\d{3,})\b")

def _route_query_v4(query: str):
    """Return (work_id, intent) without using previous request state."""
    q = (query or "").strip().lower()
    m = _WORK_ID_RE.search(query or "")
    work_id = int(m.group(1)) if m else None

    # Most-specific intents first.
    if any(k in q for k in (
        "full investigation", "full investigate", "investigate fully",
        "complete investigation", "complete investigate", "overall investigation"
    )):
        intent = "full"
    elif any(k in q for k in (
        "compare", "comparables", "comparable projects", "similar projects",
        "similar project", "peer projects"
    )):
        intent = "compare"
    elif any(k in q for k in (
        "financial", "financials", "expenditure", "payment", "payments",
        "vendor", "vendors", "money", "amount trail", "financial trail"
    )):
        intent = "financial"
    elif any(k in q for k in (
        "timeline", "time line", "dates", "duration", "recommendation date",
        "sanction date", "completion date", "chronology"
    )):
        intent = "timeline"
    elif any(k in q for k in (
        "mp context", "mp-level", "mp level", "allocation", "utilization",
        "utilisation", "completion rate", "recommended works"
    )):
        intent = "mp_context"
    elif any(k in q for k in (
        "risk", "risky", "risk score", "risk level", "risk indicator",
        "risk indicators", "why is", "why was", "flagged", "flag",
        "anomaly", "anomalies", "red flag", "red flags",
        "investigation priority"
    )):
        intent = "risk"
    else:
        intent = "project"

    return work_id, intent

def _extract_work_id(query):
    match = re.search(
        r"(?:work\s*id\s*(?:is|:)?\s*|project\s*(?:id\s*)?(?:is|:)?\s*)?(\d{4,})\b",
        query or "",
        re.I,
    )
    return int(match.group(1)) if match else None


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv("../.env")

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


# =========================================================
# AI SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
SECTION GATING RULE:
Only include a section when its corresponding evidence tool was executed in the current request.
Do not create a Comparative Analysis section for a financial-only request. Do not create Timeline
or MP Context sections unless those tools were called.

V4 CANONICAL DATA RULE:
When a Work ID exists in investigation_projects_v4.csv, V4 is authoritative for project amount,
risk score, risk level, risk reasons, lifecycle, financial trail, and MP context. Never use a legacy
V3 amount for the same Work ID.

FINANCIAL INTERPRETATION RULES:
- "Reconciled" means the dataset's reconciliation flag is Reconciled; do not translate this into
  "all funds accounted for" or any broader compliance conclusion.
- Pending payment count means payment records are marked pending/in-progress in the dataset; do not
  infer contractual obligations, vendor non-payment, or misconduct.
- Vendor count and transaction count are descriptive facts only; do not imply vendor vetting problems
  or procurement irregularity without explicit evidence.

COMPARISON NUMBERS:
If comparison evidence contains amount_difference or amount_difference_percent_vs_comparable, those
are target-minus-comparable figures. Never describe a comparable project's amount as the difference.
A large difference is an observation requiring scope/rate/quantity verification, not proof of overpricing.

STATELESS REQUEST RULE:
Every incoming /agent/investigate request is independent. Never reuse a Work ID,
tool result, selected project, or trace from a previous request.

EXPLICIT WORK ID RULE:
If the user's current query contains an explicit Work ID, that Work ID is
authoritative and must be used for every tool call in this request. Never use
a Work ID from prior conversation/tool state instead.

INTENT ROUTING RULE:
- risk/risky/flagged/anomaly/why is this project risky questions -> get_project_details
- financial/expenditure/payment/vendor questions -> get_financial_trail
- timeline/date/duration/chronology questions -> get_project_timeline
- MP allocation/utilization/completion-rate questions -> get_mp_context
- compare/similar/comparable questions -> compare_projects (and project details
  when needed for context)
- full investigation -> collect project details, financial trail, timeline,
  MP context, and comparisons before synthesis
- general project explanation -> get_project_details

Do not call an unrelated tool merely because its result is already available.

You are the MPLADS AI Investigation Copilot.

Your role is to help investigators analyze public MPLADS project data
and prioritize projects for human verification.

You are an investigation-support assistant.

You are NOT a fraud detector.

You must NEVER claim that a project is:
- fraudulent
- corrupt
- illegal
- overpriced
- misallocated
- coordinated
- involved in wrongdoing

unless explicit evidence returned by an approved tool establishes that
fact. The current tools do not establish such conclusions.

Risk indicators are signals for verification, NOT proof of wrongdoing.


=========================================================
1. STRICT EVIDENCE DISCIPLINE
=========================================================

Use ONLY information returned by the available tools.

Never invent or assume:

- contractors
- vendors
- tender details
- payment records
- approval dates
- sanction dates
- project duration
- budget allocations
- procurement outcomes
- inspection results
- financial transactions
- relationships between projects
- relationships between MPs and contractors
- reasons for project approval
- field conditions
- completion status beyond what the tool provides
- statistics
- dates or timelines
- monetary thresholds

If information is not available from the tools, explicitly state:

"This information is not available in the current dataset."

Do not silently fill missing information using general assumptions.

NUMERIC AND DATA FIDELITY:
- Treat numeric values returned by tools as authoritative.
- Never change, round, multiply, divide, or otherwise recalculate a tool-returned amount,
  score, percentage, Work ID, or similarity value unless the user explicitly asks for a calculation.
- When reporting a monetary amount, preserve exactly the digits returned by the tool.
- If formatting a monetary amount with Indian comma separators, verify that the formatted
  value contains exactly the same digits as the tool-returned value.
- Before finalizing, cross-check every important number against the supplied tool evidence.
- Never infer a number from another number.
- In comparative explanations, do not reproduce or calculate monetary amounts or
  amount-difference percentages; describe the financial relationship qualitatively.
- Exact financial values must remain in deterministic tool/frontend output, not be
  generated or recalculated by the language model.

- For monetary amounts, prefer clean Indian currency formatting with no unnecessary
  decimal suffix when the tool value is an exact whole rupee amount.
  Example: 3444811 must be displayed as ₹34,44,811, not ₹3,444,811.0.
- Do not create a second monetary representation of the same value with different digits.
- If get_project_details returns risk_reasons, those returned reasons are authoritative.
- Include all returned risk_reasons (or an accurate summary of all of them) in the Evidence Summary.
- Never say that no specific risk indicators were provided when risk_reasons are present.
- Never invent additional risk indicators.
- Do not add internal list/index numbers to risk reasons, evidence items, or other output.
- When listing risk reasons, use bullet points containing only the actual reason text returned
  by the tool.


=========================================================
2. OBSERVATION VS RECOMMENDATION
=========================================================

Always distinguish between:

A. OBSERVED EVIDENCE
Information actually returned by a tool.

B. RECOMMENDED VERIFICATION
Information that an investigator should obtain or verify.

Never present a recommended verification step as an established fact.

Example:

WRONG:
"Multiple projects were approved concurrently."

CORRECT:
"The risk engine includes a project-concentration indicator for the
same period. The current dataset does not establish the approval
circumstances."

WRONG:
"The contractor was duly vetted."

CORRECT:
"Contractor eligibility and procurement records should be verified
if those records are available."

WRONG:
"The amount was misallocated."

CORRECT:
"The project amount is a risk indicator that warrants verification."


=========================================================
3. TOOL USAGE
=========================================================

Use get_project_details when the user asks about a specific Work ID.

Use search_projects when the user asks to:
- find projects
- filter projects
- list projects
- find projects by state
- find projects by risk level
- find projects by amount
- find projects based on image availability

Use compare_projects when the user asks:
- why a project is unusual
- how a project compares with similar projects
- whether comparable projects have different amounts
- about the cost relative to comparable projects

Use get_financial_trail when the user asks about:
- recommended, sanctioned, final or expenditure amounts
- payments or transactions
- vendors
- pending payments
- financial reconciliation

Use compare_financials when the user asks whether the financial values reconcile
or whether expenditure is consistent with the final amount.

Use get_project_timeline when the user asks about:
- recommendation, sanction or completion dates
- project duration
- lifecycle timing
- work stage
- chronology

Use get_mp_context when the user asks about:
- the MP's allocation or utilization
- MP-level expenditure
- completed or recommended works
- MP-level pending payments
- broader MP context for a project

For a request for a "full investigation", "complete investigation", or "investigate this project",
use get_project_details plus the V4 tools needed to cover risk, financial trail,
timeline, MP context and contextual comparison. Do not call every tool merely because
it exists; select tools that answer the investigator's question.

You may use more than one tool when necessary.

Never replace tool evidence with guesses.


=========================================================
4. SPECIFIC WORK ID
=========================================================

When a Work ID is provided:

1. Treat the explicitly provided Work ID as authoritative.
2. Retrieve the project details using get_project_details.
3. Select additional V4 tools according to the user's question.
4. Use compare_projects for contextual similarity/cost comparison.
5. Use search_projects only when broader filtering or discovery is required.
6. Never substitute another Work ID because a different project was previously selected
   in the frontend or appeared in another tool result.

Always preserve the exact Work ID returned by the tool.


=========================================================
5. COMPARISON RULES
=========================================================

When discussing comparable projects:

- Use only projects returned by compare_projects.
- Report project amounts exactly as returned.
- Report similarity scores exactly as returned.
- Clearly distinguish contextual similarity from cost difference.
- Do not claim that two projects have identical scope merely because
  they were returned as comparable.
- Do not claim that similar projects are equivalent projects.
- A large amount difference is an observation, NOT proof of overpricing.
- Never call a project overpriced unless explicit tool evidence says so.
- Never infer fraud, corruption, collusion, or wrongdoing from
  similarity or amount differences.

If similarity is weak or limited, explicitly state that the comparison
should be treated as contextual rather than definitive.


=========================================================
6. RISK SCORE
=========================================================

Treat the risk score and risk level returned by the tool as
authoritative.

Never:
- change the score
- recalculate the score
- invent another score
- invent thresholds
- reinterpret the risk levels

Explain the risk reasons as indicators returned by the risk engine.

If the tool says:

"High project concentration in the same period"

do NOT automatically say:

"Projects were approved concurrently."

Instead say:

"The risk engine identifies high project concentration in the same
period. The current dataset does not establish the approval
circumstances."


=========================================================
7. RISK LANGUAGE
=========================================================

Prefer these terms:

- risk indicator
- anomaly
- investigation priority
- contextual comparison
- verification
- evidence review
- potential irregularity requiring verification
- investigation signal

Avoid accusatory language.

The purpose of the system is to prioritize human investigation,
not to determine guilt.


=========================================================
8. RECOMMENDED VERIFICATION
=========================================================

Recommendations must be phrased as actions an investigator can take.

Good examples:

- "Obtain the detailed project scope."
- "Compare the amount with additional contextual projects."
- "Review procurement records."
- "Verify the approved amount against the final expenditure."
- "Request site inspection records."
- "Review available photographic evidence."
- "Verify contractor information if available."
- "Check the relevant MPLADS documentation."

Do NOT claim that these documents contain a problem.

Do NOT claim that a contractor exists unless the tool provides
contractor information.

Do NOT claim that procurement irregularities exist.

IMPORTANT ANTI-INFERENCE RULES FOR V4:
- "Pending payments" means only that the approved tool reports pending/in-progress
  payment records. Do not describe them as unsettled contractual obligations unless
  the tool explicitly establishes that.
- A vendor count means only that the approved tool reports that number of vendors.
  Do not infer vendor vetting, procurement compliance, common ownership, or any
  other vendor relationship.
- "Reconciled" means report the tool's reconciliation status. Do not convert it into
  a broader conclusion that funds were properly used or that all obligations were
  settled.
- Equality or difference between recommended, sanctioned, final and expenditure
  amounts is an observation. Do not infer why the amounts differ unless the tool
  provides that reason.
- A last expenditure date is an observed transaction date. Do not use it to prove
  physical completion or site conditions.
- An image-available flag establishes availability in the dataset only; it does not
  establish image authenticity, quality, or physical verification.
- MP-level utilization, completion rate, pending payments, vendor balance, or other
  context must not be treated as proof of a project-level problem.

- Do not use causal or evaluative wording such as "indicating", "showing that",
  "suggesting", "confirm that", "properly", "fully settled", or "no deviation"
  unless the tool output explicitly establishes that conclusion.
- When two reported financial fields are equal, state the equality as an
  observation only.
- Verification actions may ask investigators to review contracts, invoices,
  procurement records, inspections, or supporting documents, but must not imply
  that an irregularity already exists.

The recommendation is what should be checked, not what has been found.


=========================================================
9. PROHIBITED INFERENCES
=========================================================

Do NOT convert:

project concentration
→ coordinated allocation

amount difference
→ overpricing

large amount
→ misallocation

similar descriptions
→ same contractor

same period
→ coordinated procurement

same constituency
→ relationship between projects

missing information
→ suspicious activity

risk score
→ proof of wrongdoing

Do not make any of these inferences.


=========================================================
10. MISSING DATA
=========================================================

The current dataset may not contain every piece of information needed
for a complete investigation.

When relevant information is missing, clearly say:

"This information is not available in the current dataset."

Then provide a reasonable verification action.

Example:

"The current dataset does not contain contractor information.
Contractor details can be obtained from the relevant procurement
records for verification."


=========================================================
11. OUTPUT FORMAT
=========================================================

Give a concise investigation brief.

OUTPUT RELEVANCE RULE:
- Include only sections supported by the tools used for the user's question.
- Do NOT create a Comparative Analysis section unless compare_projects evidence
  was actually returned.
- Do NOT say that comparative data are missing merely because the comparison tool
  was not requested.
- For a financial-only question, focus on the financial evidence and relevant
  financial verification actions.
- For a timeline-only question, focus on timeline evidence and relevant timeline
  verification actions.
- For an MP-context question, focus on MP context and do not imply project-level
  wrongdoing from MP-level statistics.

Prefer this structure:

### Investigation Summary

Identify the project and summarize the tool-returned facts.

### Evidence Summary

Explain the actual risk indicators returned by the tools.

### Comparative Analysis

Only include this section when comparison information is available.

Show:
- comparable Work IDs
- contextual similarity
- project amounts
- amount differences
- relevant state/house/category/constituency information

Clearly distinguish similarity from cost.

### Recommended Verification Actions

Give focused, practical actions for a human investigator.

### Conclusion

State that the indicators justify focused verification but do not
establish wrongdoing.

Always distinguish available evidence from information that still needs
to be obtained.


=========================================================
12. FINAL PRINCIPLE
=========================================================

Your job is to answer:

"WHAT SHOULD AN INVESTIGATOR CHECK NEXT?"

Your job is NOT to answer:

"DID FRAUD OCCUR?"

Use the available tools, stay grounded in evidence, explain the risk
signals clearly, and support human investigation.
"""


# =========================================================
# AI TOOLS
# =========================================================

tools = [

    # =====================================================
    # TOOL 1 — GET PROJECT DETAILS
    # =====================================================

    {
        "type": "function",
        "function": {
            "name": "get_project_details",

            "description": (
                "Get structured details, risk score, risk level, "
                "and risk indicators for a specific MPLADS project."
            ),

            "parameters": {
                "type": "object",

                "properties": {
                    "work_id": {
                        "type": "integer",
                        "description": (
                            "The MPLADS Work ID of the project."
                        )
                    }
                },

                "required": ["work_id"]
            }
        }
    },


    # =====================================================
    # TOOL 2 — SEARCH PROJECTS
    # =====================================================

    {
        "type": "function",
        "function": {
            "name": "search_projects",

            "description": (
                "Search MPLADS projects using available filters "
                "such as state, risk level, minimum or maximum "
                "project amount, and image availability. "
                "Use this tool when the user asks to find, "
                "filter, or list projects."
            ),

            "parameters": {
                "type": "object",

                "properties": {

                    "state": {
                        "type": "string",
                        "description": (
                            "Indian state to filter projects by."
                        )
                    },

                    "risk_level": {
                        "type": "string",
                        "enum": [
                            "LOW",
                            "MEDIUM",
                            "HIGH"
                        ],
                        "description": (
                            "Risk level to filter projects by."
                        )
                    },

                    "min_amount": {
                        "type": "number",
                        "description": (
                            "Minimum project amount in rupees."
                        )
                    },

                    "max_amount": {
                        "type": "number",
                        "description": (
                            "Maximum project amount in rupees."
                        )
                    },

                    "has_images": {
                        "type": "boolean",
                        "description": (
                            "Filter by whether project images "
                            "are available."
                        )
                    },

                    "limit": {
                        "type": "integer",
                        "description": (
                            "Maximum number of projects to return."
                        )
                    }
                },

                "required": []
            }
        }
    },


    # =====================================================
    # TOOL 3 — COMPARE PROJECTS
    # =====================================================

    {
        "type": "function",
        "function": {
            "name": "compare_projects",

            "description": (
                "Compare a specific MPLADS project with similar "
                "projects using similarity scores, project "
                "amounts, categories, states, houses, and "
                "constituencies. Use this tool when the user "
                "asks why a project is unusual, asks for "
                "comparison with similar projects, or asks "
                "about its cost relative to comparable projects."
            ),

            "parameters": {
                "type": "object",

                "properties": {

                    "work_id": {
                        "type": "integer",
                        "description": (
                            "The MPLADS Work ID to compare."
                        )
                    },

                    "limit": {
                        "type": "integer",
                        "description": (
                            "Number of similar projects to compare."
                        )
                    }
                },

                "required": ["work_id"]
            }
        }
    },

    # =====================================================
    # TOOL 4 — GET FINANCIAL TRAIL
    # =====================================================

    {
        "type": "function",
        "function": {
            "name": "get_financial_trail",
            "description": (
                "Get the deterministic financial trail for a specific MPLADS "
                "project, including recommended, sanctioned, final and "
                "expenditure amounts, transactions, vendors, payment status "
                "and reconciliation. This tool reports observations only; "
                "do not infer vendor vetting or contractual obligations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "work_id": {
                        "type": "integer",
                        "description": "The MPLADS Work ID of the project."
                    }
                },
                "required": ["work_id"]
            }
        }
    },

    # =====================================================
    # TOOL 5 — GET PROJECT TIMELINE
    # =====================================================

    {
        "type": "function",
        "function": {
            "name": "get_project_timeline",
            "description": (
                "Get recommendation, sanction and completion dates, "
                "calculated lifecycle durations, work stage and chronology "
                "status for a specific MPLADS project."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "work_id": {
                        "type": "integer",
                        "description": "The MPLADS Work ID of the project."
                    }
                },
                "required": ["work_id"]
            }
        }
    },

    # =====================================================
    # TOOL 6 — GET MP CONTEXT
    # =====================================================

    {
        "type": "function",
        "function": {
            "name": "get_mp_context",
            "description": (
                "Get MP-level contextual information associated with a project, "
                "including allocation, expenditure, utilization, completion, "
                "recommended works and pending payments."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "work_id": {
                        "type": "integer",
                        "description": "The MPLADS Work ID of the project."
                    }
                },
                "required": ["work_id"]
            }
        }
    },

    # =====================================================
    # TOOL 7 — COMPARE FINANCIALS
    # =====================================================

    {
        "type": "function",
        "function": {
            "name": "compare_financials",
            "description": (
                "Reconcile the recommended, sanctioned, final and expenditure "
                "amounts for one MPLADS project and return payment/reconciliation "
                "indicators. Use for questions specifically about financial "
                "consistency or reconciliation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "work_id": {
                        "type": "integer",
                        "description": "The MPLADS Work ID of the project."
                    }
                },
                "required": ["work_id"]
            }
        }
    }

]


# =========================================================
# AGENT EXECUTION TRACE
# =========================================================

LAST_AGENT_TRACE = []


def reset_agent_trace():
    global LAST_AGENT_TRACE
    LAST_AGENT_TRACE = []


def get_agent_trace():
    return list(LAST_AGENT_TRACE)


# =========================================================
# TOOL EXECUTOR
# =========================================================

def execute_tool(tool_name, arguments):

    LAST_AGENT_TRACE.append({
        "tool": tool_name,
        "status": "executed",
        "arguments": arguments
    })

    # -----------------------------------------------------
    # GET PROJECT DETAILS
    # -----------------------------------------------------

    if tool_name == "get_project_details":
        return _canonical_project_details(arguments["work_id"])


    # -----------------------------------------------------
    # SEARCH PROJECTS
    # -----------------------------------------------------

    if tool_name == "search_projects":

        return search_projects(
            state=arguments.get("state"),
            risk_level=arguments.get("risk_level"),
            min_amount=arguments.get("min_amount"),
            max_amount=arguments.get("max_amount"),
            has_images=arguments.get("has_images"),
            limit=arguments.get("limit", 10)
        )


    # -----------------------------------------------------
    # COMPARE PROJECTS
    # -----------------------------------------------------

    if tool_name == "compare_projects":
        return _v4_compare_projects(arguments["work_id"], arguments.get("limit", 5))


    # -----------------------------------------------------
    # V4 — FINANCIAL TRAIL
    # -----------------------------------------------------

    if tool_name == "get_financial_trail":
        return get_financial_trail_v4(arguments["work_id"])


    # -----------------------------------------------------
    # V4 — PROJECT TIMELINE
    # -----------------------------------------------------

    if tool_name == "get_project_timeline":
        return get_project_timeline_v4(arguments["work_id"])


    # -----------------------------------------------------
    # V4 — MP CONTEXT
    # -----------------------------------------------------

    if tool_name == "get_mp_context":
        return get_mp_context_v4(arguments["work_id"])


    # -----------------------------------------------------
    # V4 — FINANCIAL COMPARISON
    # -----------------------------------------------------

    if tool_name == "compare_financials":
        return compare_financials_v4(arguments["work_id"])


    # -----------------------------------------------------
    # UNKNOWN TOOL
    # -----------------------------------------------------

    return {
        "error": "Unknown tool"
    }


# =========================================================
# AI INVESTIGATION AGENT
# =========================================================

def _fallback_with_trace(work_id, user_query=""):
    """Run the deterministic fallback and record synthesis completion."""
    result = _deterministic_fallback(work_id, user_query)
    LAST_AGENT_TRACE.append({
        "tool": "Deterministic evidence synthesis",
        "status": "completed"
    })
    return result


def _deterministic_full_investigation_v4(work_id: int):
    """Build a complete evidence-grounded investigation without an LLM."""
    wid = int(work_id)
    project = execute_tool("get_project_details", {"work_id": wid})
    financial = execute_tool("get_financial_trail", {"work_id": wid})
    timeline = execute_tool("get_project_timeline", {"work_id": wid})
    mp = execute_tool("get_mp_context", {"work_id": wid})
    comparison = execute_tool("compare_projects", {"work_id": wid, "limit": 5})

    def money(v):
        try:
            return f"₹{float(v):,.0f}"
        except Exception:
            return "N/A"

    lines = ["### Full Investigation"]
    lines.append(f"- **Work ID:** {wid}")

    # Project/risk
    # NOTE: get_project_details / _canonical_project_details returns
    # {"work_id":..., "project": {...}, "risk_score":..., "risk_level":..., "risk_reasons":...}
    # so nested project fields must be read from project["project"], not the top level.
    if isinstance(project, dict):
        proj = project.get("project", {}) if isinstance(project.get("project"), dict) else {}
        lines += [
            f"- **Project:** {proj.get('description', 'N/A')}",
            f"- **Category:** {proj.get('category', 'N/A')}",
            f"- **Location:** {proj.get('state', 'N/A')}, {proj.get('constituency', 'N/A')}",
            f"- **House:** {proj.get('house', 'N/A')}",
            f"- **Risk:** {project.get('risk_level', 'N/A')} "
            f"({project.get('risk_score', 'N/A')}/100)",
        ]
        reasons = project.get("risk_reasons", [])
        if isinstance(reasons, str):
            reasons = _normalize_reasons(reasons)
        if reasons:
            lines.append("\n### Risk Indicators")
            for r in reasons:
                lines.append(f"- {r}")

    # Financial
    if isinstance(financial, dict):
        lines.append("\n### Financial Trail")
        for label, keys in [
            ("Recommended amount", ["recommended_amount", "Recommended Amount"]),
            ("Sanctioned amount", ["sanctioned_amount", "Sanctioned Amount"]),
            ("Final amount", ["final_amount", "Final Amount"]),
            ("Total expenditure", ["total_expenditure", "Total Expenditure"]),
        ]:
            value = next((financial[k] for k in keys if k in financial), None)
            lines.append(f"- **{label}:** {money(value)}")
        for label, keys in [
            ("Transactions", ["transaction_count", "Transaction Count"]),
            ("Vendors", ["vendor_count", "Vendor Count"]),
            ("Pending payments", ["pending_payment_count", "Pending Payment Count"]),
            ("Successful payments", ["successful_payment_count", "Successful Payment Count"]),
        ]:
            value = next((financial[k] for k in keys if k in financial), None)
            if value is not None:
                lines.append(f"- **{label}:** {value}")
        recon = financial.get("reconciliation", financial.get("reconciliation_status", financial.get("Reconciliation Status")))
        if recon is not None:
            lines.append(f"- **Reconciliation status:** {recon}")

    # Timeline
    if isinstance(timeline, dict):
        lines.append("\n### Timeline")
        for label, keys in [
            ("Recommendation date", ["recommendation_date", "Recommendation Date"]),
            ("Sanction date", ["sanction_date", "Sanction Date"]),
            ("Completion date", ["completion_date", "Completion Date"]),
            ("Recommendation → sanction", ["recommendation_to_sanction_days"]),
            ("Sanction → completion", ["sanction_to_completion_days"]),
            ("Work stage", ["work_stage"]),
            ("Chronology", ["status", "chronology_status", "timeline_status"]),
        ]:
            value = next((timeline[k] for k in keys if k in timeline), None)
            if value is not None:
                suffix = " days" if "→" in label else ""
                lines.append(f"- **{label}:** {value}{suffix}")

    # Comparables
    if isinstance(comparison, dict):
        items = comparison.get("comparisons", comparison.get("similar_projects", []))
        if items:
            lines.append("\n### Comparable Projects")
            for item in items[:5]:
                wid2 = item.get("work_id", item.get("Work ID", "N/A"))
                amount = item.get("amount", item.get("final_amount", item.get("Final Amount")))
                sim = item.get("similarity_score", item.get("similarity"))
                lines.append(
                    f"- Work ID {wid2}: amount {money(amount)}, "
                    f"similarity {sim if sim is not None else 'N/A'}"
                )

    # MP context
    if isinstance(mp, dict):
        lines.append("\n### MP Context")
        for label, keys, formatter in [
            ("Allocated amount", ["allocated_amount"], money),
            ("Total expenditure", ["total_expenditure"], money),
            ("Utilization", ["utilization_percent", "utilization_percentage"], lambda x: f"{float(x):.2f}%"),
            ("Completion rate", ["completion_rate_percent", "completion_rate"], lambda x: f"{float(x):.2f}%"),
            ("Recommended works", ["recommended_works"], lambda x: str(x)),
            ("Completed works", ["completed_works"], lambda x: str(x)),
            ("Pending payments", ["pending_payments"], lambda x: str(x)),
            ("Unpaid vendor balance", ["unpaid_vendor_balance"], money),
        ]:
            value = next((mp[k] for k in keys if k in mp), None)
            if value is not None:
                try:
                    rendered = formatter(value)
                except Exception:
                    rendered = str(value)
                lines.append(f"- **{label}:** {rendered}")

    lines += [
        "\n### Recommended Verification Plan",
        "- Review the approved project scope, technical specifications and cost basis.",
        "- Compare the target project with the returned contextual comparable projects.",
        "- Review the supporting financial and payment records, including any pending payments.",
        "- Cross-check recommendation, sanction and completion records with available inspection evidence.",
        "- Review relevant MP-level allocation and utilization context.",
        "\n### Conclusion",
        "The available indicators support focused human verification. "
        "They do not, by themselves, establish fraud, corruption, overpricing, "
        "or other wrongdoing."
    ]
    return "\n".join(lines)


def _deterministic_risk_investigation_v4(work_id: int):
    """Return only authoritative V4 project/risk evidence for a risk query."""
    details = _canonical_project_details(int(work_id))
    if not isinstance(details, dict) or details.get("error"):
        return "Risk data could not be loaded for the requested Work ID."

    project = details.get("project", {}) if isinstance(details.get("project"), dict) else {}
    score = details.get("risk_score")
    level = details.get("risk_level")
    reasons = details.get("risk_reasons", [])
    if isinstance(reasons, str):
        reasons = _normalize_reasons(reasons)

    peer_median = details.get("peer_median")
    peer_count = details.get("peer_count")
    ratio = details.get("amount_ratio_to_peer_median")

    if score is None or level is None:
        return (
            f"### Risk Assessment\n\n"
            f"- **Work ID:** {int(work_id)}\n"
            "- V4 risk evidence could not be retrieved.\n"
            "- I will not infer or invent a risk score without deterministic engine evidence."
        )

    lines = [
        "### Investigation Summary",
        f"- **Work ID:** {int(work_id)}",
        f"- **Project:** {project.get('description', 'N/A')}",
        f"- **Risk:** {str(level).upper()} — {float(score):.0f}/100",
        "",
        "### Risk Indicators",
    ]

    if reasons:
        lines.extend(f"- {reason}" for reason in reasons)
    else:
        lines.append("- No risk indicators were returned by the deterministic V4 risk engine.")

    if peer_median is not None or peer_count is not None or ratio is not None:
        lines += ["", "### Context"]
        if peer_median is not None:
            lines.append(f"- Contextual peer median: ₹{float(peer_median):,.0f}")
        if peer_count is not None:
            lines.append(f"- Contextual peer group size: {int(peer_count)}")
        if ratio is not None:
            lines.append(f"- Final amount / contextual peer median: {float(ratio):.2f}×")

    lines += [
        "",
        "### Interpretation",
        "These are contextual investigation indicators, not proof of fraud, corruption, "
        "overpricing, or wrongdoing.",
        "",
        "### Recommended Verification",
        "- Review the approved scope, quantities and rates against the project records.",
        "- Compare the project with appropriate contextual comparables.",
        "- Verify the supporting financial and documentary evidence before drawing conclusions.",
    ]
    return "\n".join(lines)

def _deterministic_fallback_legacy(work_id, user_query=""):
    """Evidence-based local fallback used when Groq is unavailable.

    The fallback is intentionally query-aware so the three Copilot actions
    do not all return the same generic investigation brief.
    """
    try:
        details = _canonical_project_details(int(work_id))
    except Exception as exc:
        return f"Investigation data could not be loaded: {exc}"

    target = details.get("project", details) if isinstance(details, dict) else {}

    reasons = []
    if isinstance(details, dict):
        reasons = details.get("risk_reasons", [])
        if not reasons and isinstance(target, dict):
            reasons = target.get("risk_reasons", [])

    # Normalize risk reasons so they always render as separate bullets.
    if isinstance(reasons, str):
        reasons = _normalize_reasons(reasons)
    elif isinstance(reasons, list):
        # Handles cases where the list itself contains a stringified list.
        if (
            len(reasons) == 1
            and isinstance(reasons[0], str)
            and reasons[0].strip().startswith("[")
        ):
            try:
                parsed = ast.literal_eval(reasons[0])
                if isinstance(parsed, list):
                    reasons = parsed
            except (ValueError, SyntaxError):
                pass
    else:
        reasons = [str(reasons)]

    reasons = [str(reason) for reason in reasons if str(reason).strip()]



    score = target.get("risk_score", details.get("risk_score", "N/A"))
    level = target.get("risk_level", details.get("risk_level", "N/A"))
    desc = target.get("description", target.get("work_description", "Unknown"))
    category = target.get("category", "Unknown")
    state = target.get("state", "Unknown")
    constituency = target.get("constituency", "Unknown")
    house = target.get("house", "Unknown")
    images = target.get("has_images", target.get("images", "Unknown"))

    q = (user_query or "").lower()

    # ---------------------------------------------------------
    # V4 QUERY: RISK
    # ---------------------------------------------------------
    if any(k in q for k in (
        "risk", "risky", "risk score", "risk level", "risk indicator",
        "risk indicators", "why is", "why was", "flagged", "flag",
        "anomaly", "anomalies", "red flag", "red flags",
        "investigation priority"
    )):
        return _deterministic_risk_investigation_v4(int(work_id))

    # ---------------------------------------------------------
    # V4 QUERY: FINANCIALS
    # ---------------------------------------------------------

    if any(k in q for k in (
        "financial", "expenditure", "payment", "vendor",
        "reconcile", "reconciliation", "sanctioned amount",
        "recommended amount", "final amount"
    )):
        financial = get_financial_trail_v4(int(work_id))
        if "error" in financial:
            return f"Financial data could not be loaded: {financial['error']}"

        return "\n".join([
            "### Financial Investigation",
            f"• Work ID: {work_id}",
            f"• Recommended amount: {financial.get('recommended_amount')}",
            f"• Sanctioned amount: {financial.get('sanctioned_amount')}",
            f"• Final amount: {financial.get('final_amount')}",
            f"• Total expenditure: {financial.get('total_expenditure')}",
            f"• Reconciliation: {financial.get('reconciliation')}",
            f"• Transactions: {financial.get('transaction_count')}",
            f"• Vendors: {financial.get('vendor_count')}",
            f"• Pending payments: {financial.get('pending_payment_count')}",
            "",
            "### Recommended Verification",
            "• Verify the underlying expenditure and payment records.",
            "• Review supporting financial and approval documentation.",
            "",
            "These are deterministic dataset observations and do not establish wrongdoing.",
        ])


    # ---------------------------------------------------------
    # V4 QUERY: TIMELINE
    # ---------------------------------------------------------

    if any(k in q for k in (
        "timeline", "duration", "sanction date", "completion date",
        "recommendation date", "how long", "chronology"
    )):
        timeline = get_project_timeline_v4(int(work_id))
        if "error" in timeline:
            return f"Timeline data could not be loaded: {timeline['error']}"

        return "\n".join([
            "### Project Timeline",
            f"• Work ID: {work_id}",
            f"• Recommendation date: {timeline.get('recommendation_date')}",
            f"• Sanction date: {timeline.get('sanction_date')}",
            f"• Completion date: {timeline.get('completion_date')}",
            f"• Recommendation → sanction: {timeline.get('recommendation_to_sanction_days')} days",
            f"• Sanction → completion: {timeline.get('sanction_to_completion_days')} days",
            f"• Work stage: {timeline.get('work_stage')}",
            f"• Chronology status: {timeline.get('status')}",
            "",
            "### Recommended Verification",
            "• Verify the underlying recommendation, sanction and completion records.",
        ])


    # ---------------------------------------------------------
    # V4 QUERY: MP CONTEXT
    # ---------------------------------------------------------

    if any(k in q for k in (
        "mp context", "mp-level", "mp level", "allocation",
        "utilization", "completed works", "recommended works"
    )):
        context = get_mp_context_v4(int(work_id))
        if "error" in context:
            return f"MP context could not be loaded: {context['error']}"

        return "\n".join([
            "### MP Context",
            f"• Work ID: {work_id}",
            f"• MP: {context.get('mp_name')}",
            f"• Constituency: {context.get('constituency')}",
            f"• State: {context.get('state')}",
            f"• House: {context.get('house')}",
            f"• Allocated amount: {context.get('allocated_amount')}",
            f"• Total expenditure: {context.get('total_expenditure')}",
            f"• Utilization: {context.get('utilization_percent')}%",
            f"• Completion rate: {context.get('completion_rate_percent')}%",
            f"• Recommended works: {context.get('recommended_works')}",
            f"• Completed works: {context.get('completed_works')}",
            f"• Pending payments: {context.get('pending_payments')}",
            "",
            "MP-level figures provide context for investigation; they do not by themselves establish an issue with the project.",
        ])


    # ---------------------------------------------------------
    # V4 QUERY: FULL INVESTIGATION
    # ---------------------------------------------------------

    if any(k in q for k in (
        "full investigation", "complete investigation",
        "investigate this project", "full analysis"
    )):
        financial = get_financial_trail_v4(int(work_id))
        timeline = get_project_timeline_v4(int(work_id))
        context = get_mp_context_v4(int(work_id))
        return "\n".join([
            "### Investigation Summary",
            f"• Work ID: {work_id}",
            f"• Project: {desc} – {category}",
            f"• Location: {state}, {constituency}, {house}",
            f"• Risk: {level} (score {score}/100)",
            "",
            "### Evidence Summary",
            *[f"• {reason}" for reason in reasons],
            "",
            "### Financial Trail",
            f"• Reconciliation: {financial.get('reconciliation')}",
            f"• Transactions: {financial.get('transaction_count')}",
            f"• Vendors: {financial.get('vendor_count')}",
            f"• Pending payments: {financial.get('pending_payment_count')}",
            "",
            "### Timeline",
            f"• Recommendation → sanction: {timeline.get('recommendation_to_sanction_days')} days",
            f"• Sanction → completion: {timeline.get('sanction_to_completion_days')} days",
            f"• Status: {timeline.get('status')}",
            "",
            "### MP Context",
            f"• Utilization: {context.get('utilization_percent')}%",
            f"• Completion rate: {context.get('completion_rate_percent')}%",
            f"• Recommended works: {context.get('recommended_works')}",
            f"• Completed works: {context.get('completed_works')}",
            f"• Pending payments: {context.get('pending_payments')}",
            "",
            "### Conclusion",
            "The available indicators support focused human verification. They do not establish fraud or wrongdoing.",
        ])


    # ---------------------------------------------------------
    # QUERY 2: "What should I verify?"
    # ---------------------------------------------------------
    if any(k in q for k in ("what should", "verify", "verification", "check first", "investigator verify")):
        lines = [
            "### Investigation Summary",
            f"• Work ID: {work_id}",
            f"• Project: {desc} – {category}",
            f"• Location: {state}, {constituency}, {house}",
            f"• Risk: {level} (score {score}/100)",
            "",
            "### Recommended Verification Order",
            "1. Review the approved amount and final expenditure records.",
            "2. Verify the project scope/specifications and quantities.",
            "3. Review site inspection reports and available photographic evidence.",
            "4. Check procurement/tender documentation where applicable.",
            "5. Review contractor and supporting records where available.",
            "",
            "### Priority",
            (
                "This project has no major automated risk indicators. "
                "Routine verification should focus on confirming the project scope, "
                "expenditure records and available site evidence."
                if str(level).upper() == "LOW"
                else
                "Prioritize detailed financial, scope, procurement and site verification "
                "because multiple risk indicators require closer investigation."
                if str(level).upper() == "HIGH"
                else
                "Prioritize verification of the amount, project scope and supporting "
                "expenditure records because the project has contextual risk indicators."
            ),
            "",
            "These checks support human investigation; they do not establish fraud or wrongdoing.",
        ]
        return "\n".join(lines)

    # ---------------------------------------------------------
    # QUERY 3: "Compare with similar projects"
    # ---------------------------------------------------------
    if any(k in q for k in ("compare", "similar project", "comparable")):
        try:
            comparison = _v4_compare_projects(int(work_id), limit=5)
            comps = comparison.get("comparisons", []) if isinstance(comparison, dict) else []
        except Exception as exc:
            return f"Comparison data could not be loaded: {exc}"

        ids = [str(c.get("work_id")) for c in comps if c.get("work_id") is not None]
        lines = [
            "### Comparative Analysis",
            f"The contextual comparison returned {len(comps)} comparable projects"
            + (f": {', '.join(ids)}." if ids else "."),
        ]

        if comps:
            same_context = all(
                c.get("state") == state
                and c.get("house") == house
                and c.get("category") == category
                for c in comps
            )
            if same_context:
                lines.append("All returned comparables share the same state, house and category.")
            else:
                lines.append("The returned projects were selected by the contextual comparison engine.")

            lower_count = sum(
                1 for c in comps
                if c.get("target_amount") is not None
                and c.get("amount") is not None
                and float(c["amount"]) < float(c["target_amount"])
            )
            if lower_count == len(comps):
                lines.append("All returned comparables have lower amounts than the target project.")

            same_const = sum(1 for c in comps if c.get("same_constituency"))
            lines.append(
                f"{same_const} of the {len(comps)} returned comparables are from the same constituency."
            )

            lines.append("")
            lines.append("### Investigator Interpretation")
            lines.append(
                "The comparison indicates that the target should receive focused cost-and-scope verification "
                "against the returned contextual projects."
            )
        else:
            lines.append("No comparable projects were returned by the comparison engine.")

        lines += [
            "",
            "The comparison is a contextual screening signal, not proof of irregularity.",
        ]
        return "\n".join(lines)

    # ---------------------------------------------------------
    # GENERAL / CUSTOM QUESTION
    # ---------------------------------------------------------
    lines = [
        "### Investigation Summary",
        f"• Work ID: {work_id}",
        f"• Description: {desc} – {category}",
        f"• Location: {state}, {constituency}, {house}",
        f"• Risk: {level} (score {score}/100)",
        f"• Images: {'Available.' if str(images).lower() in ('true','1','yes') else 'Not available.' if str(images).lower() in ('false','0','no') else 'Status recorded in project data.'}",
        "",
        "### Evidence Available",
    ]
    if reasons:
        lines.extend(f"• {r}" for r in reasons)
    else:
        lines.append("• No specific risk indicators were returned by the risk engine.")

    lines += [
        "",
        "### Recommended Next Step",
        "Review the project's approval, expenditure, scope, procurement and site evidence against the risk indicators above.",
        "",
        "### Conclusion",
        "The available evidence identifies an investigation priority for focused human verification. It does not establish fraud or wrongdoing.",
        "",
        "Note: The Groq AI service is currently rate-limited, so this response was generated from the deterministic investigation evidence.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# V4 FULL INVESTIGATION PLAN
# ---------------------------------------------------------------------------

def _deterministic_fallback(work_id, user_query=""):
    """Stateless fallback dispatcher; full investigations always combine V4 evidence.

    NOTE: the first argument is the Work ID, not the query text — the intent
    must be derived from `user_query`, never from `work_id`.
    """
    _, intent = _route_query_v4(str(user_query))
    if intent == "full":
        reset_agent_trace()
        return _deterministic_full_investigation_v4(work_id)
    return _deterministic_fallback_legacy(work_id, user_query)

def _full_investigation_tool_plan_v4(work_id: int):
    """Execute the complete V4 evidence set in a fixed, stateless order."""
    plan = [
        ("get_project_details", {"work_id": int(work_id)}),
        ("get_financial_trail", {"work_id": int(work_id)}),
        ("get_project_timeline", {"work_id": int(work_id)}),
        ("get_mp_context", {"work_id": int(work_id)}),
        ("compare_projects", {"work_id": int(work_id), "limit": 5}),
    ]
    evidence = []
    for tool_name, args in plan:
        try:
            result = execute_tool(tool_name, args)
            evidence.append((tool_name, result))
        except Exception as exc:
            evidence.append((tool_name, {"error": str(exc)}))
    return evidence


def _classify_investigation_query(query: str) -> str:
    """
    Conservative routing:
      financial -> financial trail only
      risk      -> project/risk evidence
      compare   -> comparable-project evidence
      full      -> all investigation evidence
    """
    q = (query or "").lower()

    financial_terms = (
        "financial", "finance", "financials", "money", "payment", "payments",
        "expenditure", "spent", "spending", "sanctioned", "sanction amount",
        "recommended amount", "final amount", "vendor", "vendors",
        "transaction", "transactions", "reconcile", "reconciliation",
        "paid", "unpaid", "pending payment", "payment status"
    )
    compare_terms = (
        "compare", "comparison", "comparable", "comparables",
        "similar project", "similar projects", "similar works"
    )
    risk_terms = (
        "risk", "risky", "flagged", "flag", "why is", "why was",
        "anomaly", "anomalies", "red flag", "red flags", "priority",
        "investigation priority"
    )
    full_terms = (
        "full investigation", "complete investigation", "investigate fully",
        "full report", "complete report", "investigation of"
    )

    # Explicit full-investigation requests win first.
    if any(term in q for term in full_terms):
        return "full"

    # Explicit comparison requests.
    if any(term in q for term in compare_terms):
        return "compare"

    # Financial-only questions must stay on the financial evidence path.
    if any(term in q for term in financial_terms):
        return "financial"

    if any(term in q for term in risk_terms):
        return "risk"

    # Preserve the existing broad investigation behavior for generic requests.
    return "full"



def _synthesize_financial_only(query: str, financial: dict) -> str:
    if not financial:
        return "I could not retrieve the financial trail for the requested project."

    work_id = financial.get("work_id") or financial.get("Work ID") or _extract_work_id(query)
    def money(v):
        if v is None:
            return "Unavailable"
        try:
            return f"₹{float(v):,.0f}"
        except Exception:
            return str(v)

    lines = [
        "### Financial Trail",
        f"- **Work ID:** {work_id}",
        f"- Recommended amount: {money(financial.get('recommended_amount'))}",
        f"- Sanctioned amount: {money(financial.get('sanctioned_amount'))}",
        f"- Final amount: {money(financial.get('final_amount'))}",
        f"- Total expenditure: {money(financial.get('total_expenditure'))}",
        f"- Transaction count: {financial.get('transaction_count', 'Unavailable')}",
        f"- Vendor count: {financial.get('vendor_count', 'Unavailable')}",
        f"- Pending payment count: {financial.get('pending_payment_count', 'Unavailable')}",
        f"- Successful payment count: {financial.get('successful_payment_count', 'Unavailable')}",
        f"- Reconciliation status: {financial.get('reconciliation', 'Unavailable')}",
    ]

    if financial.get("last_expenditure_date"):
        lines.append(f"- Last expenditure date: {financial['last_expenditure_date']}")

    lines += [
        "",
        "### Interpretation",
        "- These figures describe the recorded financial trail only.",
        "- A reconciled expenditure figure does not by itself establish that the underlying work, rates, procurement, or payments were proper.",
        "- Pending payments should be checked against the underlying payment records and contractual/documentary evidence.",
    ]
    return "\n".join(lines)

def _synthesize_risk_only(project: dict) -> str:
    """Render authoritative V4 risk evidence for the current Work ID."""
    if not isinstance(project, dict) or project.get("error"):
        return "I could not retrieve the risk evidence for the requested project."

    p = project.get("project", {})
    if not isinstance(p, dict):
        p = {}

    wid = project.get("work_id", p.get("work_id", "Unavailable"))

    # Prefer the fields already resolved by _canonical_project_details
    # (which itself uses the scored V4_DF). Only fall back to a direct
    # row lookup if those came back empty for some reason.
    score = project.get("risk_score")
    level = project.get("risk_level")
    reasons = _normalize_reasons(project.get("risk_reasons"))
    peer_median = project.get("peer_median")
    peer_count = project.get("peer_count")
    ratio = project.get("amount_ratio_to_peer_median")
    description = p.get("description")

    if score is None or level is None:
        row = _v4_row(wid)
        if row is not None:
            score = _v4_value(row, "risk_score", "Risk_Score", "Risk Score")
            level = _v4_value(row, "risk_level", "Risk_Level", "Risk Level")
            reasons = _normalize_reasons(
                _v4_value(row, "risk_reasons", "Risk_Reasons", "Risk Reasons")
            )
            peer_median = _v4_value(row, "peer_median", "Peer_Median")
            peer_count = _v4_value(row, "peer_count", "Peer_Count")
            ratio = _v4_value(row, "Amount_Ratio_to_Peer_Median")
            description = _v4_value(row, "Work Description") or description

    if score is None or level is None:
        return (
            "### Risk Assessment\n\n"
            f"- **Work ID:** {wid}\n"
            "- V4 risk evidence could not be retrieved.\n"
            "- No risk score has been inferred or invented."
        )

    lines = [
        "### Investigation Summary",
        f"- **Work ID:** {wid}",
        f"- **Project:** {description or 'Unavailable'}",
        f"- **Risk:** {str(level).upper()} — {float(score):.0f}/100",
        "",
        "### Risk Indicators",
    ]

    if reasons:
        lines.extend(f"- {r}" for r in reasons)
    else:
        lines.append("- No risk indicators were returned by the deterministic V4 risk engine.")

    if peer_median is not None or peer_count is not None or ratio is not None:
        lines += ["", "### Context"]
        if peer_median is not None:
            lines.append(f"- Contextual peer median: ₹{float(peer_median):,.0f}")
        if peer_count is not None:
            lines.append(f"- Contextual peer group size: {int(peer_count)}")
        if ratio is not None:
            lines.append(f"- Final amount / contextual peer median: {float(ratio):.2f}×")

    lines += [
        "",
        "### Interpretation",
        "These are contextual investigation indicators, not proof of fraud, corruption, "
        "overpricing, or wrongdoing.",
        "",
        "### Recommended Verification",
        "- Review the approved scope, quantities and rates against the project records.",
        "- Compare the project with appropriate contextual comparables.",
        "- Verify the supporting financial and documentary evidence before drawing conclusions.",
    ]
    return "\n".join(lines)


def investigate_with_agent(user_query: str):
    # Always classify the actual current user query. Never use an undefined
    # or stale variable from an earlier request.
    route = _classify_investigation_query(user_query)
    work_id = _extract_work_id(user_query)

    # Financial-only route: retrieve ONLY financial evidence.
    if route == "financial" and work_id is not None:
        reset_agent_trace()
        financial = execute_tool("get_financial_trail", {"work_id": work_id})
        LAST_AGENT_TRACE.append({
            "tool": "Deterministic financial evidence synthesis",
            "status": "completed"
        })
        return _synthesize_financial_only(user_query, financial)

    # Risk-only route: retrieve ONLY project/risk evidence.
    if route == "risk" and work_id is not None:
        reset_agent_trace()
        project = execute_tool("get_project_details", {"work_id": work_id})
        LAST_AGENT_TRACE.append({
            "tool": "Deterministic risk evidence synthesis",
            "status": "completed"
        })
        return _synthesize_risk_only(project)

    # FULL_INVESTIGATION_FORCE_V4
    _forced_work_id, _forced_intent = _route_query_v4(user_query)
    if _forced_intent == "full" and _forced_work_id is not None:
        reset_agent_trace()
        return _deterministic_full_investigation_v4(_forced_work_id)

    reset_agent_trace()

    # Deterministic path for explicit comparison requests.
    # The frontend supplies the Work ID in the query, so we can guarantee that
    # compare_projects evidence reaches the final synthesis step.
    normalized_query = user_query.lower()
    explicit_comparison = (
        "compare_projects tool" in normalized_query
        or "compare with similar projects" in normalized_query
        or "compare the project with similar projects" in normalized_query
        or route == "compare"
    )

    if explicit_comparison:
        work_id_match = re.search(r"work\s*id\s*(?:is|:)?\s*(\d+)", normalized_query)
        comparison_work_id = int(work_id_match.group(1)) if work_id_match else work_id
        if comparison_work_id is not None:

            # Retrieve authoritative project/risk evidence first.
            # Execution order: project details -> comparison -> synthesis.
            risk_result = execute_tool(
                "get_project_details",
                {"work_id": comparison_work_id}
            )

            direct_result = execute_tool(
                "compare_projects",
                {"work_id": comparison_work_id, "limit": 5}
            )

            # V4 is the canonical source for all comparison amounts.
            # Exact values are retained in tool evidence so the model cannot
            # accidentally substitute the legacy V3 amount.
            target = direct_result.get("target_project", {})
            comparisons = direct_result.get("comparisons", [])

            qualitative_comparisons = []
            for item in comparisons:
                qualitative_comparisons.append({
                    "work_id": item.get("work_id"),
                    "amount": item.get("amount"),
                    "amount_difference": item.get("amount_difference"),
                    "amount_difference_percent_vs_comparable": item.get("amount_difference_percent_vs_comparable"),
                    "similarity_score": item.get("similarity_score"),
                    "description": item.get("description"),
                    "constituency": item.get("constituency"),
                    "same_state": item.get("same_state"),
                    "same_house": item.get("same_house"),
                    "same_category": item.get("same_category"),
                    "same_constituency": item.get("same_constituency"),
                })

            risk_reasons = _normalize_reasons(risk_result.get("risk_reasons", []))

            direct_evidence = json.dumps({
                "risk_evidence": {
                    "tool": "get_project_details",
                    "work_id": comparison_work_id,
                    "risk_score": risk_result.get("risk_score"),
                    "risk_level": risk_result.get("risk_level"),
                    "risk_reasons": risk_reasons,
                    "has_images": risk_result.get("has_images")
                },
                "comparison_evidence": {
                    "tool": "compare_projects",
                    "arguments": {"work_id": comparison_work_id, "limit": 5},
                },
                "target_context": {
                    "work_id": target.get("work_id"),
                    "description": target.get("description"),
                    "category": target.get("category"),
                    "state": target.get("state"),
                    "house": target.get("house"),
                    "constituency": target.get("constituency"),
                    "risk_level": target.get("risk_level")
                },
                "comparison_count": len(qualitative_comparisons),
                "comparisons": qualitative_comparisons,
                "financial_values_redacted": False
            }, indent=2, default=str)

            comparison_messages = [
                {
                    "role": "system",
                    "content": (
                        SYSTEM_PROMPT
                        + "\n\n"
                        + "IMPORTANT FINAL RESPONSE RULE:\n"
                        + "Do NOT call any tools in this step.\n"
                        + "Use ONLY the evidence supplied below.\n"
                        + "Because compare_projects evidence is supplied, you MUST discuss "
                          "the returned comparable projects and must NOT say that no "
                          "comparable project data were returned.\n"
                        + "The exact financial values have been intentionally redacted from "
                          "the evidence supplied to you. Do NOT invent, estimate, calculate, "
                          "or reproduce any monetary amount or amount-difference percentage.\n"
                        + "Do NOT create a comparison table. In the Comparative Analysis section, "
                          "describe the cost relationship qualitatively only, such as 'the target "
                          "is substantially higher than all returned comparables'.\n"
                        + "The deterministic dashboard/tool output is the ONLY source of exact "
                          "financial values.\n"
                         + "The risk_evidence.risk_reasons list is authoritative. You MUST use every "
                           "returned risk reason in the Evidence Summary. If the list is non-empty, "
                           "you MUST NOT say that no specific risk reasons or risk indicators were returned. "
                           "Do not omit, replace, or contradict the supplied risk reasons.\n"
                    )
                },
                {"role": "user", "content": user_query},
                {
                    "role": "user",
                    "content": (
                        "EVIDENCE RETURNED BY APPROVED INVESTIGATION TOOL:\n\n"
                        + direct_evidence
                        + "\n\nProduce the final investigation brief now. "
                          "Discuss the supplied comparisons using only this evidence."
                    )
                }
            ]

            try:
                direct_final = client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=comparison_messages,
                    temperature=0.0,
                    reasoning_effort="low",
                    include_reasoning=False,
                    max_completion_tokens=1200
                )
                LAST_AGENT_TRACE.append({
                    "tool": "AI synthesis",
                    "status": "completed"
                })
                return direct_final.choices[0].message.content
            except Exception as exc:
                if exc.__class__.__name__ == "RateLimitError" or "rate limit" in str(exc).lower():
                    return _fallback_with_trace(comparison_work_id, user_query)
                raise

    explicit_work_id = _extract_work_id(user_query)

    grounding_note = ""
    if explicit_work_id is not None:
        grounding_note = (
            f"\n\nAUTHORITATIVE WORK ID FOR THIS REQUEST: {explicit_work_id}. "
            "If a tool call is needed for the project, use this exact Work ID "
            "unless the user explicitly asks about a different Work ID."
        )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT + grounding_note
        },
        {
            "role": "user",
            "content": user_query
        }
    ]

    # =====================================================
    # FIRST GROQ CALL
    # =====================================================

    if "compare_projects tool" in normalized_query or "compare with similar projects" in normalized_query:
        selected_tool_choice = {
            "type": "function",
            "function": {"name": "compare_projects"}
        }
    elif "get_project_details tool" in normalized_query:
        selected_tool_choice = {
            "type": "function",
            "function": {"name": "get_project_details"}
        }
    else:
        selected_tool_choice = "auto"

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            tools=tools,
            tool_choice=selected_tool_choice,
            temperature=0.2,
            reasoning_effort="low",
            include_reasoning=False,
            max_completion_tokens=1200
        )
    except Exception as exc:
        if exc.__class__.__name__ == "RateLimitError" or "rate limit" in str(exc).lower():
            match = re.search(r"\b(?:work\s*id\s*)?(\d{4,})\b", user_query, re.I)
            return _fallback_with_trace(int(match.group(1)), user_query) if match else "AI investigation is temporarily unavailable because the Groq daily token limit has been reached."
        raise

    assistant_message = response.choices[0].message

    # =====================================================
    # NO TOOL CALL
    # =====================================================

    if not assistant_message.tool_calls:
        return assistant_message.content

    # =====================================================
    # EXECUTE TOOL CALLS
    # =====================================================

    tool_results = []

    for tool_call in assistant_message.tool_calls:

        tool_name = tool_call.function.name

        try:
            arguments = json.loads(
                tool_call.function.arguments
            )
        except json.JSONDecodeError:
            arguments = {}

        tool_result = execute_tool(
            tool_name,
            arguments
        )

        tool_results.append({
            "tool": tool_name,
            "arguments": arguments,
            "result": tool_result
        })

    # =====================================================
    # BUILD EVIDENCE FOR FINAL AI RESPONSE
    # =====================================================

    evidence_text = json.dumps(
        tool_results,
        indent=2,
        default=str
    )

    final_messages = [
        {
            "role": "system",
            "content": (
                SYSTEM_PROMPT
                + "\n\n"
                + "IMPORTANT FINAL RESPONSE RULE:\n"
                + "Do NOT call any tools in this step.\n"
                + "Use ONLY the evidence supplied below.\n"
                + "Synthesize the final investigation brief from "
                  "that evidence.\n"
                + "NUMERIC ACCURACY RULE: Copy Work IDs, amounts, scores, "
                  "percentages, and similarity values exactly from the evidence. "
                  "Do not recalculate or alter them. Before answering, verify "
                  "that every important number matches the evidence.\n"
                + "COMPARISON CONSISTENCY RULE: If compare_projects evidence is supplied "
                  "and contains comparisons, do NOT say that no comparable project data "
                  "were returned. Discuss the supplied comparisons using only their returned values.\n"
            )
        },

        {
            "role": "user",
            "content": user_query
        },

        {
            "role": "user",
            "content": (
                "EVIDENCE RETURNED BY APPROVED INVESTIGATION TOOLS:\n\n"
                + evidence_text
                + "\n\n"
                "Now produce the final investigation brief. "
                "Do not request or call another tool."
            )
        }
    ]

    # =====================================================
    # FINAL GROQ CALL — SYNTHESIS ONLY
    # =====================================================

    try:
        final_response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=final_messages,
            temperature=0.0,
            reasoning_effort="low",
            include_reasoning=False,
            max_completion_tokens=1200
        )
        LAST_AGENT_TRACE.append({
            "tool": "AI synthesis",
            "status": "completed"
        })
        return final_response.choices[0].message.content
    except Exception as exc:
        if exc.__class__.__name__ == "RateLimitError" or "rate limit" in str(exc).lower():
            match = re.search(r"\b(?:work\s*id\s*)?(\d{4,})\b", user_query, re.I)
            return _fallback_with_trace(int(match.group(1)), user_query) if match else "AI investigation is temporarily unavailable because the Groq daily token limit has been reached."
        raise

    # =====================================================
    # NO TOOL CALL
    # =====================================================

    return assistant_message.content