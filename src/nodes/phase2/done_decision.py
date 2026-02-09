"""Done Decision node for Phase 2."""

import json
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import DONE_DECISION_SYSTEM, DONE_DECISION_PROMPT
from schema.phase2 import Phase2State, DoneDecisionResult
from ._common import PAPERS_DIR, invoke_with_structured_output


def done_decision_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 3.4: Done Decision

    Decides if the proposal quality is sufficient to exit the loop.
    """
    iteration = state.get("phase2_iteration", 1)
    max_iterations = state.get("max_iterations", 5)
    print(f"--- Done Decision: Evaluating proposal (iteration {iteration}/{max_iterations}) ---")

    proposal_num = state.get("proposal_num", 1)

    # Force exit if we've hit max iterations
    if iteration >= max_iterations:
        print("Max iterations reached - forcing exit")
        decision_result = {
            "is_done": True,
            "done_reason": f"Maximum iterations ({max_iterations}) reached.",
        }

        # Save decision
        arxiv_id = state.get("arxiv_id")
        if arxiv_id:
            decision_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / f"proposal_{proposal_num}" / "decisions"
            decision_dir.mkdir(parents=True, exist_ok=True)
            decision_path = decision_dir / f"decision_iteration_{iteration}.json"
            decision_path.write_text(json.dumps(decision_result, indent=2), encoding="utf-8")

        return decision_result

    prompt = ChatPromptTemplate.from_messages([
        ("system", DONE_DECISION_SYSTEM),
        ("human", DONE_DECISION_PROMPT)
    ])

    feedback = state.get("consolidated_feedback", {})

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=DoneDecisionResult,
        inputs={
            "proposal": state["current_proposal"],
            "feedback": feedback.get("overall_assessment", "No feedback available"),
            "iteration": iteration,
            "max_iterations": max_iterations,
        }
    )

    print(f"Done Decision: is_done={result.is_done}, clarity={result.clarity_met}, "
          f"feasibility={result.feasibility_met}, novelty={result.novelty_met}")

    # Save decision to file if arxiv_id is available
    arxiv_id = state.get("arxiv_id")
    if arxiv_id:
        decision_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / f"proposal_{proposal_num}" / "decisions"
        decision_dir.mkdir(parents=True, exist_ok=True)

        decision_data = {
            "iteration": iteration,
            "is_done": result.is_done,
            "clarity_met": result.clarity_met,
            "feasibility_met": result.feasibility_met,
            "novelty_met": result.novelty_met,
            "reasoning": result.reasoning,
            "recommendation": result.recommendation,
        }
        decision_path = decision_dir / f"decision_iteration_{iteration}.json"
        decision_path.write_text(json.dumps(decision_data, indent=2), encoding="utf-8")
        print(f"  > Saved decision to {decision_path}")

    return {
        "is_done": result.is_done,
        "done_reason": result.reasoning,
    }
