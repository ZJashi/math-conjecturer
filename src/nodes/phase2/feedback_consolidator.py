"""Feedback Consolidator node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import BASE_SYSTEM_PROMPT, FEEDBACK_CONSOLIDATOR_PROMPT
from schema.phase2 import Phase2State, ConsolidatedFeedbackResult, ConsolidatedFeedback, Critique
from ._common import get_model


def _format_critique(c: Critique) -> str:
    """Format a critique for the prompt."""
    return f"""
**Issues:** {', '.join(c['issues']) if c['issues'] else 'None identified'}
**Strengths:** {', '.join(c['strengths']) if c['strengths'] else 'None identified'}
**Suggestions:** {', '.join(c['suggestions']) if c['suggestions'] else 'None'}
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

    model = get_model()
    prompt = ChatPromptTemplate.from_messages([
        ("system", BASE_SYSTEM_PROMPT),
        ("human", FEEDBACK_CONSOLIDATOR_PROMPT)
    ])

    chain = prompt | model.with_structured_output(ConsolidatedFeedbackResult)

    result = chain.invoke({
        "sanity_critique": _format_critique(sanity) if sanity else "No critique available",
        "example_critique": _format_critique(example) if example else "No critique available",
        "reverse_critique": _format_critique(reverse) if reverse else "No critique available",
        "obstruction_critique": _format_critique(obstruction) if obstruction else "No critique available",
    })

    consolidated = ConsolidatedFeedback(
        critical_issues=result.critical_issues,
        minor_issues=result.minor_issues,
        strengths=result.strengths,
        required_fixes=result.required_fixes,
        overall_assessment=result.overall_assessment,
    )

    print(f"Consolidated: {len(result.critical_issues)} critical, {len(result.minor_issues)} minor issues")

    return {
        "consolidated_feedback": consolidated,
    }
