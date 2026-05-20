"""Summarizer node for Phase 1: Generates paper summary."""

from prompts.phase1 import CONTEXT_EXTRACTOR_SYSTEM_PROMPT, CONTEXT_EXTRACTOR_USER_PROMPT
from schema.phase1 import GraphState
from utils.openrouter import call_openrouter
from utils.io import save_text


def summarizer_node(state: GraphState) -> GraphState:
    """Generate initial summary (iteration 1)."""
    messages = [
        {
            "role": "system",
            "content": CONTEXT_EXTRACTOR_SYSTEM_PROMPT.strip(),
        },
        {
            "role": "user",
            "content": CONTEXT_EXTRACTOR_USER_PROMPT.format(
                input_paper=state["tex"]
            ),
        },
    ]

    summary = call_openrouter(messages, temperature=0.1)

    iteration = state.get("iteration", 1)
    save_text(state, "step2_summary", f"iteration_{iteration}.md", summary)

    return {
        **state,
        "summary": summary,
    }
