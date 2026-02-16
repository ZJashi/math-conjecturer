"""Mechanism Updater node for Phase 2."""

import re
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2.mechanism_updater import (
    MECHANISM_UPDATER_SYSTEM,
    MECHANISM_UPDATER_PROMPT,
)
from schema.phase2 import Phase2State
from ._common import PAPERS_DIR, call_openrouter_direct


def mechanism_updater_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node: Mechanism Updater

    Updates the mechanism XML with new proposed_problem elements
    that trace back to existing context/motivation elements.
    """
    print("--- Mechanism Updater: Adding traceability to mechanism XML ---")

    # Parse the final report sections from markdown
    report = state.get("final_report", "")
    sections = _parse_report_sections(report)

    prompt = ChatPromptTemplate.from_messages([
        ("system", MECHANISM_UPDATER_SYSTEM),
        ("human", MECHANISM_UPDATER_PROMPT),
    ])

    formatted = prompt.format_messages(
        mechanism=state["mechanism"],
        problem_statement=sections.get("problem_statement", ""),
        proposed_approach=sections.get("proposed_approach", ""),
        expected_challenges=sections.get("expected_challenges", ""),
        potential_impact=sections.get("potential_impact", ""),
        direction=state.get("current_direction", ""),
    )

    messages = []
    for msg in formatted:
        role = "user" if msg.type == "human" else msg.type
        messages.append({"role": role, "content": msg.content})

    response_text = call_openrouter_direct(messages, temperature=0.3)

    # Strip markdown code fences if present
    updated_xml = response_text.strip()
    updated_xml = re.sub(r'^```(?:xml)?\s*', '', updated_xml)
    updated_xml = re.sub(r'\s*```$', '', updated_xml)

    print(f"  Updated mechanism XML ({len(updated_xml)} chars)")

    # Save to file
    arxiv_id = state.get("arxiv_id")
    proposal_num = state.get("proposal_num", 1)
    if arxiv_id:
        out_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / f"proposal_{proposal_num}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "mechanism_updated.xml"
        out_path.write_text(updated_xml, encoding="utf-8")
        print(f"  > Saved updated mechanism to {out_path}")

    return {
        "updated_mechanism": updated_xml,
    }


def _parse_report_sections(report: str) -> Dict[str, str]:
    """Parse the markdown report into sections."""
    sections = {}
    current_key = None
    current_lines = []

    for line in report.split("\n"):
        header_match = re.match(r'^#{1,2}\s+(.+)$', line)
        if header_match:
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            title = header_match.group(1).strip()
            current_key = title.lower().replace(" ", "_")
            current_lines = []
        else:
            current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections
