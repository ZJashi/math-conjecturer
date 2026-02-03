"""Ingestion node for Phase 1: Downloads and processes LaTeX from arXiv."""

from utils.ingest.ingestion_pipeline import pipeline
from schema.phase1 import GraphState


def ingestion_node(state: GraphState) -> GraphState:
    """Download and process LaTeX from arXiv."""
    arxiv_id = state["arxiv_id"]
    latex_doc = pipeline(arxiv_id)

    return {**state,
            "tex": latex_doc}
