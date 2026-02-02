"""
Prompts package for the Math Conjecturer pipeline.

- phase1: Paper ingestion, summarization, critique, mechanism extraction
- phase2: Open problem formulation workflow
"""

from . import phase1
from . import phase2

__all__ = ["phase1", "phase2"]
