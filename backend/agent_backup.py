from groq import Groq
from dotenv import load_dotenv
import os
import json
import re

from tools import (
    get_project_details,
    search_projects,
    compare_projects
)


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

You may use more than one tool when necessary.

Never replace tool evidence with guesses.


=========================================================
4. SPECIFIC WORK ID
=========================================================

When a Work ID is provided:

1. Retrieve the project details using get_project_details.
2. Use compare_projects if the user asks about unusualness,
   similarity, or cost comparison.
3. Use search_projects only when broader filtering or discovery
   is required.

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
    }
]


# =========================================================
# TOOL EXECUTOR
# =========================================================

def execute_tool(tool_name, arguments):

    # -----------------------------------------------------
    # GET PROJECT DETAILS
    # -----------------------------------------------------

    if tool_name == "get_project_details":

        return get_project_details(
            arguments["work_id"]
        )


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

        return compare_projects(
            work_id=arguments["work_id"],
            limit=arguments.get("limit", 5)
        )


    # -----------------------------------------------------
    # UNKNOWN TOOL
    # -----------------------------------------------------

    return {
        "error": "Unknown tool"
    }


# =========================================================
# AI INVESTIGATION AGENT
# =========================================================
# =========================================================
# AI INVESTIGATION AGENT
# =========================================================

def investigate_with_agent(user_query: str):

    # Deterministic path for explicit comparison requests.
    # The frontend supplies the Work ID in the query, so we can guarantee that
    # compare_projects evidence reaches the final synthesis step.
    normalized_query = user_query.lower()
    explicit_comparison = (
        "compare_projects tool" in normalized_query
        or "compare with similar projects" in normalized_query
        or "compare the project with similar projects" in normalized_query
    )

    if explicit_comparison:
        work_id_match = re.search(r"work\s*id\s*(?:is|:)?\s*(\d+)", normalized_query)
        if work_id_match:
            comparison_work_id = int(work_id_match.group(1))
            direct_result = execute_tool(
                "compare_projects",
                {"work_id": comparison_work_id, "limit": 5}
            )

            # IMPORTANT: exact financial values are deliberately NOT passed to the
            # LLM for comparison synthesis. The deterministic comparison endpoint
            # remains the source of truth for the dashboard table.
            target = direct_result.get("target_project", {})
            comparisons = direct_result.get("comparisons", [])

            qualitative_comparisons = []
            for item in comparisons:
                qualitative_comparisons.append({
                    "work_id": item.get("work_id"),
                    "constituency": item.get("constituency"),
                    "same_state": item.get("same_state"),
                    "same_house": item.get("same_house"),
                    "same_category": item.get("same_category"),
                    "same_constituency": item.get("same_constituency"),
                    "similarity_score_available": item.get("similarity_score") is not None,
                    "comparable_amount_is_lower_than_target": (
                        item.get("amount") is not None
                        and target.get("amount") is not None
                        and float(item.get("amount")) < float(target.get("amount"))
                    )
                })

            direct_evidence = json.dumps({
                "tool": "compare_projects",
                "arguments": {"work_id": comparison_work_id, "limit": 5},
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
                "financial_values_redacted": True
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

            direct_final = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=comparison_messages,
                temperature=0.0,
                reasoning_effort="low",
                include_reasoning=False,
                max_completion_tokens=2000
            )

            return direct_final.choices[0].message.content

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": user_query
        }
    ]

    # =====================================================
    # FIRST GROQ CALL
    # =====================================================

    # Force the comparison tool for explicit comparison requests.
    normalized_query = user_query.lower()

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

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=messages,
        tools=tools,
        tool_choice=selected_tool_choice,
        temperature=0.2,
        reasoning_effort="low",
        include_reasoning=False,
        max_completion_tokens=2000
    )

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

    final_response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=final_messages,
        temperature=0.0,
        reasoning_effort="low",
        include_reasoning=False,
        max_completion_tokens=2000
    )

    return (
        final_response
        .choices[0]
        .message
        .content
    )

    # =====================================================
    # NO TOOL CALL
    # =====================================================

    return assistant_message.content