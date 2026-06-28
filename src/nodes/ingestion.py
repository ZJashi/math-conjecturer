"""Ingestion node: Downloads and processes LaTeX from arXiv."""

from utils.ingest.ingestion_pipeline import pipeline
from schema.state import GraphState


def ingestion_node(state: GraphState) -> dict:
    """Download and process LaTeX from arXiv."""
    arxiv_id = state["arxiv_id"]
    latex_doc = pipeline(arxiv_id)

    return {"tex": latex_doc}
