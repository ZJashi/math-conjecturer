from typing import TypedDict, NotRequired


class GraphState(TypedDict):
    arxiv_id: str
    tex: NotRequired[str]
    summary: NotRequired[str]