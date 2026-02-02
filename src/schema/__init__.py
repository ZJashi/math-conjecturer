"""
Schema package for state definitions and Pydantic models.

- phase1: GraphState for paper processing pipeline
- phase2: Phase2State and Pydantic models for open problem formulation
"""

from .phase1 import GraphState
from .phase2 import (
    Phase2State,
    Critique,
    ConsolidatedFeedback,
    QualityAssessment,
    # Pydantic models
    AgendaResult,
    ProposalResult,
    CritiqueResult,
    ConsolidatedFeedbackResult,
    DoneDecisionResult,
    ReportResult,
    JudgeResult,
    QualityScoreResult,
)

__all__ = [
    # Phase 1
    "GraphState",
    # Phase 2 State
    "Phase2State",
    "Critique",
    "ConsolidatedFeedback",
    "QualityAssessment",
    # Pydantic models
    "AgendaResult",
    "ProposalResult",
    "CritiqueResult",
    "ConsolidatedFeedbackResult",
    "DoneDecisionResult",
    "ReportResult",
    "JudgeResult",
    "QualityScoreResult",
]
