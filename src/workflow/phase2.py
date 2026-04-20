"""
Phase 2: Expert-Driven Open Problem Formulation Workflow

Two-stage design:
1. Agenda workflow: agenda → R1 surveys (parallel) → R2 proposals (parallel)
   → R2 critics (parallel) → r2_critic_aggregate → [loop or accept]
   → acceptance → ranking
2. Finalization loop: for each accepted proposal, run report_generator → final_judge
   → mechanism_updater sequentially
"""

from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from schema.phase2 import Phase2State
from nodes.phase2 import (
    agenda_creator_node,
    field_expert_0_r1_node,
    field_expert_1_r1_node,
    field_expert_2_r1_node,
    field_expert_3_r1_node,
    r2_sync_node,
    r2_proposals_sync_node,
    field_expert_0_r2_node,
    field_expert_1_r2_node,
    field_expert_2_r2_node,
    field_expert_3_r2_node,
    expert_r2_critic_0_node,
    expert_r2_critic_1_node,
    expert_r2_critic_2_node,
    expert_r2_critic_3_node,
    r2_critic_aggregate_node,
    expert_r2_revision_dispatch_node,
    expert_acceptance_node,
    problem_ranker_node,
    report_generator_node,
    mechanism_updater_node,
    final_judge_node,
)


def should_continue_r2_loop(state: Phase2State) -> Literal["approved", "revise"]:
    """Conditional: proceed to acceptance or loop back for revision."""
    if state.get("expert_r2_approved", True):
        return "approved"
    return "revise"

NUM_PROPOSALS = 3


