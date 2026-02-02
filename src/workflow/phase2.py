"""
Phase 2: Open Problem Formulation LangGraph Workflow

This module defines the complete LangGraph workflow that implements the
iterative ideation + critique loop for research proposal generation.

Flow:
1. Context Ingestion
2. Agenda Creator
3. Agent K Loop (iterative):
   3.1 Brainstormer
   3.2 Parallel Critics (Sanity, Example, Reverse, Obstruction)
   3.3 Feedback Consolidator
   3.4 Done Decision (loop or exit)
4. Report Generator
5. Final Judge
6. Quality Score
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


def create_phase2_workflow(
    max_iterations: int = 5,
    save_visualization: bool = True,
) -> CompiledStateGraph:
    """
    Creates and compiles the Phase 2 Open Problem Formulation workflow.

    Args:
        max_iterations: Maximum number of brainstorm-critique iterations (default: 5)
        save_visualization: Whether to save a PNG visualization of the graph

    Returns:
        Compiled LangGraph workflow ready for execution
    """
    print(f"--- Building Phase 2 Workflow (max_iterations={max_iterations}) ---")

    # Create the state graph
    workflow = StateGraph(Phase2State)

    # =========================================================================
    # ADD NODES
    # =========================================================================

    # Phase 1: Context and Planning
    workflow.add_node("context_ingestion", context_ingestion_node)
    workflow.add_node("agenda_creator", agenda_creator_node)

    # Phase 2: Agent K Loop
    workflow.add_node("brainstormer", brainstormer_node)

    # Parallel Critique Agents
    workflow.add_node("sanity_checker", sanity_checker_node)
    workflow.add_node("example_tester", example_tester_node)
    workflow.add_node("reverse_reasoner", reverse_reasoner_node)
    workflow.add_node("obstruction_analyzer", obstruction_analyzer_node)

    # Feedback and Decision
    workflow.add_node("feedback_consolidator", feedback_consolidator_node)
    workflow.add_node("done_decision", done_decision_node)

    # Phase 3: Finalization
    workflow.add_node("report_generator", report_generator_node)
    workflow.add_node("final_judge", final_judge_node)
    workflow.add_node("quality_score", quality_score_node)

    # =========================================================================
    # DEFINE EDGES
    # =========================================================================

    # Entry point
    workflow.set_entry_point("context_ingestion")

    # Sequential: Context → Agenda → Brainstormer
    workflow.add_edge("context_ingestion", "agenda_creator")
    workflow.add_edge("agenda_creator", "brainstormer")

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
            "continue": "brainstormer",  # Loop back for another iteration
            "exit": "report_generator",   # Proceed to report generation
        }
    )

    # Sequential: Report → Judge → Score → END
    workflow.add_edge("report_generator", "final_judge")
    workflow.add_edge("final_judge", "quality_score")
    workflow.add_edge("quality_score", END)

    # =========================================================================
    # COMPILE
    # =========================================================================

    compiled = workflow.compile()
    print("--- Phase 2 Workflow compiled successfully ---")

    # Optionally save visualization
    if save_visualization:
        try:
            output_file = Path(__file__).resolve().parent.parent / "phase2_workflow.png"
            with open(output_file, "wb") as f:
                graph_data = compiled.get_graph().draw_mermaid_png()
                f.write(graph_data)
            print(f"Graph visualization saved to {output_file}")
        except Exception as e:
            print(f"Could not save graph visualization: {e}")

    return compiled


def run_phase2_workflow(
    summary: str,
    mechanism: str,
    arxiv_id: str = None,
    max_iterations: int = 5,
) -> Phase2State:
    """
    Convenience function to create and run the Phase 2 workflow.

    Args:
        summary: Paper summary from Phase 1 (summarizer_node output)
        mechanism: Mechanism XML from Phase 1 (mechanism_node output)
        arxiv_id: Optional paper identifier for file saving
        max_iterations: Maximum brainstorm-critique iterations

    Returns:
        Final state containing the report, scores, and all intermediate results
    """
    # Create workflow
    workflow = create_phase2_workflow(
        max_iterations=max_iterations,
        save_visualization=False,
    )

    # Prepare initial state (using Phase 1 field names)
    initial_state: Phase2State = {
        "summary": summary,
        "mechanism": mechanism,
        "arxiv_id": arxiv_id,
        "max_iterations": max_iterations,
        "critiques": [],
    }

    # Run workflow
    print("\n" + "=" * 60)
    print("STARTING PHASE 2: OPEN PROBLEM FORMULATION")
    print("=" * 60 + "\n")

    final_state = workflow.invoke(initial_state)

    print("\n" + "=" * 60)
    print("PHASE 2 COMPLETE")
    print("=" * 60)
    print(f"Iterations: {final_state.get('phase2_iteration', 'N/A')}")
    score = final_state.get('quality_score')
    print(f"Quality Score: {score:.1f}/100" if score else "Quality Score: N/A")
    print(f"Category: {final_state.get('quality_category', 'N/A')}")
    print("=" * 60 + "\n")

    return final_state


def run_phase2_from_phase1_state(phase1_state: dict, max_iterations: int = 5) -> Phase2State:
    """
    Run Phase 2 directly from Phase 1 output state.

    Args:
        phase1_state: The state dict from Phase 1 containing 'summary' and 'mechanism'
        max_iterations: Maximum brainstorm-critique iterations

    Returns:
        Final Phase 2 state
    """
    return run_phase2_workflow(
        summary=phase1_state["summary"],
        mechanism=phase1_state["mechanism"],
        arxiv_id=phase1_state.get("arxiv_id"),
        max_iterations=max_iterations,
    )
