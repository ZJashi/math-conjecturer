"""Baseline workflow: ingest → single few-shot proposer."""

from langgraph.graph import END, START, StateGraph

from schema.state import GraphState
from nodes import ingestion_node, baseline_proposer_node


def build_baseline_workflow():
    graph = StateGraph(GraphState)
    graph.add_node("ingest", ingestion_node)
    graph.add_node("propose", baseline_proposer_node)
    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "propose")
    graph.add_edge("propose", END)
    return graph.compile()
