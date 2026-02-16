"""
Phase 2 State Definition and Pydantic models.

State for the Open Problem Formulation workflow, plus Pydantic models
for structured LLM outputs.
"""

import operator
from typing import Annotated, List, Literal, NotRequired, TypedDict

from pydantic import BaseModel, Field


# =============================================================================
# STATE TYPEDDICTS
# =============================================================================

class Critique(TypedDict):
    """Individual critique from a critic agent."""
    source: str  # Which critic agent produced this
    issues: List[str]  # List of identified issues
    strengths: List[str]  # List of identified strengths
    suggestions: List[str]  # Suggested improvements


class ConsolidatedFeedback(TypedDict):
    """Merged feedback from all critic agents."""
    critical_issues: List[str]  # Must-fix issues
    minor_issues: List[str]  # Nice-to-fix issues
    strengths: List[str]  # Things that work well
    required_fixes: List[str]  # Specific changes needed
    overall_assessment: str  # Summary assessment


class QualityAssessment(TypedDict):
    """Final quality assessment from the judge."""
    clarity_score: int  # 1-10
    feasibility_score: int  # 1-10
    novelty_score: int  # 1-10
    rigor_score: int  # 1-10
    overall_score: int  # 1-10
    justification: str  # Explanation of scores
    verdict: Literal["excellent", "good", "acceptable", "needs_work", "poor"]


class Phase2State(TypedDict):
    """
    Complete state for the Phase 2 Open Problem Formulation workflow.

    INPUTS (from Phase 1 GraphState):
    - summary: Paper summary from summarizer_node
    - mechanism: Mechanism XML from mechanism_node
    - arxiv_id: Paper identifier (optional, for file saving)
    """
    # === INPUTS (from Phase 1 GraphState) ===
    arxiv_id: NotRequired[str]  # Paper identifier for file saving
    summary: str  # Markdown summary from Phase 1 summarizer_node
    mechanism: str  # Mechanism XML from Phase 1 mechanism_node

    # === AGENDA CREATOR OUTPUT ===
    agenda: NotRequired[List[str]]  # High-level strategies/directions

    # === MULTI-PROPOSAL STATE ===
    current_direction: NotRequired[str]  # Specific research direction for this proposal
    proposal_num: NotRequired[int]  # Which proposal (1, 2, 3) is being generated

    # === AGENT K LOOP STATE ===
    current_proposal: NotRequired[str]
    phase2_iteration: NotRequired[int]
    max_iterations: NotRequired[int]

    # Critiques from parallel agents (using Annotated with operator.add for merging)
    critiques: Annotated[List[Critique], operator.add]

    # Consolidated feedback
    consolidated_feedback: NotRequired[ConsolidatedFeedback]

    # Done decision
    is_done: NotRequired[bool]
    done_reason: NotRequired[str]

    # === REPORT GENERATOR OUTPUT ===
    final_report: NotRequired[str]

    # === MECHANISM UPDATER OUTPUT ===
    updated_mechanism: NotRequired[str]  # Updated mechanism XML with traceability

    # === FINAL JUDGE OUTPUT ===
    quality_assessment: NotRequired[QualityAssessment]

    # === QUALITY SCORE OUTPUT ===
    quality_score: NotRequired[float]  # Final numerical score (0-100)
    quality_category: NotRequired[Literal["excellent", "good", "acceptable", "needs_work", "poor"]]


# =============================================================================
# PYDANTIC MODELS FOR STRUCTURED LLM OUTPUTS
# =============================================================================

class AgendaResult(BaseModel):
    """Output from the Agenda Creator agent."""
    research_directions: List[str] = Field(
        description="List of 3-5 high-level research directions or problem strategies to explore."
    )
    rationale: str = Field(
        description="Brief explanation of why these directions are promising given the context."
    )


