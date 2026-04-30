"""Agenda Creator node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import AGENDA_CREATOR_SYSTEM, AGENDA_CREATOR_PROMPT
from schema.phase2 import Phase2State, AgendaResult
from ._common import invoke_with_structured_output, save_json, save_text


def agenda_creator_node(state: Phase2State) -> Dict[str, Any]:
    print("--- Agenda Creator: Generating research directions ---")

    prompt = ChatPromptTemplate.from_messages([("system", AGENDA_CREATOR_SYSTEM), ("human", AGENDA_CREATOR_PROMPT)])
    result = invoke_with_structured_output(
        prompt=prompt, output_class=AgendaResult,
        inputs={"paper_summary": state["summary"], "mechanisms": state["mechanism"]},
        temperature=0.8,
    )

    subfields = result.subfields[:4]
    print(f"Generated {len(result.research_directions)} directions, {len(subfields)} subfields:")
    for i, sf in enumerate(subfields, 1):
        print(f"  {i}. {sf}")

    rel_dir = "step4_open_problems/4a_agenda"
    agenda_md = "# Research Agenda\n\n## Rationale\n" + result.rationale + "\n\n## Research Directions\n\n"
    agenda_md += "".join(f"### Direction {i}\n{d}\n\n" for i, d in enumerate(result.research_directions, 1))
    agenda_md += "## Expert Subfields\n\n" + "".join(f"{i}. {sf}\n" for i, sf in enumerate(subfields, 1))

    save_text(state, rel_dir, "agenda.md", agenda_md)
    save_json(state, rel_dir, "agenda.json", {
        "research_directions": result.research_directions,
        "subfields": subfields,
        "rationale": result.rationale,
    })

    return {"agenda": result.research_directions, "subfields": subfields}
