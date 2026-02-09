"""Agenda Creator node for Phase 2."""

import json
from typing import Any, Dict
from langchain_core.prompts import ChatPromptTemplate
from prompts.phase2 import AGENDA_CREATOR_SYSTEM, AGENDA_CREATOR_PROMPT
from schema.phase2 import Phase2State, AgendaResult
from ._common import PAPERS_DIR, invoke_with_structured_output


def agenda_creator_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 2: Agenda Creator
    Generates high-level research directions based on the paper summary
    and mechanism from Phase 1.
    """
    print("--- Agenda Creator: Generating research directions ---")

    prompt = ChatPromptTemplate.from_messages([
        ("system", AGENDA_CREATOR_SYSTEM),
        ("human", AGENDA_CREATOR_PROMPT)
    ])

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=AgendaResult,
        inputs={
            "paper_summary": state["summary"],
            "mechanisms": state["mechanism"],
        },
        temperature=0.8,
    )

    print(f"Generated {len(result.research_directions)} research directions")
    for i, direction in enumerate(result.research_directions, 1):
        print(f"  {i}. {direction[:80]}...")

    # Save agenda to file if arxiv_id is available
    arxiv_id = state.get("arxiv_id")
    if arxiv_id:
        agenda_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / "4a_agenda"
        agenda_dir.mkdir(parents=True, exist_ok=True)

        # Save as markdown
        agenda_md = "# Research Agenda\n\n"
        agenda_md += f"## Rationale\n{result.rationale}\n\n"
        agenda_md += "## Research Directions\n\n"
        for i, direction in enumerate(result.research_directions, 1):
            agenda_md += f"### Direction {i}\n{direction}\n\n"

        agenda_path = agenda_dir / "agenda.md"
        agenda_path.write_text(agenda_md, encoding="utf-8")
        print(f"  > Saved agenda to {agenda_path}")

        # Also save as JSON for programmatic access
        agenda_json = {
            "research_directions": result.research_directions,
            "rationale": result.rationale,
        }
        json_path = agenda_dir / "agenda.json"
        json_path.write_text(json.dumps(agenda_json, indent=2), encoding="utf-8")

    return {
        "agenda": result.research_directions,
    }
