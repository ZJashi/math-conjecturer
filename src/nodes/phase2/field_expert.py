"""Field Expert nodes for Phase 2 — two-round expert-driven proposal generation."""

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
from ._common import (
    invoke_with_structured_output, get_latest_r2_proposals, get_latest_r2_critiques,
    format_survey_as_text, format_proposals_as_text, save_json,
)

_EXPERTS_DIR = "step4_open_problems/4b_experts"


def _format_agenda(state: Phase2State) -> str:
    agenda = state.get("agenda", [])
    return "\n".join(f"{i}. {d}" for i, d in enumerate(agenda, 1)) if agenda else "No agenda available."


def _format_critic_feedback(critique: dict) -> str:
    verdicts = critique.get("verdicts", [])
    lines = [f"Overall approved: {critique.get('overall_approved', False)}",
             f"Summary: {critique.get('summary', '')}", ""]
    for v in verdicts:
        lines.append(f"Proposal {v.get('proposal_index', '?')} — {'APPROVED' if v.get('approved') else 'REJECTED'}")
        if v.get("blocking_issues"):
            lines += ["  Blocking issues:"] + [f"    - {i}" for i in v["blocking_issues"]]
        if v.get("suggestions"):
            lines += ["  Suggestions:"] + [f"    - {s}" for s in v["suggestions"]]
        lines.append("")
    return "\n".join(lines)


def _field_expert_r1(state: Phase2State, expert_index: int) -> Dict[str, Any]:
    subfields = state.get("subfields", [])
    if expert_index >= len(subfields):
        print(f"  WARNING: No subfield at index {expert_index}, skipping R1.")
        return {"expert_surveys_r1": []}

    subfield = subfields[expert_index]
    print(f"--- Field Expert R1 [{subfield}]: Conducting literature survey ---")

    prompt = ChatPromptTemplate.from_messages([("system", FIELD_EXPERT_SYSTEM), ("human", FIELD_EXPERT_R1_PROMPT)])
    result = invoke_with_structured_output(
        prompt=prompt, output_class=ExpertSurveyResult,
        inputs={"subfield": subfield, "paper_summary": state["summary"],
                "mechanisms": state["mechanism"], "agenda": _format_agenda(state)},
        temperature=0.8,
    )

    survey_dict = {
        "expert_index": expert_index, "subfield": subfield, "round": 1,
        "paper_connections": result.paper_connections,
        "state_of_the_art": result.state_of_the_art,
        "landmark_results": result.landmark_results,
        "settled_claims": result.settled_claims,
        "open_territory": result.open_territory,
        "available_techniques": result.available_techniques,
        "cross_field_bridges": result.cross_field_bridges,
    }
    print(f"  [{subfield}] R1 complete: {len(result.landmark_results)} landmark results, "
          f"{len(result.available_techniques)} techniques.")
    save_json(state, _EXPERTS_DIR, f"expert_{expert_index}_r1_survey.json", survey_dict)
    return {"expert_surveys_r1": [survey_dict]}


def r2_sync_node(state: Phase2State) -> Dict[str, Any]:
    print(f"--- R2 Sync: {len(state.get('expert_surveys_r1', []))} R1 surveys ready ---")
    return {}


def r2_proposals_sync_node(state: Phase2State) -> Dict[str, Any]:
    print(f"--- R2 Proposals Sync: {len(state.get('expert_proposals_r2', []))} proposals ready ---")
    return {}


