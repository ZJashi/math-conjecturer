"""Example Tester node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import CRITIC_SYSTEM, EXAMPLE_TESTER_PROMPT
from schema.phase2 import Phase2State, CritiqueResult, Critique
from ._common import get_model


def example_tester_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 3.2b: Example Tester

    Tests proposal with concrete/toy examples.
    """
    print("--- Example Tester: Testing with examples ---")

    model = get_model()
    prompt = ChatPromptTemplate.from_messages([
        ("system", CRITIC_SYSTEM),
        ("human", EXAMPLE_TESTER_PROMPT)
    ])

    chain = prompt | model.with_structured_output(CritiqueResult)

    result = chain.invoke({
        "proposal": state["current_proposal"],
        "paper_summary": state["summary"],
        "mechanisms": state["mechanism"],
    })

    print(f"Example Tester: Found {len(result.issues)} issues, {len(result.strengths)} strengths")

    critique = Critique(
        source="example_tester",
        issues=result.issues,
        strengths=result.strengths,
        suggestions=result.suggestions,
    )

    return {
        "critiques": [critique],
    }
