"""
Phase 2: Expert-Driven Open Problem Formulation Workflow

Two-stage design:
1. Agenda workflow: agenda → R1 surveys (parallel) → R2 proposals (parallel)
   → R2 critics (parallel) → r2_critic_aggregate → [loop or accept]
   → acceptance → ranking
2. Finalization: for each accepted proposal, run report_generator → final_judge
   → mechanism_updater sequentially
"""

from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from schema.phase2 import Phase2State
from nodes.phase2 import (
    agenda_creator_node,
    field_expert_0_r1_node, field_expert_1_r1_node, field_expert_2_r1_node, field_expert_3_r1_node,
    r2_sync_node, r2_proposals_sync_node,
    field_expert_0_r2_node, field_expert_1_r2_node, field_expert_2_r2_node, field_expert_3_r2_node,
    expert_r2_critic_0_node, expert_r2_critic_1_node, expert_r2_critic_2_node, expert_r2_critic_3_node,
    r2_critic_aggregate_node, expert_r2_revision_dispatch_node,
    expert_acceptance_node, problem_ranker_node,
    report_generator_node, mechanism_updater_node, final_judge_node,
)

NUM_PROPOSALS = 2

_R1_NODES = [field_expert_0_r1_node, field_expert_1_r1_node, field_expert_2_r1_node, field_expert_3_r1_node]
_R2_NODES = [field_expert_0_r2_node, field_expert_1_r2_node, field_expert_2_r2_node, field_expert_3_r2_node]
_CRITIC_NODES = [expert_r2_critic_0_node, expert_r2_critic_1_node, expert_r2_critic_2_node, expert_r2_critic_3_node]


def should_continue_r2_loop(state: Phase2State) -> Literal["approved", "revise"]:
    return "approved" if state.get("expert_r2_approved", False) else "revise"


def _create_agenda_workflow() -> CompiledStateGraph:
    workflow = StateGraph(Phase2State)

    workflow.add_node("agenda_creator", agenda_creator_node)
    workflow.add_node("r2_sync", r2_sync_node)
    workflow.add_node("r2_proposals_sync", r2_proposals_sync_node)
    workflow.add_node("r2_critic_aggregate", r2_critic_aggregate_node)
    workflow.add_node("expert_r2_revision_dispatch", expert_r2_revision_dispatch_node)
    workflow.add_node("expert_acceptance", expert_acceptance_node)
    workflow.add_node("problem_ranker", problem_ranker_node)

    for i, (r1, r2, critic) in enumerate(zip(_R1_NODES, _R2_NODES, _CRITIC_NODES)):
        workflow.add_node(f"expert_{i}_r1", r1)
        workflow.add_node(f"expert_{i}_r2", r2)
        workflow.add_node(f"expert_r2_critic_{i}", critic)

    workflow.set_entry_point("agenda_creator")

    for i in range(4):
        workflow.add_edge("agenda_creator", f"expert_{i}_r1")
    workflow.add_edge([f"expert_{i}_r1" for i in range(4)], "r2_sync")

    for i in range(4):
        workflow.add_edge("r2_sync", f"expert_{i}_r2")
    workflow.add_edge([f"expert_{i}_r2" for i in range(4)], "r2_proposals_sync")

    for i in range(4):
        workflow.add_edge("r2_proposals_sync", f"expert_r2_critic_{i}")
    workflow.add_edge([f"expert_r2_critic_{i}" for i in range(4)], "r2_critic_aggregate")

    workflow.add_conditional_edges("r2_critic_aggregate", should_continue_r2_loop,
                                   {"approved": "expert_acceptance", "revise": "expert_r2_revision_dispatch"})

    for i in range(4):
        workflow.add_edge("expert_r2_revision_dispatch", f"expert_{i}_r2")

    workflow.add_edge("expert_acceptance", "problem_ranker")
    workflow.add_edge("problem_ranker", END)

    compiled = workflow.compile()
    print("--- Agenda Workflow compiled successfully ---")
    return compiled


