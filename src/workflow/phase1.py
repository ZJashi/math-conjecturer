"""
Phase 1: Paper Processing LangGraph Workflow

Pipeline: ingest → summarize → critic → mechanism → END
The critic revision loop is handled externally in app.py for Chainlit user interaction.
"""

from langgraph.graph import END, START, StateGraph

from schema.phase1 import GraphState
from nodes.phase1 import (
    ingestion_node,
    summarizer_node,
    critic_node,
    mechanism_node,
)


def build_phase1_workflow():
    """
    Builds the Phase 1 pipeline: ingest → summarize → critic → mechanism → END

    The critic revision loop is handled externally in app.py for
    Chainlit user interaction.

    Returns:
        Compiled LangGraph workflow
    """
    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("ingest", ingestion_node)
    graph.add_node("summarize", summarizer_node)
    graph.add_node("critic", critic_node)
    graph.add_node("mechanism", mechanism_node)

    # Add edges
    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "summarize")
    graph.add_edge("summarize", "critic")
    graph.add_edge("critic", "mechanism")
    graph.add_edge("mechanism", END)

    return graph.compile()


# Convenience alias
build_app = build_phase1_workflow