class ProposalResult(BaseModel):
    """Output from the Brainstormer agent."""
    title: str = Field(
        description="Concise title for the proposed research problem."
    )
    problem_statement: str = Field(
        description="Clear, precise statement of the open problem or conjecture."
    )
    motivation: str = Field(
        description="Why this problem is interesting and worth pursuing."
    )
    approach_sketch: str = Field(
        description="Initial ideas for how one might approach this problem."
    )
    connections: str = Field(
        description="How this connects to existing work and the provided context."
    )
    potential_impact: str = Field(
        description="What solving this problem would enable or reveal."
    )


class CritiqueResult(BaseModel):
    """Output from a critic agent (Sanity, Example, Reverse, Obstruction)."""
    issues: List[str] = Field(
        description="List of identified problems, weaknesses, or concerns."
    )
    strengths: List[str] = Field(
        description="List of positive aspects and things that work well."
    )
    suggestions: List[str] = Field(
        description="Specific, actionable suggestions for improvement."
    )
    severity: Literal["critical", "moderate", "minor"] = Field(
        description="Overall severity of the issues found."
    )
    summary: str = Field(
        description="Brief summary of the critique."
    )


class ConsolidatedFeedbackResult(BaseModel):
    """Output from the Feedback Consolidator."""
    critical_issues: List[str] = Field(
        description="Issues that MUST be fixed before the proposal is acceptable."
    )
    minor_issues: List[str] = Field(
        description="Issues that would be nice to fix but aren't blockers."
    )
    strengths: List[str] = Field(
        description="Consolidated list of proposal strengths."
    )
    required_fixes: List[str] = Field(
        description="Specific, prioritized list of changes needed."
    )
    overall_assessment: str = Field(
        description="Summary assessment of proposal quality and readiness."
    )


class DoneDecisionResult(BaseModel):
    """Output from the Done Decision node."""
    is_done: bool = Field(
        description="Whether the proposal quality is sufficient to proceed."
    )
    clarity_met: bool = Field(
        description="Whether the proposal is clear and well-defined."
    )
    feasibility_met: bool = Field(
        description="Whether the proposal seems feasible to pursue."
    )
    novelty_met: bool = Field(
        description="Whether the proposal offers genuine novelty."
    )
    reasoning: str = Field(
        description="Explanation of the decision."
    )
    recommendation: str = Field(
        description="What should happen next (refine further or proceed)."
    )


class ReportResult(BaseModel):
    """Output from the Report Generator."""
    problem_statement: str = Field(
        description="Formal, rigorous statement of the problem."
    )
    proposed_approach: str = Field(
        description="Detailed approach and methodology."
    )
    expected_challenges: str = Field(
        description="Anticipated difficulties and how to address them."
    )
    potential_impact: str = Field(
        description="What success would mean and enable."
    )


class JudgeResult(BaseModel):
    """Output from the Final Judge."""
    clarity_score: int = Field(
        ge=1, le=10,
        description="How clear and well-defined is the proposal? (1-10)"
    )
    feasibility_score: int = Field(
        ge=1, le=10,
        description="How feasible is this research direction? (1-10)"
    )
    novelty_score: int = Field(
        ge=1, le=10,
        description="How novel and original is the proposal? (1-10)"
    )
    rigor_score: int = Field(
        ge=1, le=10,
        description="How rigorous and well-founded is the proposal? (1-10)"
    )
    overall_score: int = Field(
        ge=1, le=10,
        description="Overall quality score (1-10)"
    )
    strengths: List[str] = Field(
        description="Key strengths of the proposal."
    )
    weaknesses: List[str] = Field(
        description="Key weaknesses or areas for improvement."
    )
    justification: str = Field(
        description="Detailed explanation of the scores."
    )
    verdict: Literal["excellent", "good", "acceptable", "needs_work", "poor"] = Field(
        description="Final verdict on proposal quality."
    )


class QualityScoreResult(BaseModel):
    """Final quality score output."""
    numerical_score: float = Field(
        ge=0, le=100,
        description="Final quality score from 0-100."
    )
    category: Literal["excellent", "good", "acceptable", "needs_work", "poor"] = Field(
        description="Quality category."
    )
    breakdown: str = Field(
        description="Brief breakdown of how the score was computed."
    )
