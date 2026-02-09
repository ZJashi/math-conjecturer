"""
Phase 2: Open Problem Formulation LangGraph Workflow

This module defines the complete LangGraph workflow that implements the
iterative ideation + critique loop for research proposal generation.

The workflow generates 3 distinct proposals by:
1. Running an agenda workflow once to get research directions
2. Running a proposal workflow 3 times, each focused on a different direction

Flow per proposal:
1. Brainstormer
2. Parallel Critics (Sanity, Example, Reverse, Obstruction)
3. Feedback Consolidator
4. Done Decision (loop or exit)
5. Report Generator
6. Final Judge
7. Quality Score
"""

from pathlib import Path
from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from schema.phase2 import Phase2State
from nodes.phase2 import (
    context_ingestion_node,
    agenda_creator_node,
    brainstormer_node,
    sanity_checker_node,
    example_tester_node,
    reverse_reasoner_node,
    obstruction_analyzer_node,
    feedback_consolidator_node,
    done_decision_node,
    report_generator_node,
    final_judge_node,
    quality_score_node,
)


NUM_PROPOSALS = 3


def should_continue_loop(state: Phase2State) -> Literal["continue", "exit"]:
    """
    Conditional edge function for the Agent K loop.

    Returns "continue" to loop back to brainstormer, or "exit" to proceed
    to report generation.
    """
    is_done = state.get("is_done", False)

    if is_done:
        print(f"--- Loop Exit: {state.get('done_reason', 'Proposal approved')} ---")
        return "exit"
    else:
        iteration = state.get("phase2_iteration", 1)
        print(f"--- Loop Continue: Returning to brainstormer (iteration {iteration}) ---")
        return "continue"


def create_agenda_workflow() -> CompiledStateGraph:
    """
    Creates the agenda-only workflow: context_ingestion → agenda_creator.

    Returns:
        Compiled LangGraph workflow that produces research directions.
    """
    workflow = StateGraph(Phase2State)

    workflow.add_node("context_ingestion", context_ingestion_node)
    workflow.add_node("agenda_creator", agenda_creator_node)

    workflow.set_entry_point("context_ingestion")
    workflow.add_edge("context_ingestion", "agenda_creator")
    workflow.add_edge("agenda_creator", END)

    compiled = workflow.compile()
    print("--- Agenda Workflow compiled successfully ---")
    return compiled


def create_proposal_workflow(
    max_iterations: int = 5,
) -> CompiledStateGraph:
    """
    Creates the proposal workflow: brainstormer → critics → feedback → done → report → judge → score.

    This workflow is run once per research direction.

    Args:
        max_iterations: Maximum number of brainstorm-critique iterations (default: 5)

    Returns:
        Compiled LangGraph workflow for a single proposal
    """
    workflow = StateGraph(Phase2State)

    # Agent K Loop
    workflow.add_node("brainstormer", brainstormer_node)

    # Parallel Critique Agents
    workflow.add_node("sanity_checker", sanity_checker_node)
    workflow.add_node("example_tester", example_tester_node)
    workflow.add_node("reverse_reasoner", reverse_reasoner_node)
    workflow.add_node("obstruction_analyzer", obstruction_analyzer_node)

    # Feedback and Decision
    workflow.add_node("feedback_consolidator", feedback_consolidator_node)
    workflow.add_node("done_decision", done_decision_node)

    # Finalization
    workflow.add_node("report_generator", report_generator_node)
    workflow.add_node("final_judge", final_judge_node)
    workflow.add_node("quality_score", quality_score_node)

    # Entry point
    workflow.set_entry_point("brainstormer")

    # Parallel: Brainstormer → All 4 Critics (fan-out)
    workflow.add_edge("brainstormer", "sanity_checker")
    workflow.add_edge("brainstormer", "example_tester")
    workflow.add_edge("brainstormer", "reverse_reasoner")
    workflow.add_edge("brainstormer", "obstruction_analyzer")

    # Join: All Critics → Feedback Consolidator (fan-in)
    workflow.add_edge(
        ["sanity_checker", "example_tester", "reverse_reasoner", "obstruction_analyzer"],
        "feedback_consolidator"
    )

    # Sequential: Consolidator → Done Decision
    workflow.add_edge("feedback_consolidator", "done_decision")

    # Conditional: Done Decision → Loop or Exit
    workflow.add_conditional_edges(
        "done_decision",
        should_continue_loop,
        {
            "continue": "brainstormer",
            "exit": "report_generator",
        }
    )

    # Sequential: Report → Judge → Score → END
    workflow.add_edge("report_generator", "final_judge")
    workflow.add_edge("final_judge", "quality_score")
    workflow.add_edge("quality_score", END)

    compiled = workflow.compile()
    print("--- Proposal Workflow compiled successfully ---")
    return compiled


