from typing import TypedDict, NotRequired, Literal


class GraphState(TypedDict):
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