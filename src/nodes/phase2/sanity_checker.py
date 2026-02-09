"""Sanity Checker node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import CRITIC_SYSTEM, SANITY_CHECKER_PROMPT
from schema.phase2 import Phase2State, CritiqueResult, Critique
from ._common import PAPERS_DIR, invoke_with_structured_output


def sanity_checker_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 3.2a: Sanity Checker

    Checks logical consistency and assumptions.
    """
    print("--- Sanity Checker: Analyzing logical consistency ---")

    prompt = ChatPromptTemplate.from_messages([
        ("system", CRITIC_SYSTEM),
        ("human", SANITY_CHECKER_PROMPT)
    ])

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=CritiqueResult,
        inputs={
            "proposal": state["current_proposal"],
            "paper_summary": state["summary"],
            "mechanisms": state["mechanism"],
        }
    )

    print(f"Sanity Checker: Found {len(result.issues)} issues, {len(result.strengths)} strengths")

    critique = Critique(
        source="sanity_checker",
        issues=result.issues,
        strengths=result.strengths,
        suggestions=result.suggestions,
    )

    # Save critique to file if arxiv_id is available
    arxiv_id = state.get("arxiv_id")
    iteration = state.get("phase2_iteration", 1)
    proposal_num = state.get("proposal_num", 1)
    if arxiv_id:
        critique_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / f"proposal_{proposal_num}" / "critiques" / f"iteration_{iteration}"
        critique_dir.mkdir(parents=True, exist_ok=True)

        critique_md = f"""# Sanity Checker Critique (Iteration {iteration})

## Summary
{result.summary}

## Severity: {result.severity}

## Issues Found
{chr(10).join(f'- {issue}' for issue in result.issues) if result.issues else '- None'}

## Strengths Identified
{chr(10).join(f'- {s}' for s in result.strengths) if result.strengths else '- None'}

## Suggestions
{chr(10).join(f'- {s}' for s in result.suggestions) if result.suggestions else '- None'}
"""
        critique_path = critique_dir / "sanity_checker.md"
        critique_path.write_text(critique_md, encoding="utf-8")
        print(f"  > Saved critique to {critique_path}")

    return {
        "critiques": [critique],
    }