def create_agenda_workflow() -> CompiledStateGraph:
    """
    Agenda workflow:

    agenda_creator
    → [expert_0_r1, expert_1_r1, expert_2_r1, expert_3_r1]   (parallel)
    → (fan-in) r2_sync
    → [expert_0_r2, expert_1_r2, expert_2_r2, expert_3_r2]   (parallel)
    → (fan-in) r2_proposals_sync
    → [expert_r2_critic_0 ... expert_r2_critic_3]              (parallel)
    → (fan-in) r2_critic_aggregate
    → conditional:
        "approved" → expert_acceptance → problem_ranker → END
        "revise"   → expert_r2_revision_dispatch
                     → [expert_0_r2 ... expert_3_r2]           (loop back)
    """
    workflow = StateGraph(Phase2State)

    # Agenda
    workflow.add_node("agenda_creator", agenda_creator_node)

    # Expert Round 1 (parallel literature surveys)
    workflow.add_node("expert_0_r1", field_expert_0_r1_node)
    workflow.add_node("expert_1_r1", field_expert_1_r1_node)
    workflow.add_node("expert_2_r1", field_expert_2_r1_node)
    workflow.add_node("expert_3_r1", field_expert_3_r1_node)

    # R1 → R2 barrier
    workflow.add_node("r2_sync", r2_sync_node)

    # Expert Round 2 (parallel proposal writing, also used on revision loops)
    workflow.add_node("expert_0_r2", field_expert_0_r2_node)
    workflow.add_node("expert_1_r2", field_expert_1_r2_node)
    workflow.add_node("expert_2_r2", field_expert_2_r2_node)
    workflow.add_node("expert_3_r2", field_expert_3_r2_node)

    # R2 proposals → critics barrier
    workflow.add_node("r2_proposals_sync", r2_proposals_sync_node)

    # R2 critics (parallel, one per expert pair of proposals)
    workflow.add_node("expert_r2_critic_0", expert_r2_critic_0_node)
    workflow.add_node("expert_r2_critic_1", expert_r2_critic_1_node)
    workflow.add_node("expert_r2_critic_2", expert_r2_critic_2_node)
    workflow.add_node("expert_r2_critic_3", expert_r2_critic_3_node)

    # R2 critic aggregate — computes expert_r2_approved + iteration counter
    workflow.add_node("r2_critic_aggregate", r2_critic_aggregate_node)

    # R2 revision dispatch barrier — loops back to R2 experts
    workflow.add_node("expert_r2_revision_dispatch", expert_r2_revision_dispatch_node)

    # Acceptance + ranking
    workflow.add_node("expert_acceptance", expert_acceptance_node)
    workflow.add_node("problem_ranker", problem_ranker_node)

    # Entry point
    workflow.set_entry_point("agenda_creator")

    # Fan-out: agenda → 4 parallel R1 experts
    workflow.add_edge("agenda_creator", "expert_0_r1")
    workflow.add_edge("agenda_creator", "expert_1_r1")
    workflow.add_edge("agenda_creator", "expert_2_r1")
    workflow.add_edge("agenda_creator", "expert_3_r1")

    # Fan-in: all R1 experts → r2_sync barrier
    workflow.add_edge(
        ["expert_0_r1", "expert_1_r1", "expert_2_r1", "expert_3_r1"],
        "r2_sync",
    )

    # Fan-out: r2_sync → 4 parallel R2 experts
    workflow.add_edge("r2_sync", "expert_0_r2")
    workflow.add_edge("r2_sync", "expert_1_r2")
    workflow.add_edge("r2_sync", "expert_2_r2")
    workflow.add_edge("r2_sync", "expert_3_r2")

    # Fan-in: all R2 experts → r2_proposals_sync barrier
    workflow.add_edge(
        ["expert_0_r2", "expert_1_r2", "expert_2_r2", "expert_3_r2"],
        "r2_proposals_sync",
    )

    # Fan-out: r2_proposals_sync → 4 parallel R2 critics
    workflow.add_edge("r2_proposals_sync", "expert_r2_critic_0")
    workflow.add_edge("r2_proposals_sync", "expert_r2_critic_1")
    workflow.add_edge("r2_proposals_sync", "expert_r2_critic_2")
    workflow.add_edge("r2_proposals_sync", "expert_r2_critic_3")

    # Fan-in: all R2 critics → r2_critic_aggregate
    workflow.add_edge(
        ["expert_r2_critic_0", "expert_r2_critic_1", "expert_r2_critic_2", "expert_r2_critic_3"],
        "r2_critic_aggregate",
    )

    # Conditional: approved → acceptance path | revise → loop back
    workflow.add_conditional_edges(
        "r2_critic_aggregate",
        should_continue_r2_loop,
        {
            "approved": "expert_acceptance",
            "revise": "expert_r2_revision_dispatch",
        },
    )

    # Revision loop: dispatch → 4 R2 experts fan-out
    workflow.add_edge("expert_r2_revision_dispatch", "expert_0_r2")
    workflow.add_edge("expert_r2_revision_dispatch", "expert_1_r2")
    workflow.add_edge("expert_r2_revision_dispatch", "expert_2_r2")
    workflow.add_edge("expert_r2_revision_dispatch", "expert_3_r2")

    # Sequential: acceptance → ranking → END
    workflow.add_edge("expert_acceptance", "problem_ranker")
    workflow.add_edge("problem_ranker", END)

    compiled = workflow.compile()
    print("--- Agenda Workflow compiled successfully ---")
    return compiled


def create_finalization_workflow() -> CompiledStateGraph:
    """
    Simple sequential workflow for a single proposal:
    report_generator → final_judge → mechanism_updater → END
    """
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
    """Format an accepted proposal dict as a markdown string for the finalization workflow."""
    return f"""# {proposal.get('title', 'Untitled')}

## Problem Statement
{proposal.get('problem_statement', '')}

## Motivation
{proposal.get('motivation', '')}

## Connections to Existing Work
{proposal.get('connections', '')}

## Potential Impact
{proposal.get('potential_impact', '')}
"""


