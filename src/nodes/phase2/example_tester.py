"""Example Tester node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import CRITIC_SYSTEM, EXAMPLE_TESTER_PROMPT
from schema.phase2 import Phase2State, CritiqueResult, Critique
from ._common import PAPERS_DIR, invoke_with_structured_output


def example_tester_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 3.2b: Example Tester

    Tests the proposal with concrete examples and counterexamples.
    """
    print("--- Example Tester: Testing with concrete examples ---")

    prompt = ChatPromptTemplate.from_messages([
        ("system", CRITIC_SYSTEM),
        ("human", EXAMPLE_TESTER_PROMPT)
    ])

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=CritiqueResult,
        inputs={
            "proposal": state["current_proposal"],
            "paper_summary": state["summary"],
            "mechanisms": state["mechanism"],
        },
        temperature=0.5,
    )

    print(f"Example Tester: Found {len(result.issues)} issues, {len(result.strengths)} strengths")

    critique = Critique(
        source="example_tester",
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

        critique_md = f"""# Example Tester Critique (Iteration {iteration})

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
        critique_path = critique_dir / "example_tester.md"
        critique_path.write_text(critique_md, encoding="utf-8")
        print(f"  > Saved critique to {critique_path}")

    return {
        "critiques": [critique],
    }
