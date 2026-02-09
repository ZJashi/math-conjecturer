"""Feedback Consolidator node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import FEEDBACK_CONSOLIDATOR_SYSTEM, FEEDBACK_CONSOLIDATOR_PROMPT
from schema.phase2 import Phase2State, ConsolidatedFeedbackResult, ConsolidatedFeedback, Critique
from ._common import PAPERS_DIR, invoke_with_structured_output


def _format_critique(c: Critique) -> str:
    """Format a critique for the prompt."""
    return f"""
**Issues:** {chr(10).join(f'- {issue}' for issue in c['issues']) if c['issues'] else 'None identified'}

**Strengths:** {chr(10).join(f'- {s}' for s in c['strengths']) if c['strengths'] else 'None identified'}

**Suggestions:** {chr(10).join(f'- {s}' for s in c['suggestions']) if c['suggestions'] else 'None'}
"""


def feedback_consolidator_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 3.3: Feedback Consolidator

    Merges all critiques into a single structured feedback object.
    """
    print("--- Feedback Consolidator: Merging critiques ---")

    critiques = state.get("critiques", [])

    # Find each critic's feedback
    sanity = next((c for c in critiques if c["source"] == "sanity_checker"), None)
    example = next((c for c in critiques if c["source"] == "example_tester"), None)
    reverse = next((c for c in critiques if c["source"] == "reverse_reasoner"), None)
    obstruction = next((c for c in critiques if c["source"] == "obstruction_analyzer"), None)

    prompt = ChatPromptTemplate.from_messages([
        ("system", FEEDBACK_CONSOLIDATOR_SYSTEM),
        ("human", FEEDBACK_CONSOLIDATOR_PROMPT)
    ])

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=ConsolidatedFeedbackResult,
        inputs={
            "sanity_critique": _format_critique(sanity) if sanity else "No critique available",
            "example_critique": _format_critique(example) if example else "No critique available",
            "reverse_critique": _format_critique(reverse) if reverse else "No critique available",
            "obstruction_critique": _format_critique(obstruction) if obstruction else "No critique available",
        },
        temperature=0.1,
    )

    consolidated = ConsolidatedFeedback(
        critical_issues=result.critical_issues,
        minor_issues=result.minor_issues,
        strengths=result.strengths,
        required_fixes=result.required_fixes,
        overall_assessment=result.overall_assessment,
    )

    print(f"Consolidated: {len(result.critical_issues)} critical, {len(result.minor_issues)} minor issues")

    # Save consolidated feedback to file if arxiv_id is available
    arxiv_id = state.get("arxiv_id")
    iteration = state.get("phase2_iteration", 1)
    proposal_num = state.get("proposal_num", 1)
    if arxiv_id:
        feedback_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / f"proposal_{proposal_num}" / "feedback"
        feedback_dir.mkdir(parents=True, exist_ok=True)

        feedback_md = f"""# Consolidated Feedback (Iteration {iteration})

## Overall Assessment
{result.overall_assessment}

## Critical Issues (Must Fix)
{chr(10).join(f'- {issue}' for issue in result.critical_issues) if result.critical_issues else '- None'}

## Minor Issues (Nice to Fix)
{chr(10).join(f'- {issue}' for issue in result.minor_issues) if result.minor_issues else '- None'}

## Strengths (Preserve)
{chr(10).join(f'- {s}' for s in result.strengths) if result.strengths else '- None'}

## Required Fixes (Priority Order)
{chr(10).join(f'{i+1}. {fix}' for i, fix in enumerate(result.required_fixes)) if result.required_fixes else '- None'}
"""
        feedback_path = feedback_dir / f"consolidated_iteration_{iteration}.md"
        feedback_path.write_text(feedback_md, encoding="utf-8")
        print(f"  > Saved feedback to {feedback_path}")

    return {
        "consolidated_feedback": consolidated,
    }
