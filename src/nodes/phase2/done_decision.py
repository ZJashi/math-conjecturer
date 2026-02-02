"""Done Decision node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import BASE_SYSTEM_PROMPT, DONE_DECISION_PROMPT
from schema.phase2 import Phase2State, DoneDecisionResult
from ._common import get_model


def done_decision_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 3.4: Done Decision

    Decides if the proposal quality is sufficient to exit the loop.
    """
    iteration = state.get("phase2_iteration", 1)
    max_iterations = state.get("max_iterations", 5)
    print(f"--- Done Decision: Evaluating proposal (iteration {iteration}/{max_iterations}) ---")

    # Force exit if we've hit max iterations
    if iteration >= max_iterations:
        print("Max iterations reached - forcing exit")
        return {
            "is_done": True,
            "done_reason": f"Maximum iterations ({max_iterations}) reached.",
        }

    model = get_model()
    prompt = ChatPromptTemplate.from_messages([
        ("system", BASE_SYSTEM_PROMPT),
        ("human", DONE_DECISION_PROMPT)
    ])

    chain = prompt | model.with_structured_output(DoneDecisionResult)

    feedback = state.get("consolidated_feedback", {})

    result = chain.invoke({
        "proposal": state["current_proposal"],
        "feedback": feedback.get("overall_assessment", "No feedback available"),
        "iteration": iteration,
        "max_iterations": max_iterations,
    })

    print(f"Done Decision: is_done={result.is_done}, clarity={result.clarity_met}, "
          f"feasibility={result.feasibility_met}, novelty={result.novelty_met}")

    return {
        "is_done": result.is_done,
        "done_reason": result.reasoning,
    }
