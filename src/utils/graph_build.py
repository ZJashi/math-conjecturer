from langgraph.graph import END, START, StateGraph

from .graph_state import GraphState
from .ingestion_node import ingestion_node
from .summarizer_node import summarizer_node
from .critic_node import critic_node


def build_app():
    """
    Builds the main pipeline: ingest → summarize → critic → END
    The critic loop is handled externally in app.py for Chainlit user interaction.
    """
    graph = StateGraph(GraphState)

    # Nodes
    graph.add_node("ingest", ingestion_node)
    graph.add_node("summarize", summarizer_node)
    graph.add_node("critic", critic_node)

    # Edges
    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "summarize")
    graph.add_edge("summarize", "critic")
    graph.add_edge("critic", END)

    return graph.compile()

