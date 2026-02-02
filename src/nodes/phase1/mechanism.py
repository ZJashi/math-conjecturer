"""Mechanism node for Phase 1: Extracts mechanism graph from summary."""

from pathlib import Path

from prompts.phase1 import (
    MECHANISM_EXTRACTOR_SYSTEM_PROMPT,
    MECHANISM_EXTRACTOR_USER_PROMPT,
)
from schema.phase1 import GraphState
from utils.openrouter import call_openrouter

# Project root directory (outside src/)
BASE_DIR = Path(__file__).resolve().parents[3]
PAPERS_DIR = BASE_DIR / "papers"


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

    # Save mechanism to papers/{arxiv_id}/step3_mechanism/mechanism.xml
    paper_id = state["arxiv_id"]
    mechanism_dir = PAPERS_DIR / paper_id / "step3_mechanism"
    mechanism_dir.mkdir(parents=True, exist_ok=True)

    mechanism_path = mechanism_dir / "mechanism.xml"
    mechanism_path.write_text(mechanism_xml, encoding="utf-8")

    return {
        **state,
        "mechanism": mechanism_xml,
    }
