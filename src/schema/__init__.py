"""
Schema package for state definitions and Pydantic models.

- phase1: GraphState for paper processing pipeline
- phase2: Phase2State and Pydantic models for open problem formulation
"""

from .phase1 import GraphState
from .phase2 import (
    Phase2State,
    QualityAssessment,
    # Pydantic models
    AgendaResult,
    ExpertSurveyResult,
    ExpertProposalResult,
    ExpertR2CritiqueResult,
    ReportResult,
    JudgeResult,
)

__all__ = [
    # Phase 1
    "GraphState",
    # Phase 2 State
    "Phase2State",
    "QualityAssessment",
    # Pydantic models
    "AgendaResult",
    "ExpertSurveyResult",
    "ExpertProposalResult",
    "ExpertR2CritiqueResult",
    "ReportResult",
    "JudgeResult",
]
