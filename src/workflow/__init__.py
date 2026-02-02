"""
Workflow package for LangGraph workflow definitions.

- phase1: Paper processing pipeline (ingest → summarize → critic → mechanism)
- phase2: Open problem formulation workflow
"""

from .phase1 import build_phase1_workflow
from .phase2 import create_phase2_workflow, run_phase2_workflow, run_phase2_from_phase1_state

__all__ = [
    "build_phase1_workflow",
    "create_phase2_workflow",
    "run_phase2_workflow",
    "run_phase2_from_phase1_state",
]
