"""Critic node for Phase 1: Evaluates summary quality."""

import re

from prompts.phase1 import (
    SUMMARIZER_CRITIC_SYSTEM_PROMPT,
    SUMMARIZER_CRITIC_USER_PROMPT,
)
from schema.phase1 import GraphState
from utils.openrouter import call_openrouter
from utils.io import save_text


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

    status = "NEEDS_REVISION"
    status_match = re.search(
        r"\*\*STATUS:\*\*\s*(PASS|NEEDS_REVISION)",
        critique_response,
        re.IGNORECASE,
    )
    if status_match:
        status = status_match.group(1).upper()

    save_text(state, "step2_critique", f"iteration_{iteration}.md", critique_response)

    return {
        **state,
        "critique": critique_response,
        "critic_status": status,
        "iteration": iteration,
    }
