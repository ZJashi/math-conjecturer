"""Field Expert nodes for Phase 2 — two-round expert-driven proposal generation.

Round 1 (R1): each expert conducts an independent deep literature survey. No proposals.
Round 2 (R2): each expert writes one full research proposal, informed by all R1 surveys.
"""

import json
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import (
    FIELD_EXPERT_SYSTEM,
    FIELD_EXPERT_R1_PROMPT,
    FIELD_EXPERT_R2_PROMPT,
    FIELD_EXPERT_R2_REVISION_PROMPT,
)
from schema.phase2 import Phase2State, ExpertSurveyResult, ExpertProposalResult
from ._common import PAPERS_DIR, invoke_with_structured_output, get_latest_r2_proposals, get_latest_r2_critiques


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_agenda(state: Phase2State) -> str:
    agenda = state.get("agenda", [])
    return "\n".join(f"{i}. {d}" for i, d in enumerate(agenda, 1)) if agenda else "No agenda available."


def _format_survey_as_text(survey: dict) -> str:
    """Format an R1 survey dict as readable text for R2 prompts."""
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
        "SETTLED CLAIMS (FORBIDDEN — do not propose anything on this list):",
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


def _save_expert_output(state: Phase2State, expert_index: int, filename: str, data: dict) -> None:
    arxiv_id = state.get("arxiv_id")
    if not arxiv_id:
        return
    experts_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / "4b_experts"
    experts_dir.mkdir(parents=True, exist_ok=True)
    path = experts_dir / filename
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  > Saved to {path}")


# ---------------------------------------------------------------------------
# Round 1: Deep literature survey — one-shot, no revision loop
# ---------------------------------------------------------------------------

def _field_expert_r1(state: Phase2State, expert_index: int) -> Dict[str, Any]:
    """Round 1: independent deep literature survey. No proposals generated."""
    subfields = state.get("subfields", [])
    if expert_index >= len(subfields):
        print(f"  WARNING: No subfield at index {expert_index}, skipping R1.")
        return {"expert_surveys_r1": []}

    subfield = subfields[expert_index]
    print(f"--- Field Expert R1 [{subfield}]: Conducting literature survey ---")

    prompt = ChatPromptTemplate.from_messages([
        ("system", FIELD_EXPERT_SYSTEM),
        ("human", FIELD_EXPERT_R1_PROMPT),
    ])

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=ExpertSurveyResult,
        inputs={
            "subfield": subfield,
            "paper_summary": state["summary"],
            "mechanisms": state["mechanism"],
            "agenda": _format_agenda(state),
        },
        temperature=0.8,
    )

    survey_dict = {
        "expert_index": expert_index,
        "subfield": subfield,
        "round": 1,
        "paper_connections": result.paper_connections,
        "state_of_the_art": result.state_of_the_art,
        "landmark_results": result.landmark_results,
        "settled_claims": result.settled_claims,
        "open_territory": result.open_territory,
        "available_techniques": result.available_techniques,
        "cross_field_bridges": result.cross_field_bridges,
    }

    print(f"  [{subfield}] R1 survey complete: "
          f"{len(result.landmark_results)} landmark results, "
          f"{len(result.available_techniques)} techniques.")

    _save_expert_output(state, expert_index, f"expert_{expert_index}_r1_survey.json", survey_dict)
    return {"expert_surveys_r1": [survey_dict]}


# ---------------------------------------------------------------------------
# R2 sync barrier
# ---------------------------------------------------------------------------

def r2_sync_node(state: Phase2State) -> Dict[str, Any]:
    """Barrier node: waits for all R1 surveys to complete, then signals R2 fan-out."""
    surveys = state.get("expert_surveys_r1", [])
    print(f"--- R2 Sync: {len(surveys)} R1 surveys ready — proceeding to R2 proposals ---")
    return {}


# ---------------------------------------------------------------------------
# R2 proposals sync barrier
# ---------------------------------------------------------------------------

def r2_proposals_sync_node(state: Phase2State) -> Dict[str, Any]:
    """Barrier node: waits for all R2 proposals to complete, then signals R2 critics fan-out."""
    proposals = state.get("expert_proposals_r2", [])
    print(f"--- R2 Proposals Sync: {len(proposals)} R2 proposals ready — proceeding to critics ---")
    return {}


