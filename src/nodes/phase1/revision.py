"""Revision node for Phase 1: Revises summary based on critique."""

from prompts.phase1 import (
    CONTEXT_EXTRACTOR_REVISION_SYSTEM_PROMPT,
    CONTEXT_EXTRACTOR_REVISION_USER_PROMPT,
)
from schema.phase1 import GraphState
from utils.openrouter import call_openrouter
from utils.io import save_text


def revision_node(state: GraphState) -> GraphState:
    """Revises the summary based on the critique from the critic node."""
    messages = [
        {
            "role": "system",
            "content": CONTEXT_EXTRACTOR_REVISION_SYSTEM_PROMPT.strip(),
        },
        {
            "role": "user",
            "content": CONTEXT_EXTRACTOR_REVISION_USER_PROMPT.format(
                input_paper=state["tex"],
                previous_summary=state["summary"],
                expert_critique=state["critique"],
            ),
        },
    ]

    revised_summary = call_openrouter(messages, temperature=0.4)

    new_iteration = state.get("iteration", 1) + 1
    save_text(state, "step2_summary", f"iteration_{new_iteration}.md", revised_summary)

    return {
        **state,
        "summary": revised_summary,
        "iteration": new_iteration,
    }