def run_phase2_workflow(
    summary: str,
    mechanism: str,
    arxiv_id: str = None,
    max_iterations: int = 5,
    num_proposals: int = NUM_PROPOSALS,
) -> dict:
    """
    Convenience function to create and run the Phase 2 workflow.

    Generates multiple proposals by:
    1. Running the agenda workflow once to get research directions
    2. Running the proposal workflow once per direction (top N)

    Args:
        summary: Paper summary from Phase 1 (summarizer_node output)
        mechanism: Mechanism XML from Phase 1 (mechanism_node output)
        arxiv_id: Optional paper identifier for file saving
        max_iterations: Maximum brainstorm-critique iterations per proposal
        num_proposals: Number of proposals to generate (default: 3)

    Returns:
        Dict containing 'proposals' list and 'agenda' from the workflow
    """
    print("\n" + "=" * 60)
    print("STARTING PHASE 2: OPEN PROBLEM FORMULATION")
    print(f"  Generating {num_proposals} proposals")
    print("=" * 60 + "\n")

    # === Step 1: Run agenda workflow once ===
    print("--- Phase 2 Step 1: Generating Research Agenda ---")
    agenda_workflow = create_agenda_workflow()

    agenda_state: Phase2State = {
        "summary": summary,
        "mechanism": mechanism,
        "arxiv_id": arxiv_id,
        "max_iterations": max_iterations,
        "critiques": [],
    }

    agenda_result = agenda_workflow.invoke(agenda_state)
    directions = agenda_result.get("agenda", [])

    if not directions:
        print("ERROR: Agenda creator produced no research directions!")
        return {"proposals": [], "agenda": []}

    # Pick top N directions
    selected_directions = directions[:num_proposals]
    print(f"\nSelected {len(selected_directions)} directions for proposal generation:")
    for i, d in enumerate(selected_directions, 1):
        print(f"  {i}. {d[:100]}...")

    # === Step 2: Run proposal workflow for each direction ===
    proposal_workflow = create_proposal_workflow(max_iterations=max_iterations)
    all_proposals = []

    for i, direction in enumerate(selected_directions, 1):
        print(f"\n{'='*60}")
        print(f"PROPOSAL {i}/{len(selected_directions)}")
        print(f"Direction: {direction[:100]}...")
        print(f"{'='*60}\n")

        proposal_state: Phase2State = {
            "summary": summary,
            "mechanism": mechanism,
            "arxiv_id": arxiv_id,
            "max_iterations": max_iterations,
            "current_direction": direction,
            "proposal_num": i,
            "agenda": directions,  # Pass full agenda for context
            "critiques": [],
        }

        final_state = proposal_workflow.invoke(proposal_state)

        proposal_result = {
            "proposal_num": i,
            "direction": direction,
            "final_report": final_state.get("final_report", ""),
            "quality_score": final_state.get("quality_score", 0),
            "quality_category": final_state.get("quality_category", "N/A"),
            "quality_assessment": final_state.get("quality_assessment", {}),
            "iterations": final_state.get("phase2_iteration", 0),
        }
        all_proposals.append(proposal_result)

        score = proposal_result["quality_score"]
        print(f"\nProposal {i} complete: score={score:.1f}/100 ({proposal_result['quality_category']})")

    # === Print summary ===
    print("\n" + "=" * 60)
    print("PHASE 2 COMPLETE")
    print("=" * 60)
    for p in all_proposals:
        score = p["quality_score"]
        print(f"  Proposal {p['proposal_num']}: {score:.1f}/100 ({p['quality_category']}) - {p['iterations']} iterations")
    print("=" * 60 + "\n")

    return {
        "proposals": all_proposals,
        "agenda": directions,
    }


def run_phase2_from_phase1_state(phase1_state: dict, max_iterations: int = 5) -> dict:
    """
    Run Phase 2 directly from Phase 1 output state.

    Args:
        phase1_state: The state dict from Phase 1 containing 'summary' and 'mechanism'
        max_iterations: Maximum brainstorm-critique iterations

    Returns:
        Dict with 'proposals' list and 'agenda'
    """
    return run_phase2_workflow(
        summary=phase1_state["summary"],
        mechanism=phase1_state["mechanism"],
        arxiv_id=phase1_state.get("arxiv_id"),
        max_iterations=max_iterations,
    )