def _field_expert_r2(state: Phase2State, expert_index: int) -> Dict[str, Any]:
    subfields = state.get("subfields", [])
    if expert_index >= len(subfields):
        print(f"  WARNING: No subfield at index {expert_index}, skipping R2.")
        return {"expert_proposals_r2": []}

    subfield = subfields[expert_index]
    all_surveys = state.get("expert_surveys_r1", [])
    my_r1 = next((s for s in all_surveys if s.get("expert_index") == expert_index), None)
    others_r1 = [s for s in all_surveys if s.get("expert_index") != expert_index]

    my_r1_text = format_survey_as_text(my_r1) if my_r1 else "No Round 1 survey found for this expert."
    others_text = "\n\n---\n\n".join(format_survey_as_text(s) for s in others_r1) if others_r1 else "No other expert surveys available."

    latest_critiques = get_latest_r2_critiques(state.get("expert_r2_critiques", []))
    my_critique = next((c for c in latest_critiques if c.get("expert_index") == expert_index), None)

    # Re-emit unchanged if already approved
    if my_critique and my_critique.get("overall_approved", False):
        latest_proposals = get_latest_r2_proposals(state.get("expert_proposals_r2", []))
        existing = next((p for p in latest_proposals if p.get("expert_index") == expert_index), None)
        if existing:
            print(f"--- Field Expert R2 [{subfield}]: Already approved — re-emitting ---")
            return {"expert_proposals_r2": [existing]}

    base_inputs = {
        "subfield": subfield, "paper_summary": state["summary"],
        "mechanisms": state["mechanism"], "agenda": _format_agenda(state),
        "my_r1_survey": my_r1_text, "other_r1_surveys": others_text,
    }

    is_revision = my_critique is not None and not my_critique.get("overall_approved", True)
    if is_revision:
        latest_proposals = get_latest_r2_proposals(state.get("expert_proposals_r2", []))
        prev_entry = next((p for p in latest_proposals if p.get("expert_index") == expert_index), None)
        prev_text = format_proposals_as_text(prev_entry.get("proposals", []) if prev_entry else [])
        print(f"--- Field Expert R2 [{subfield}]: Revising proposals ---")
        prompt = ChatPromptTemplate.from_messages([("system", FIELD_EXPERT_SYSTEM), ("human", FIELD_EXPERT_R2_REVISION_PROMPT)])
        inputs = {**base_inputs, "previous_proposals": prev_text, "critic_feedback": _format_critic_feedback(my_critique)}
    else:
        print(f"--- Field Expert R2 [{subfield}]: Writing proposals (informed by {len(others_r1)} surveys) ---")
        prompt = ChatPromptTemplate.from_messages([("system", FIELD_EXPERT_SYSTEM), ("human", FIELD_EXPERT_R2_PROMPT)])
        inputs = base_inputs

    result = invoke_with_structured_output(prompt=prompt, output_class=ExpertProposalResult, inputs=inputs, temperature=0.7)

    proposal_dict = {
        "expert_index": expert_index, "subfield": subfield, "round": 2,
        "proposals": [{"title": p.title, "problem_statement": p.problem_statement, "potential_impact": p.potential_impact}
                      for p in result.proposals],
    }
    print(f"  [{subfield}] R2 complete: {[p.title[:60] for p in result.proposals]}")
    save_json(state, _EXPERTS_DIR, f"expert_{expert_index}_r2_proposal.json", proposal_dict)
    return {"expert_proposals_r2": [proposal_dict]}


def r2_critic_aggregate_node(state: Phase2State) -> Dict[str, Any]:
    latest_critiques = get_latest_r2_critiques(state.get("expert_r2_critiques", []))
    all_approved = all(c.get("overall_approved", False) for c in latest_critiques)
    new_iteration = state.get("expert_r2_iteration", 0) + 1
    max_iterations = state.get("expert_r2_max_iterations", 2)
    force_approved = new_iteration >= max_iterations
    if force_approved and not all_approved:
        print(f"--- R2 Critic Aggregate: iteration {new_iteration}/{max_iterations} — forcing approval ---")
    not_approved = [c["expert_index"] for c in latest_critiques if not c.get("overall_approved", False)]
    print(f"--- R2 Critic Aggregate: iteration={new_iteration}, approved={all_approved or force_approved} "
          f"(needing revision: {not_approved}) ---")
    return {"expert_r2_approved": all_approved or force_approved, "expert_r2_iteration": new_iteration}


def expert_r2_revision_dispatch_node(state: Phase2State) -> Dict[str, Any]:
    latest_critiques = get_latest_r2_critiques(state.get("expert_r2_critiques", []))
    needs = [c["expert_index"] for c in latest_critiques if not c.get("overall_approved", True)]
    print(f"--- R2 Revision Dispatch: experts {needs} need revision ---")
    return {}


def field_expert_0_r1_node(state: Phase2State) -> Dict[str, Any]: return _field_expert_r1(state, 0)
def field_expert_1_r1_node(state: Phase2State) -> Dict[str, Any]: return _field_expert_r1(state, 1)
def field_expert_2_r1_node(state: Phase2State) -> Dict[str, Any]: return _field_expert_r1(state, 2)
def field_expert_3_r1_node(state: Phase2State) -> Dict[str, Any]: return _field_expert_r1(state, 3)

def field_expert_0_r2_node(state: Phase2State) -> Dict[str, Any]: return _field_expert_r2(state, 0)
def field_expert_1_r2_node(state: Phase2State) -> Dict[str, Any]: return _field_expert_r2(state, 1)
def field_expert_2_r2_node(state: Phase2State) -> Dict[str, Any]: return _field_expert_r2(state, 2)
def field_expert_3_r2_node(state: Phase2State) -> Dict[str, Any]: return _field_expert_r2(state, 3)
