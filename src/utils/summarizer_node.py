from pathlib import Path

from prompts.paper_summarizer import (
    CONTEXT_EXTRACTOR_SYSTEM_PROMPT,
    CONTEXT_EXTRACTOR_USER_PROMPT,
)

from .graph_state import GraphState
from .openrouter import call_openrouter

# Project root directory (outside src/)
BASE_DIR = Path(__file__).resolve().parents[2]
PAPERS_DIR = BASE_DIR / "papers"


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

    summary = call_openrouter(messages, temperature=0.0)

    paper_id = state["arxiv_id"]
    iteration = state.get("iteration", 1)

    # Save summary to papers/{arxiv_id}/summary/iteration_1.md
    summary_dir = PAPERS_DIR / paper_id / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)

    summary_path = summary_dir / f"iteration_{iteration}.md"
    summary_path.write_text(summary, encoding="utf-8")

    return {
        **state,
        "summary": summary,
    }