def _create_finalization_workflow() -> CompiledStateGraph:
    workflow = StateGraph(Phase2State)
    workflow.add_node("report_generator", report_generator_node)
    workflow.add_node("final_judge", final_judge_node)
    workflow.add_node("mechanism_updater", mechanism_updater_node)
    workflow.set_entry_point("report_generator")
    workflow.add_edge("report_generator", "final_judge")
    workflow.add_edge("final_judge", "mechanism_updater")
    workflow.add_edge("mechanism_updater", END)
    return workflow.compile()


def _format_proposal_as_markdown(proposal: dict) -> str:
    return f"""# {proposal.get('title', 'Untitled')}

## Problem Statement
{proposal.get('problem_statement', '')}

## Potential Impact
{proposal.get('potential_impact', '')}
"""


def run_phase2_workflow(
    summary: str,
    mechanism: str,
    arxiv_id: str = None,
    num_proposals: int = NUM_PROPOSALS,
) -> dict:
    print("\n" + "=" * 60)
    print("STARTING PHASE 2: EXPERT-DRIVEN OPEN PROBLEM FORMULATION")
    print(f"  Finalizing up to {num_proposals} proposals")
    print("=" * 60 + "\n")

    print("--- Phase 2 Step 1: Agenda, R1 surveys, R2 proposals, critic review ---")
    agenda_result = _create_agenda_workflow().invoke({
        "summary": summary, "mechanism": mechanism, "arxiv_id": arxiv_id,
        "expert_surveys_r1": [], "expert_proposals_r2": [], "expert_r2_critiques": [],
        "expert_r2_iteration": 0, "expert_r2_max_iterations": 2, "expert_r2_approved": False,
    })

    directions = agenda_result.get("agenda", [])
    accepted_proposals = agenda_result.get("accepted_proposals", [])

    if not directions:
        print("ERROR: Agenda creator produced no research directions!")
        return {"proposals": [], "agenda": []}
    if not accepted_proposals:
        print("ERROR: No proposals were accepted!")
        return {"proposals": [], "agenda": directions}

    print(f"\nAgenda workflow complete: {len(directions)} directions, {len(accepted_proposals)} accepted proposals")

    finalization_workflow = _create_finalization_workflow()
    selected = accepted_proposals[:num_proposals]
    print(f"\n--- Phase 2 Step 2: Finalizing {len(selected)} proposal(s) ---")

    all_proposals = []
    for i, proposal in enumerate(selected, 1):
        subfield = proposal.get("subfield", "?")
        title = proposal.get("title", "Untitled")
        print(f"\n{'='*60}\nFINALIZING PROPOSAL {i}/{len(selected)}\n  [{subfield}] {title[:80]}\n{'='*60}\n")

        final_state = finalization_workflow.invoke({
            "summary": summary, "mechanism": mechanism, "arxiv_id": arxiv_id,
            "proposal_num": i, "current_proposal": _format_proposal_as_markdown(proposal),
            "current_direction": f"[{subfield}] {title}",
            "expert_surveys_r1": [], "expert_proposals_r2": [], "expert_r2_critiques": [],
        })

        proposal_result = {
            "proposal_num": i, "subfield": subfield, "title": title,
            "expert_index": proposal.get("expert_index"),
            "final_report": final_state.get("final_report", ""),
            "ps_score": final_state.get("ps_score", 0),
            "pi_score": final_state.get("pi_score", 0),
            "quality_assessment": final_state.get("quality_assessment", {}),
        }
        all_proposals.append(proposal_result)
        print(f"\nProposal {i} finalized: PS={proposal_result['ps_score']}/5 | PI={proposal_result['pi_score']}/5")

    print("\n" + "=" * 60 + "\nPHASE 2 COMPLETE\n" + "=" * 60)
    for p in all_proposals:
        print(f"  Proposal {p['proposal_num']} [{p['subfield']}]: PS={p['ps_score']}/5 | PI={p['pi_score']}/5")
    print("=" * 60 + "\n")

    return {"proposals": all_proposals, "agenda": directions}


def _run_phase2_from_phase1_state(phase1_state: dict, num_proposals: int = NUM_PROPOSALS) -> dict:
    return run_phase2_workflow(
        summary=phase1_state["summary"],
        mechanism=phase1_state["mechanism"],
        arxiv_id=phase1_state.get("arxiv_id"),
        num_proposals=num_proposals,
    )
