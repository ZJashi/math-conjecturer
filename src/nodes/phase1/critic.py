"""Critic node for Phase 1: Evaluates summary quality."""

import re
from pathlib import Path

from prompts.phase1 import (
    SUMMARIZER_CRITIC_SYSTEM_PROMPT,
    SUMMARIZER_CRITIC_USER_PROMPT,
)
from schema.phase1 import GraphState
from utils.openrouter import call_openrouter

# Project root directory (outside src/)
BASE_DIR = Path(__file__).resolve().parents[3]
PAPERS_DIR = BASE_DIR / "papers"


def critic_node(state: GraphState) -> GraphState:
    """
    Evaluates the summary and determines if it needs revision.
    Returns status (PASS/NEEDS_REVISION) and critique.
    """
    iteration = state.get("iteration", 1)

    messages = [
        {
            "role": "system",
            "content": SUMMARIZER_CRITIC_SYSTEM_PROMPT.strip(),
        },
        {
            "role": "user",
            "content": SUMMARIZER_CRITIC_USER_PROMPT.format(
                input_paper=state["tex"],
                summary=state["summary"],
            ),
        },
    ]

    critique_response = call_openrouter(messages, temperature=0.0)

    # Parse the status from the critique response
    # Look for **STATUS:** PASS or **STATUS:** NEEDS_REVISION
    status = "NEEDS_REVISION"  # Default to needing revision
    status_match = re.search(
        r"\*\*STATUS:\*\*\s*(PASS|NEEDS_REVISION)",
        critique_response,
        re.IGNORECASE
    )
    if status_match:
        status = status_match.group(1).upper()

    # Save critique to papers/{arxiv_id}/step2_critique/iteration_X.md
    paper_id = state["arxiv_id"]
    critique_dir = PAPERS_DIR / paper_id / "step2_critique"
    critique_dir.mkdir(parents=True, exist_ok=True)

    critique_path = critique_dir / f"iteration_{iteration}.md"
    critique_path.write_text(critique_response, encoding="utf-8")

    return {
        **state,
        "critique": critique_response,
        "critic_status": status,
        "iteration": iteration,
    }