# ---------------------------------------------------------------------------
# Round 2: Full proposal writing — informed by all R1 surveys (with revision support)
# ---------------------------------------------------------------------------

def _format_proposals_as_text(proposals: list) -> str:
    """Format a list of proposal dicts as numbered text."""
    parts = []
    for i, p in enumerate(proposals):
        parts.append(f"Proposal {i + 1}:\n"
                     f"Title: {p.get('title', 'Untitled')}\n"
                     f"Problem Statement: {p.get('problem_statement', '')}\n"
                     f"Motivation: {p.get('motivation', '')}\n"
                     f"Connections: {p.get('connections', '')}\n"
                     f"Potential Impact: {p.get('potential_impact', '')}")
    return "\n\n".join(parts)


def _format_critic_feedback(critique: dict) -> str:
    """Format critique dict as readable text for the revision prompt."""
    verdicts = critique.get("verdicts", [])
    lines = [f"Overall approved: {critique.get('overall_approved', False)}",
             f"Summary: {critique.get('summary', '')}",
             ""]
    for v in verdicts:
        idx = v.get("proposal_index", "?")
        approved = v.get("approved", False)
        lines.append(f"Proposal {idx} — {'APPROVED' if approved else 'REJECTED'}")
        if v.get("blocking_issues"):
            lines.append("  Blocking issues:")
            for issue in v["blocking_issues"]:
                lines.append(f"    - {issue}")
        if v.get("suggestions"):
            lines.append("  Suggestions:")
            for s in v["suggestions"]:
                lines.append(f"    - {s}")
        lines.append("")
    return "\n".join(lines)


def _field_expert_r2(state: Phase2State, expert_index: int) -> Dict[str, Any]:
    """Round 2: each expert writes two full proposals, with revision loop support."""
    subfields = state.get("subfields", [])
    if expert_index >= len(subfields):
        print(f"  WARNING: No subfield at index {expert_index}, skipping R2.")
        return {"expert_proposals_r2": []}

    subfield = subfields[expert_index]
    all_surveys = state.get("expert_surveys_r1", [])

    # Split: my survey vs other experts' surveys
    my_r1 = next(
        (s for s in all_surveys if s.get("expert_index") == expert_index),
        None,
    )
    others_r1 = [s for s in all_surveys if s.get("expert_index") != expert_index]

    my_r1_text = _format_survey_as_text(my_r1) if my_r1 else "No Round 1 survey found for this expert."
    others_text = "\n\n---\n\n".join(
        _format_survey_as_text(s) for s in others_r1
    ) if others_r1 else "No other expert surveys available."

    # Detect revision mode: check latest critique for this expert
    latest_critiques = get_latest_r2_critiques(state.get("expert_r2_critiques", []))
    my_critique = next(
        (c for c in latest_critiques if c.get("expert_index") == expert_index),
        None,
    )

    is_revision = my_critique is not None and not my_critique.get("overall_approved", True)

    # If already approved in critique, re-emit existing proposals unchanged
    if my_critique is not None and my_critique.get("overall_approved", False):
        latest_proposals = get_latest_r2_proposals(state.get("expert_proposals_r2", []))
        existing = next(
            (p for p in latest_proposals if p.get("expert_index") == expert_index),
            None,
        )
        if existing:
            print(f"--- Field Expert R2 [{subfield}]: Already approved — re-emitting proposals ---")
            return {"expert_proposals_r2": [existing]}

    base_inputs = {
        "subfield": subfield,
        "paper_summary": state["summary"],
        "mechanisms": state["mechanism"],
        "agenda": _format_agenda(state),
        "my_r1_survey": my_r1_text,
        "other_r1_surveys": others_text,
    }

    if is_revision:
        # Find previous proposals for this expert
        latest_proposals = get_latest_r2_proposals(state.get("expert_proposals_r2", []))
        prev_proposal_entry = next(
            (p for p in latest_proposals if p.get("expert_index") == expert_index),
            None,
        )
        prev_proposals_list = prev_proposal_entry.get("proposals", []) if prev_proposal_entry else []
        prev_text = _format_proposals_as_text(prev_proposals_list)
        critic_text = _format_critic_feedback(my_critique)

        print(f"--- Field Expert R2 [{subfield}]: Revising proposals (critique received) ---")

        prompt = ChatPromptTemplate.from_messages([
            ("system", FIELD_EXPERT_SYSTEM),
            ("human", FIELD_EXPERT_R2_REVISION_PROMPT),
        ])
        inputs = {**base_inputs, "previous_proposals": prev_text, "critic_feedback": critic_text}
    else:
        print(f"--- Field Expert R2 [{subfield}]: Writing proposals "
              f"(informed by {len(others_r1)} other surveys) ---")

        prompt = ChatPromptTemplate.from_messages([
            ("system", FIELD_EXPERT_SYSTEM),
            ("human", FIELD_EXPERT_R2_PROMPT),
        ])
        inputs = base_inputs

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=ExpertProposalResult,
        inputs=inputs,
        temperature=0.7,
    )

    proposal_dict = {
        "expert_index": expert_index,
        "subfield": subfield,
        "round": 2,
        "proposals": [
            {
                "title": p.title,
                "problem_statement": p.problem_statement,
                "motivation": p.motivation,
                "connections": p.connections,
                "potential_impact": p.potential_impact,
            }
            for p in result.proposals
        ],
    }

    titles = [p.title[:60] for p in result.proposals]
    print(f"  [{subfield}] R2 proposals complete: {titles}")

    _save_expert_output(state, expert_index, f"expert_{expert_index}_r2_proposal.json", proposal_dict)
    return {"expert_proposals_r2": [proposal_dict]}


