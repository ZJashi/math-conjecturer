"""Reverse Reasoner node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import CRITIC_SYSTEM, REVERSE_REASONER_PROMPT
from schema.phase2 import Phase2State, CritiqueResult, Critique
from ._common import get_model


def reverse_reasoner_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 3.2c: Reverse Reasoner

    Assumes proposal is wrong and finds failure points.
    """
    print("--- Reverse Reasoner: Playing devil's advocate ---")

    model = get_model()
    prompt = ChatPromptTemplate.from_messages([
        ("system", CRITIC_SYSTEM),
        ("human", REVERSE_REASONER_PROMPT)
    ])

    chain = prompt | model.with_structured_output(CritiqueResult)

    result = chain.invoke({
        "proposal": state["current_proposal"],
        "paper_summary": state["summary"],
        "mechanisms": state["mechanism"],
    })

    print(f"Reverse Reasoner: Found {len(result.issues)} issues, {len(result.strengths)} strengths")

    critique = Critique(
        source="reverse_reasoner",
        issues=result.issues,
        strengths=result.strengths,
        suggestions=result.suggestions,
    )

    return {
        "critiques": [critique],
    }
