"""Phase 1 State Definition: Paper processing pipeline."""

from typing import Literal, NotRequired, TypedDict


class GraphState(TypedDict):
    """
    State for Phase 1: Paper ingestion, summarization, and mechanism extraction.

    This state flows through the nodes:
    ingestion → summarizer → critic → (revision loop) → mechanism
    """
    arxiv_id: str
    tex: NotRequired[str]
    summary: NotRequired[str]
    # Critic loop fields
    critique: NotRequired[str]
    critic_status: NotRequired[Literal["PASS", "NEEDS_REVISION"]]
    iteration: NotRequired[int]
    user_wants_to_continue: NotRequired[bool]
    # Mechanism extraction
    mechanism: NotRequired[str]
