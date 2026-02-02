from pathlib import Path

from prompts.paper_summarizer import (
    CONTEXT_EXTRACTOR_REVISION_SYSTEM_PROMPT,
    CONTEXT_EXTRACTOR_REVISION_USER_PROMPT,
)

from .graph_state import GraphState
from .openrouter import call_openrouter

# Project root directory (outside src/)
BASE_DIR = Path(__file__).resolve().parents[2]
PAPERS_DIR = BASE_DIR / "papers"


def revision_node(state: GraphState) -> GraphState:
    """
    Revises the summary based on the critique from the critic node.
    """
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

    revised_summary = call_openrouter(messages, temperature=0.0)

    # Increment iteration for the new summary
    new_iteration = state.get("iteration", 1) + 1

    # Save revised summary to papers/{arxiv_id}/step2_summary/iteration_X.md
    paper_id = state["arxiv_id"]
    summary_dir = PAPERS_DIR / paper_id / "step2_summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    summary_path = summary_dir / f"iteration_{new_iteration}.md"
    summary_path.write_text(revised_summary, encoding="utf-8")

    return {
        **state,
        "summary": revised_summary,
        "iteration": new_iteration,
    }