def run_phase2_workflow(
    summary: str,
    mechanism: str,
    arxiv_id: str = None,
    num_proposals: int = NUM_PROPOSALS,
) -> dict:
    """
    Run the full Phase 2 expert-driven workflow.

    Step 1: Run the agenda workflow to get accepted + ranked proposals.
    Step 2: For each of the top `num_proposals` accepted proposals, run the
            finalization workflow (report_generator → final_judge → mechanism_updater).

    Args:
        summary: Paper summary from Phase 1.
        mechanism: Mechanism XML from Phase 1.
        arxiv_id: Optional paper identifier for file saving.
        num_proposals: Maximum number of proposals to finalize (default: 3).

    Returns:
        Dict with 'proposals' (list of finalized proposal results) and 'agenda' (list of directions).
    """
    print("\n" + "=" * 60)
    print("STARTING PHASE 2: EXPERT-DRIVEN OPEN PROBLEM FORMULATION")
    print(f"  Finalizing up to {num_proposals} proposals")
    print("=" * 60 + "\n")

    # === Step 1: Agenda + expert workflow ===
    print("--- Phase 2 Step 1: Agenda, R1 surveys, R2 proposals, critic review ---")
    agenda_workflow = create_agenda_workflow()

    initial_state: Phase2State = {
        "summary": summary,
        "mechanism": mechanism,
        "arxiv_id": arxiv_id,
        "expert_surveys_r1": [],
        "expert_proposals_r2": [],
        "expert_r2_critiques": [],
        "expert_r2_iteration": 0,
        "expert_r2_max_iterations": 2,
        "expert_r2_approved": False,
    }

    agenda_result = agenda_workflow.invoke(initial_state)

    directions = agenda_result.get("agenda", [])
    accepted_proposals = agenda_result.get("accepted_proposals", [])

    if not directions:
        print("ERROR: Agenda creator produced no research directions!")
        return {"proposals": [], "agenda": []}

    if not accepted_proposals:
        print("ERROR: No proposals were accepted!")
        return {"proposals": [], "agenda": directions}

    print(f"\nAgenda workflow complete:")
    print(f"  Research directions: {len(directions)}")
    print(f"  Accepted proposals: {len(accepted_proposals)}")

    # === Step 2: Finalize top N accepted proposals ===
    finalization_workflow = create_finalization_workflow()
    selected = accepted_proposals[:num_proposals]

    print(f"\n--- Phase 2 Step 2: Finalizing {len(selected)} proposal(s) ---")

    all_proposals = []

    for i, proposal in enumerate(selected, 1):
        subfield = proposal.get("subfield", "?")
        title = proposal.get("title", "Untitled")

        print(f"\n{'='*60}")
        print(f"FINALIZING PROPOSAL {i}/{len(selected)}")
        print(f"  [{subfield}] {title[:80]}")
        print(f"{'='*60}\n")

        current_proposal_text = _format_proposal_as_markdown(proposal)

        finalization_state: Phase2State = {
            "summary": summary,
            "mechanism": mechanism,
            "arxiv_id": arxiv_id,
            "proposal_num": i,
            "current_proposal": current_proposal_text,
            "current_direction": f"[{subfield}] {title}",
            "expert_surveys_r1": [],
            "expert_proposals_r2": [],
            "expert_r2_critiques": [],
        }

        final_state = finalization_workflow.invoke(finalization_state)

        proposal_result = {
            "proposal_num": i,
            "subfield": subfield,
            "title": title,
            "expert_index": proposal.get("expert_index"),
            "final_report": final_state.get("final_report", ""),
            "ps_score": final_state.get("ps_score", 0),
            "pi_score": final_state.get("pi_score", 0),
            "quality_assessment": final_state.get("quality_assessment", {}),
        }
        all_proposals.append(proposal_result)

        print(
            f"\nProposal {i} finalized: "
            f"PS={proposal_result['ps_score']}/5 | "
            f"PI={proposal_result['pi_score']}/5"
        )

    # === Summary ===
    print("\n" + "=" * 60)
    print("PHASE 2 COMPLETE")
    print("=" * 60)
    for p in all_proposals:
        print(
            f"  Proposal {p['proposal_num']} [{p['subfield']}]: "
            f"PS={p['ps_score']}/5 | PI={p['pi_score']}/5"
        )
    print("=" * 60 + "\n")

    return {
        "proposals": all_proposals,
        "agenda": directions,
    }


def run_phase2_from_phase1_state(phase1_state: dict, num_proposals: int = NUM_PROPOSALS) -> dict:
    """
    Run Phase 2 directly from Phase 1 output state.

    Args:
        phase1_state: The state dict from Phase 1 containing 'summary' and 'mechanism'.
        num_proposals: Maximum number of proposals to finalize.

    Returns:
        Dict with 'proposals' list and 'agenda'.
    """
    return run_phase2_workflow(
        summary=phase1_state["summary"],
        mechanism=phase1_state["mechanism"],
        arxiv_id=phase1_state.get("arxiv_id"),
        num_proposals=num_proposals,
    )
