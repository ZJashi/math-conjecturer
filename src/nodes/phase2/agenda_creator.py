"""Agenda Creator node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import AGENDA_CREATOR_SYSTEM, AGENDA_CREATOR_PROMPT
from schema.phase2 import Phase2State, AgendaResult
from ._common import get_model


def agenda_creator_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 2: Agenda Creator

    Generates high-level research directions based on the paper summary
    and mechanism from Phase 1.
    """
    print("--- Agenda Creator: Generating research directions ---")

    model = get_model()
    prompt = ChatPromptTemplate.from_messages([
        ("system", AGENDA_CREATOR_SYSTEM),
        ("human", AGENDA_CREATOR_PROMPT)
    ])

    chain = prompt | model.with_structured_output(AgendaResult)

    result = chain.invoke({
        "paper_summary": state["summary"],
        "mechanisms": state["mechanism"],
    })

    print(f"Generated {len(result.research_directions)} research directions")
    for i, direction in enumerate(result.research_directions, 1):
        print(f"  {i}. {direction[:80]}...")

    return {
        "agenda": result.research_directions,
    }
