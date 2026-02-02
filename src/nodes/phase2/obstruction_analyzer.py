"""Obstruction Analyzer node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import CRITIC_SYSTEM, OBSTRUCTION_ANALYZER_PROMPT
from schema.phase2 import Phase2State, CritiqueResult, Critique
from ._common import get_model


def obstruction_analyzer_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 3.2d: Obstruction Analyzer

    Identifies practical, theoretical, or implementation blockers.
    """
    print("--- Obstruction Analyzer: Identifying barriers ---")

    model = get_model()
    prompt = ChatPromptTemplate.from_messages([
        ("system", CRITIC_SYSTEM),
        ("human", OBSTRUCTION_ANALYZER_PROMPT)
    ])

    chain = prompt | model.with_structured_output(CritiqueResult)

    result = chain.invoke({
        "proposal": state["current_proposal"],
        "paper_summary": state["summary"],
        "mechanisms": state["mechanism"],
    })

    print(f"Obstruction Analyzer: Found {len(result.issues)} issues, {len(result.strengths)} strengths")

    critique = Critique(
        source="obstruction_analyzer",
        issues=result.issues,
        strengths=result.strengths,
        suggestions=result.suggestions,
    )

    return {
        "critiques": [critique],
    }
