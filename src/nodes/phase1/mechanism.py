"""Mechanism node for Phase 1: Extracts mechanism graph from summary."""

from prompts.phase1 import (
    MECHANISM_EXTRACTOR_SYSTEM_PROMPT,
    MECHANISM_EXTRACTOR_USER_PROMPT,
)
from schema.phase1 import GraphState
from utils.openrouter import call_openrouter
from utils.io import save_text


def mechanism_node(state: GraphState) -> GraphState:
    """
    Extracts the core mechanisms from the paper summary as an XML document.
    Input: Paper summary
    Output: XML document recording the mechanism graph
    """
    messages = [
        {
            "role": "system",
            "content": MECHANISM_EXTRACTOR_SYSTEM_PROMPT.strip(),
        },
        {
            "role": "user",
            "content": MECHANISM_EXTRACTOR_USER_PROMPT.format(
                paper_summary=state["summary"],
            ),
        },
    ]

    mechanism_xml = call_openrouter(messages, temperature=0.0)

    save_text(state, "step3_mechanism", "mechanism.xml", mechanism_xml)

    return {
        **state,
        "mechanism": mechanism_xml,
    }