# ---------------------------------------------------------------------------
# Round 1 node wrappers
# ---------------------------------------------------------------------------

def field_expert_0_r1_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r1(state, 0)

def field_expert_1_r1_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r1(state, 1)

def field_expert_2_r1_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r1(state, 2)

def field_expert_3_r1_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r1(state, 3)


# ---------------------------------------------------------------------------
# R2 critic aggregate node — computes expert_r2_approved and increments iteration
# ---------------------------------------------------------------------------

def r2_critic_aggregate_node(state: Phase2State) -> Dict[str, Any]:
    """
    After critics fan-in: compute overall approval and manage iteration counter.
    Forces approval if max_iterations reached.
    """
    latest_critiques = get_latest_r2_critiques(state.get("expert_r2_critiques", []))
    all_approved = all(c.get("overall_approved", False) for c in latest_critiques)

    current_iteration = state.get("expert_r2_iteration", 0)
    new_iteration = current_iteration + 1
    max_iterations = state.get("expert_r2_max_iterations", 2)

    force_approved = new_iteration >= max_iterations

    if force_approved and not all_approved:
        print(f"--- R2 Critic Aggregate: iteration {new_iteration}/{max_iterations} — "
              f"forcing approval (max iterations reached) ---")

    final_approved = all_approved or force_approved

    not_approved = [c["expert_index"] for c in latest_critiques if not c.get("overall_approved", False)]
    print(f"--- R2 Critic Aggregate: iteration={new_iteration}, "
          f"all_approved={all_approved}, force={force_approved} "
          f"(experts needing revision: {not_approved}) ---")

    return {
        "expert_r2_approved": final_approved,
        "expert_r2_iteration": new_iteration,
    }


# ---------------------------------------------------------------------------
# R2 revision dispatch node — barrier before looping back to R2 experts
# ---------------------------------------------------------------------------

def expert_r2_revision_dispatch_node(state: Phase2State) -> Dict[str, Any]:
    """No-op barrier: signals which experts need revision before looping back."""
    latest_critiques = get_latest_r2_critiques(state.get("expert_r2_critiques", []))
    needs_revision = [c["expert_index"] for c in latest_critiques
                      if not c.get("overall_approved", True)]
    print(f"--- R2 Revision Dispatch: experts {needs_revision} need revision ---")
    return {}


# ---------------------------------------------------------------------------
# Round 2 node wrappers
# ---------------------------------------------------------------------------

def field_expert_0_r2_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r2(state, 0)

def field_expert_1_r2_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r2(state, 1)

def field_expert_2_r2_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r2(state, 2)

def field_expert_3_r2_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r2(state, 3)
