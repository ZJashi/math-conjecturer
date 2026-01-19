from langgraph.graph import StateGraph, START, END
from .graph_state import GraphState
from .ingestion_node import ingestion_node
from .summarizer_node import summarizer_node


def build_app():
    graph = StateGraph(GraphState)

    # Nodes
    graph.add_node("ingest", ingestion_node)
    graph.add_node("summarize", summarizer_node)

    # Edges
    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()
