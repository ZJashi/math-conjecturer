"""Brainstormer node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import (
    BRAINSTORMER_SYSTEM,
    BRAINSTORMER_PROMPT,
    BRAINSTORMER_REVISION_PROMPT,
)
from schema.phase2 import Phase2State, ProposalResult
from ._common import PAPERS_DIR, invoke_with_structured_output


def brainstormer_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 3.1: Brainstormer

    Generates or revises a proposal based on context and feedback.
    Supports pivot mode: when pivot_requested=True, switches to the next vetted problem
    and starts fresh (resetting iteration count and prior proposal).
    """
    pivot_requested = state.get("pivot_requested", False)
    vetted_problems = state.get("vetted_problems", [])
    current_index = state.get("vetted_problem_index", 0)
    max_iterations = state.get("max_iterations", 5)

    if pivot_requested and vetted_problems:
        # Advance to next vetted problem and start fresh
        new_index = min(current_index + 1, len(vetted_problems) - 1)
        new_direction = vetted_problems[new_index]
        iteration = 1
        current_proposal = None
        feedback = None
        print(f"--- Brainstormer: PIVOT to vetted problem {new_index + 1}/{len(vetted_problems)} "
              f"(iteration {iteration}/{max_iterations}) ---")
        print(f"  New problem: {new_direction[:120]}...")
    else:
        new_index = current_index
        new_direction = None  # Use existing current_direction logic below
        iteration = state.get("phase2_iteration", 0) + 1
        current_proposal = state.get("current_proposal")
        feedback = state.get("consolidated_feedback")
        print(f"--- Brainstormer: Generating proposal (iteration {iteration}/{max_iterations}) ---")

    # Build focused agenda string
    # On pivot, focus tightly on the new vetted problem; otherwise use current_direction
    focus_direction = new_direction or state.get("current_direction", "")
    agenda_items = state.get("agenda", [])
    if focus_direction:
        agenda_str = (
            f"**FOCUS PROBLEM (you MUST base your proposal on this specific problem):**\n"
            f"{focus_direction}\n\n"
            f"Research directions for context:\n" +
            "\n".join(f"- {d}" for d in agenda_items)
        )
    else:
        agenda_str = "\n".join(agenda_items)

    expert_context = state.get(
        "consolidated_expert_context",
        "No cross-field expert synthesis available.",
    )

    if current_proposal and feedback:
        # Revision mode
        prompt = ChatPromptTemplate.from_messages([
            ("system", BRAINSTORMER_SYSTEM),
            ("human", BRAINSTORMER_REVISION_PROMPT)
        ])

        result = invoke_with_structured_output(
            prompt=prompt,
            output_class=ProposalResult,
            inputs={
                "current_proposal": current_proposal,
                "critical_issues": "\n".join(feedback.get("critical_issues", [])),
                "required_fixes": "\n".join(feedback.get("required_fixes", [])),
                "minor_issues": "\n".join(feedback.get("minor_issues", [])),
                "strengths": "\n".join(feedback.get("strengths", [])),
                "paper_summary": state["summary"],
                "mechanisms": state["mechanism"],
                "agenda": agenda_str,
                "expert_context": expert_context,
                "iteration": iteration,
                "max_iterations": max_iterations,
            },
            temperature=0.5,
        )
    else:
        # Initial proposal mode
        prompt = ChatPromptTemplate.from_messages([
            ("system", BRAINSTORMER_SYSTEM),
            ("human", BRAINSTORMER_PROMPT)
        ])

        result = invoke_with_structured_output(
            prompt=prompt,
            output_class=ProposalResult,
            inputs={
                "paper_summary": state["summary"],
                "mechanisms": state["mechanism"],
                "agenda": agenda_str,
                "expert_context": expert_context,
                "feedback": "None - this is the first iteration.",
                "iteration": iteration,
                "max_iterations": max_iterations,
            },
            temperature=0.9,
        )

    # Format proposal as markdown
    proposal_text = f"""# {result.title}

## Problem Statement
{result.problem_statement}

## Motivation
{result.motivation}

## Approach Sketch
{result.approach_sketch}

## Connections to Existing Work
{result.connections}

## Potential Impact
{result.potential_impact}
"""

    print(f"Generated proposal: {result.title}")

    # Save proposal to file if arxiv_id is available
    arxiv_id = state.get("arxiv_id")
    proposal_num = state.get("proposal_num", 1)
    if arxiv_id:
        proposal_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / f"proposal_{proposal_num}" / "proposals"
        proposal_dir.mkdir(parents=True, exist_ok=True)
        proposal_path = proposal_dir / f"proposal_iteration_{iteration}.md"
        proposal_path.write_text(proposal_text, encoding="utf-8")
        print(f"  > Saved proposal to {proposal_path}")

    return {
        "current_proposal": proposal_text,
        "phase2_iteration": iteration,
        "critiques": [],
        "vetted_problem_index": new_index,
        "pivot_requested": False,  # Clear the pivot flag after acting on it
        # Update current_direction when pivoting so subsequent revisions stay on the new problem
        **({"current_direction": new_direction} if new_direction else {}),
        # Reset feedback history on pivot so stagnation detection starts fresh
        **({"feedback_history": []} if pivot_requested else {}),
    }
