import operator
import os
from pathlib import Path
from typing import List, TypedDict, Annotated, Literal, Callable
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from schema import Proposal


# --- 2. Define Agent Nodes and Edges ---
# Note: The implementation of the nodes is in agents.py
# Here, we just import them and wire them up.

from .agents import (
    set_agenda_node,
    create_specialist_node,
    scrutinize_and_update_node,
    generate_summary_node
)

def should_continue(state: GraphState) -> Literal["continue", "end"]:
    """Conditional edge to decide whether to loop or end."""
    print(f"--- Checking Round: {state['round_number']} / {state['max_rounds']} ---")
    if state['round_number'] < state['max_rounds']:
        return "continue"
    else:
        return "end"

# --- 3. Create the Graph ---

def create_workflow_graph(subfields: List[str]) -> CompiledStateGraph:
    """Builds and compiles the multi-agent graph.
    Args:
        subfields (List[str]): List of specialized subfields to involve.
    Returns:
        The compiled multi-agent workflow graph.
    """
    
    # Create specialist agent nodes
    specialist_agent_nodes = []
    SA_names = [f"{subfield.title().replace(' ', '')}Agent" 
                for subfield in subfields]
    for sa_name, subfield in zip(SA_names, subfields):
        node = create_specialist_node(
            specialty=subfield,
            agent_name=sa_name
        )
        specialist_agent_nodes.append(node)

    # Define the graph
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("set_agenda", set_agenda_node)
    for name, node in zip(SA_names, specialist_agent_nodes):
        workflow.add_node(name, node)
    workflow.add_node("scrutinize_and_update", scrutinize_and_update_node)
    workflow.add_node("generate_summary", generate_summary_node)
    
    # --- 4. Define the Edges ---
    
    # Start of the process
    workflow.set_entry_point("set_agenda")
    
    # # This is for parallel execution of SAs
    # After the agenda is set, all SAs run in parallel.
    for sa_name in SA_names:
        workflow.add_edge("set_agenda", sa_name)
    # After all SAs have run (this is the join),
    # the CA scrutinizes the collected proposals.
    workflow.add_edge(SA_names, "scrutinize_and_update")
 
    # # # This is for sequential execution of SAs
    # # After the agenda is set, all SAs run sequentially.
    # previous_node = "set_agenda"
    # for sa_name in SA_names:
    #     workflow.add_edge(previous_node, sa_name)
    #     previous_node = sa_name
    # workflow.add_edge(previous_node, "scrutinize_and_update")
    

    
    # After scrutiny, we check if we should loop.
    workflow.add_conditional_edges(
        "scrutinize_and_update",
        should_continue,
        {
            "continue": "set_agenda", # Loop back
            "end": "generate_summary"  # Finish
        }
    )
    
    # The final node generates the summary and ends.
    workflow.add_edge("generate_summary", END)
    
    # Compile the graph
    app = workflow.compile()
    print("Workflow compiled successfully.")

    # save a visual representation of the graph
    output_file = Path(__file__).resolve().parent.parent / "langgraph_workflow.png"
    try:
        with open(output_file, "wb") as f:
            graph_data = app.get_graph().draw_mermaid_png()
            f.write(graph_data)
        
        print(f"✅ Graph successfully saved to {os.path.abspath(output_file)}")

    except Exception as e:
        print(f"❌ An error occurred during image generation/saving: {e}")

    return app

# # Export a single, compiled graph instance
# app = create_workflow_graph()