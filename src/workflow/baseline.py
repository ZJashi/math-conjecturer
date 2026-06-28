"""Baseline workflow: ingest → single few-shot proposer."""

from langgraph.graph import END, START, StateGraph

from schema.state import GraphState
from nodes import ingestion_node, baseline_proposer_node, baseline_evaluator_node


def build_baseline_workflow():
    graph = StateGraph(GraphState)
    graph.add_node("ingest", ingestion_node)
    graph.add_node("propose", baseline_proposer_node)
    graph.add_node("evaluate", baseline_evaluator_node)
    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "propose")
    graph.add_edge("propose", "evaluate")
    graph.add_edge("evaluate", END)
    return graph.compile()
