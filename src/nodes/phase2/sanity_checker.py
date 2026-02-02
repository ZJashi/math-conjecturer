"""Sanity Checker node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import CRITIC_SYSTEM, SANITY_CHECKER_PROMPT
from schema.phase2 import Phase2State, CritiqueResult, Critique
from ._common import get_model


def sanity_checker_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 3.2a: Sanity Checker

    Checks logical consistency and assumptions.
    """
    print("--- Sanity Checker: Analyzing logical consistency ---")

    model = get_model()
    prompt = ChatPromptTemplate.from_messages([
        ("system", CRITIC_SYSTEM),
        ("human", SANITY_CHECKER_PROMPT)
    ])

    chain = prompt | model.with_structured_output(CritiqueResult)

    result = chain.invoke({
        "proposal": state["current_proposal"],
        "paper_summary": state["summary"],
        "mechanisms": state["mechanism"],
    })

    print(f"Sanity Checker: Found {len(result.issues)} issues, {len(result.strengths)} strengths")

    critique = Critique(
        source="sanity_checker",
        issues=result.issues,
        strengths=result.strengths,
        suggestions=result.suggestions,
    )

    return {
        "critiques": [critique],
    }
