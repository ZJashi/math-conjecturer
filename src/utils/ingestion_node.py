from ingest.ingestion_pipeline import pipeline

from .graph_state import GraphState

def ingestion_node(state: GraphState) -> GraphState:
    arxiv_id = state["arxiv_id"]
    latex_doc = pipeline(arxiv_id)

    return { **state,
             "tex": latex_doc}
