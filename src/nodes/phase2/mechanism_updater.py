"""Mechanism Updater node for Phase 2."""

import re
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2.mechanism_updater import MECHANISM_UPDATER_SYSTEM, MECHANISM_UPDATER_PROMPT
from schema.phase2 import Phase2State
from ._common import call_openrouter_direct, save_text


def _parse_report_sections(report: str) -> Dict[str, str]:
    sections, current_key, current_lines = {}, None, []
    for line in report.split("\n"):
        m = re.match(r'^#{1,2}\s+(.+)$', line)
        if m:
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = m.group(1).strip().lower().replace(" ", "_")
            current_lines = []
        else:
            current_lines.append(line)
    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()
    return sections


def mechanism_updater_node(state: Phase2State) -> Dict[str, Any]:
    print("--- Mechanism Updater: Adding traceability to mechanism XML ---")

    sections = _parse_report_sections(state.get("final_report", ""))
    prompt = ChatPromptTemplate.from_messages([("system", MECHANISM_UPDATER_SYSTEM), ("human", MECHANISM_UPDATER_PROMPT)])
    messages = [
        {"role": "user" if msg.type == "human" else msg.type, "content": msg.content}
        for msg in prompt.format_messages(
            mechanism=state["mechanism"],
            problem_statement=sections.get("problem_statement", ""),
            potential_impact=sections.get("potential_impact", ""),
            direction=state.get("current_direction", ""),
        )
    ]

    response_text = call_openrouter_direct(messages, temperature=0.3)
    updated_xml = re.sub(r'^```(?:xml)?\s*', '', response_text.strip())
    updated_xml = re.sub(r'\s*```$', '', updated_xml)
    print(f"  Updated mechanism XML ({len(updated_xml)} chars)")

    save_text(state, f"step4_open_problems/proposal_{state.get('proposal_num', 1)}", "mechanism_updated.xml", updated_xml)
    return {"updated_mechanism": updated_xml}
