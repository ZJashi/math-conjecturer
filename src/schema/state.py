from typing import NotRequired, TypedDict


class GraphState(TypedDict):
    arxiv_id: str
    tex: NotRequired[str]
    proposals: NotRequired[list]
    evaluations: NotRequired[list]
