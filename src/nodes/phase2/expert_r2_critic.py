"""Expert R2 Critic nodes for Phase 2 — one critic per expert's two R2 proposals."""

import json
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import EXPERT_R2_CRITIC_SYSTEM, EXPERT_R2_CRITIC_PROMPT
from schema.phase2 import Phase2State, ExpertR2CritiqueResult
from ._common import PAPERS_DIR, invoke_with_structured_output, get_latest_r2_proposals


def _format_survey_as_text(survey: dict) -> str:
    """Format an R1 survey dict as readable text for the critic."""
    settled = survey.get("settled_claims", [])
    lines = [
        f"**Subfield: {survey.get('subfield', 'Unknown')}**",
        "",
        f"Paper Connections: {survey.get('paper_connections', '')}",
        "",
        f"State of the Art: {survey.get('state_of_the_art', '')}",
        "",
        "Landmark Results:",
        *[f"  - {r}" for r in survey.get("landmark_results", [])],
        "",
        "SETTLED CLAIMS (automatic rejection if proposed):",
        *(
            [f"  - {s}" for s in settled]
            if settled else ["  (none identified)"]
        ),
        "",
        f"Open Territory: {survey.get('open_territory', '')}",
        "",
        "Available Techniques:",
        *[f"  - {t}" for t in survey.get("available_techniques", [])],
        "",
        f"Cross-Field Bridges: {survey.get('cross_field_bridges', '')}",
    ]
    return "\n".join(lines)


def _format_proposals_as_text(proposals: list) -> str:
    """Format a list of proposal dicts with Proposal 1/2 headers for the critic."""
    parts = []
    for i, p in enumerate(proposals):
        lines = [
            f"Proposal {i + 1}:",
            f"Title: {p.get('title', 'Untitled')}",
            "",
            "Problem Statement:",
            p.get("problem_statement", ""),
            "",
            "Motivation:",
            p.get("motivation", ""),
            "",
            "Connections:",
            p.get("connections", ""),
            "",
            "Potential Impact:",
            p.get("potential_impact", ""),
        ]
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


def _expert_r2_critic_node(state: Phase2State, expert_index: int) -> Dict[str, Any]:
    """Evaluate one expert's two R2 proposals using their own R1 survey as the novelty benchmark."""
    subfields = state.get("subfields", [])
    subfield = subfields[expert_index] if expert_index < len(subfields) else f"expert_{expert_index}"

    # Find this expert's R1 survey and latest R2 proposals
    r1_survey = next(
        (s for s in state.get("expert_surveys_r1", []) if s.get("expert_index") == expert_index),
        None,
    )
    latest_proposals = get_latest_r2_proposals(state.get("expert_proposals_r2", []))
    r2_proposal = next(
        (p for p in latest_proposals if p.get("expert_index") == expert_index),
        None,
    )

    # Auto-reject if either is missing
    if r1_survey is None or r2_proposal is None:
        missing = []
        if r1_survey is None:
            missing.append("R1 survey")
        if r2_proposal is None:
            missing.append("R2 proposal")
        msg = f"Missing {' and '.join(missing)} for expert {expert_index} ({subfield})."
        print(f"  WARNING: {msg} Auto-rejecting.")
        critique_dict = {
            "expert_index": expert_index,
            "subfield": subfield,
            "verdicts": [
                {"proposal_index": 0, "approved": False,
                 "blocking_issues": [f"Cannot evaluate: {msg}"], "suggestions": []},
                {"proposal_index": 1, "approved": False,
                 "blocking_issues": [f"Cannot evaluate: {msg}"], "suggestions": []},
            ],
            "overall_approved": False,
            "summary": f"Auto-rejected because {msg} was not available for review.",
        }
        _save_critique(state, expert_index, critique_dict)
        return {"expert_r2_critiques": [critique_dict]}

    proposals_list = r2_proposal.get("proposals", [])
    print(f"--- Expert R2 Critic [{subfield}]: Evaluating {len(proposals_list)} proposals ---")

    r1_text = _format_survey_as_text(r1_survey)
    proposals_text = _format_proposals_as_text(proposals_list)

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXPERT_R2_CRITIC_SYSTEM),
        ("human", EXPERT_R2_CRITIC_PROMPT),
    ])

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=ExpertR2CritiqueResult,
        inputs={
            "subfield": subfield,
            "r1_survey": r1_text,
            "proposal": proposals_text,
            "paper_summary": state["summary"],
            "mechanisms": state["mechanism"],
        },
        temperature=0.3,
    )

    critique_dict = {
        "expert_index": expert_index,
        "subfield": subfield,
        "verdicts": [
            {
                "proposal_index": v.proposal_index,
                "approved": v.approved,
                "blocking_issues": v.blocking_issues,
                "suggestions": v.suggestions,
            }
            for v in result.verdicts
        ],
        "overall_approved": result.overall_approved,
        "summary": result.summary,
    }

    verdict = "APPROVED" if result.overall_approved else "REJECTED"
    print(f"  [{subfield}] Critique: {verdict} — {result.summary[:100]}")

    _save_critique(state, expert_index, critique_dict)
    return {"expert_r2_critiques": [critique_dict]}


def _save_critique(state: Phase2State, expert_index: int, data: dict) -> None:
    arxiv_id = state.get("arxiv_id")
    if not arxiv_id:
        return
    experts_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / "4b_experts"
    experts_dir.mkdir(parents=True, exist_ok=True)
    path = experts_dir / f"expert_{expert_index}_r2_critique.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  > Saved to {path}")


# ---------------------------------------------------------------------------
# Node wrappers (one per expert)
# ---------------------------------------------------------------------------

def expert_r2_critic_0_node(state: Phase2State) -> Dict[str, Any]:
    return _expert_r2_critic_node(state, 0)

def expert_r2_critic_1_node(state: Phase2State) -> Dict[str, Any]:
    return _expert_r2_critic_node(state, 1)

def expert_r2_critic_2_node(state: Phase2State) -> Dict[str, Any]:
    return _expert_r2_critic_node(state, 2)

def expert_r2_critic_3_node(state: Phase2State) -> Dict[str, Any]:
    return _expert_r2_critic_node(state, 3)
