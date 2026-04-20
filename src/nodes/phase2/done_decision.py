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
            "pivot_requested": False,
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

    critical_issues = feedback.get("critical_issues", [])
    required_fixes = feedback.get("required_fixes", [])
    minor_issues = feedback.get("minor_issues", [])
    overall_assessment = feedback.get("overall_assessment", "No feedback available.")

    history = state.get("feedback_history", [])
    if history:
        history_text = "\n".join(f"Iteration {i+1}: {h}" for i, h in enumerate(history))
    else:
        history_text = "No prior iterations."

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=DoneDecisionResult,
        inputs={
            "proposal": state["current_proposal"],
            "critical_issues": "\n".join(f"- {i}" for i in critical_issues) if critical_issues else "None.",
            "required_fixes": "\n".join(f"- {i}" for i in required_fixes) if required_fixes else "None.",
            "minor_issues": "\n".join(f"- {i}" for i in minor_issues) if minor_issues else "None.",
            "overall_assessment": overall_assessment,
            "iteration": iteration,
            "max_iterations": max_iterations,
            "feedback_history": history_text,
        }
    )

    # Decide whether to pivot (switch to a different vetted problem) vs revise.
    # Pivot when the PROBLEM ITSELF is broken — revision cannot fix these:
    #   - novelty_met=False  → problem is already known
    #   - feasibility_met=False → problem is fundamentally intractable
    # Only clarity issues (unclear formulation) warrant revision rather than pivot.
    problem_is_broken = not result.novelty_met or not result.feasibility_met
    pivot_requested = False
    force_exit = False
    if not result.is_done and problem_is_broken:
        reason = []
        if not result.novelty_met:
            reason.append("not novel")
        if not result.feasibility_met:
            reason.append("not feasible")
        vetted_problems = state.get("vetted_problems", [])
        current_index = state.get("vetted_problem_index", 0)
        if current_index + 1 < len(vetted_problems):
            pivot_requested = True
            print(f"  problem broken ({', '.join(reason)}) → requesting pivot to vetted problem "
                  f"{current_index + 2}/{len(vetted_problems)}")
        else:
            # No more vetted problems to try — revising a broken problem is pointless
            force_exit = True
            print(f"  problem broken ({', '.join(reason)}) and vetted pool exhausted → forcing exit")

    is_done = result.is_done or force_exit
    done_reason = result.reasoning if not force_exit else (
        f"Vetted problem pool exhausted with broken problem ({', '.join(reason) if problem_is_broken else ''}). "
        f"Exiting to avoid wasteful revision of unfixable problem."
    )

    print(f"Done Decision: is_done={is_done}, clarity={result.clarity_met}, "
          f"feasibility={result.feasibility_met}, novelty={result.novelty_met}, "
          f"pivot_requested={pivot_requested}")

    # Save decision to file if arxiv_id is available
    arxiv_id = state.get("arxiv_id")
    if arxiv_id:
        decision_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / f"proposal_{proposal_num}" / "decisions"
        decision_dir.mkdir(parents=True, exist_ok=True)

        decision_data = {
            "iteration": iteration,
            "is_done": is_done,
            "force_exit": force_exit,
            "clarity_met": result.clarity_met,
            "feasibility_met": result.feasibility_met,
            "novelty_met": result.novelty_met,
            "pivot_requested": pivot_requested,
            "reasoning": done_reason,
            "recommendation": result.recommendation,
        }
        decision_path = decision_dir / f"decision_iteration_{iteration}.json"
        decision_path.write_text(json.dumps(decision_data, indent=2), encoding="utf-8")
        print(f"  > Saved decision to {decision_path}")

    return {
        "is_done": is_done,
        "done_reason": done_reason,
        "pivot_requested": pivot_requested,
    }
