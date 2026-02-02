"""
Nodes package for the Math Conjecturer pipeline.

- phase1: Ingestion, summarization, critique, revision, mechanism extraction
- phase2: Open problem formulation workflow nodes
"""

from . import phase1
from . import phase2

__all__ = ["phase1", "phase2"]
