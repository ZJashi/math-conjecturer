"""Expert R2 Critic nodes for Phase 2 — one critic per expert's two R2 proposals."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import EXPERT_R2_CRITIC_SYSTEM, EXPERT_R2_CRITIC_PROMPT
from schema.phase2 import Phase2State, ExpertR2CritiqueResult
from ._common import (
    invoke_with_structured_output, get_latest_r2_proposals,
    format_survey_as_text, format_proposals_as_text, save_json,
)

_EXPERTS_DIR = "step4_open_problems/4b_experts"


def _expert_r2_critic_node(state: Phase2State, expert_index: int) -> Dict[str, Any]:
    subfields = state.get("subfields", [])
    subfield = subfields[expert_index] if expert_index < len(subfields) else f"expert_{expert_index}"

    r1_survey = next((s for s in state.get("expert_surveys_r1", []) if s.get("expert_index") == expert_index), None)
    latest_proposals = get_latest_r2_proposals(state.get("expert_proposals_r2", []))
    r2_proposal = next((p for p in latest_proposals if p.get("expert_index") == expert_index), None)

    if r1_survey is None or r2_proposal is None:
        missing = " and ".join(x for x, v in [("R1 survey", r1_survey), ("R2 proposal", r2_proposal)] if v is None)
        msg = f"Missing {missing} for expert {expert_index} ({subfield})."
        print(f"  WARNING: {msg} Auto-rejecting.")
        critique_dict = {
            "expert_index": expert_index, "subfield": subfield,
            "verdicts": [
                {"proposal_index": i, "approved": False, "blocking_issues": [f"Cannot evaluate: {msg}"], "suggestions": []}
                for i in range(2)
            ],
            "overall_approved": False,
            "summary": f"Auto-rejected: {msg}",
        }
        save_json(state, _EXPERTS_DIR, f"expert_{expert_index}_r2_critique.json", critique_dict)
        return {"expert_r2_critiques": [critique_dict]}

    proposals_list = r2_proposal.get("proposals", [])
    print(f"--- Expert R2 Critic [{subfield}]: Evaluating {len(proposals_list)} proposals ---")

    prompt = ChatPromptTemplate.from_messages([("system", EXPERT_R2_CRITIC_SYSTEM), ("human", EXPERT_R2_CRITIC_PROMPT)])
    result = invoke_with_structured_output(
        prompt=prompt, output_class=ExpertR2CritiqueResult,
        inputs={
            "subfield": subfield,
            "r1_survey": format_survey_as_text(r1_survey),
            "proposal": format_proposals_as_text(proposals_list),
            "paper_summary": state["summary"],
            "mechanisms": state["mechanism"],
        },
        temperature=0.3,
    )

    critique_dict = {
        "expert_index": expert_index, "subfield": subfield,
        "verdicts": [{"proposal_index": v.proposal_index, "approved": v.approved,
                      "blocking_issues": v.blocking_issues, "suggestions": v.suggestions}
                     for v in result.verdicts],
        "overall_approved": result.overall_approved,
        "summary": result.summary,
    }
    print(f"  [{subfield}] {'APPROVED' if result.overall_approved else 'REJECTED'} — {result.summary[:100]}")
    save_json(state, _EXPERTS_DIR, f"expert_{expert_index}_r2_critique.json", critique_dict)
    return {"expert_r2_critiques": [critique_dict]}


def expert_r2_critic_0_node(state: Phase2State) -> Dict[str, Any]: return _expert_r2_critic_node(state, 0)
def expert_r2_critic_1_node(state: Phase2State) -> Dict[str, Any]: return _expert_r2_critic_node(state, 1)
def expert_r2_critic_2_node(state: Phase2State) -> Dict[str, Any]: return _expert_r2_critic_node(state, 2)
def expert_r2_critic_3_node(state: Phase2State) -> Dict[str, Any]: return _expert_r2_critic_node(state, 3)
