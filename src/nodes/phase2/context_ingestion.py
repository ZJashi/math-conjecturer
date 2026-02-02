"""Context Ingestion node for Phase 2."""

from typing import Any, Dict

from schema.phase2 import Phase2State


def context_ingestion_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 1: Context Ingestion

    Initializes Phase 2 iteration tracking.
    Takes summary and mechanism from Phase 1 as inputs.
    """
    print("--- Phase 2 Context Ingestion: Initializing workflow state ---")
    print(f"  > Summary length: {len(state.get('summary', ''))} chars")
    print(f"  > Mechanism length: {len(state.get('mechanism', ''))} chars")

    return {
        "phase2_iteration": 0,
        "max_iterations": state.get("max_iterations", 5),
        "critiques": [],
    }
