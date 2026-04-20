"""
Phase 2 State Definition and Pydantic models.
"""

import operator
from typing import Annotated, List, NotRequired, TypedDict

from pydantic import BaseModel, Field


class QualityAssessment(TypedDict):
    ps_coherence: int
    ps_motivation: int
    ps_derivation: int
    ps_depth: int
    pi_novelty: int
    pi_advancement: int
    pi_publication: int
    justification: str


class Phase2State(TypedDict):
    # INPUTS
    arxiv_id: NotRequired[str]
    summary: str
    mechanism: str

    # AGENDA OUTPUT
    agenda: NotRequired[List[str]]
    subfields: NotRequired[List[str]]

    # R1: literature surveys (parallel fan-in via operator.add)
    expert_surveys_r1: Annotated[List[dict], operator.add]

    # R2: full proposals (parallel fan-in)
    expert_proposals_r2: Annotated[List[dict], operator.add]

    # R2 critics (parallel fan-in)
    expert_r2_critiques: Annotated[List[dict], operator.add]

    # R2 revision loop control
    expert_r2_iteration: NotRequired[int]
    expert_r2_max_iterations: NotRequired[int]
    expert_r2_approved: NotRequired[bool]

    # Acceptance + ranking
    accepted_proposals: NotRequired[List[dict]]

    # Finalization (set per proposal run)
    proposal_num: NotRequired[int]
    current_proposal: NotRequired[str]
    current_direction: NotRequired[str]  # used by mechanism_updater for traceability label
    final_report: NotRequired[str]
    updated_mechanism: NotRequired[str]
    quality_assessment: NotRequired[QualityAssessment]
    ps_score: NotRequired[float]
    pi_score: NotRequired[float]


# ---- Pydantic models ----

class AgendaResult(BaseModel):
    research_directions: List[str] = Field(description="3-5 high-level research directions.")
    subfields: List[str] = Field(description="Exactly 4 mathematical subfields for the expert agents.")
    rationale: str = Field(description="Why these directions are promising.")


class ExpertSurveyResult(BaseModel):
    """R1: deep literature survey. No problem proposals."""
    paper_connections: str = Field(description="How this paper specifically intersects with the subfield — named results and techniques from the paper that are relevant.")
    state_of_the_art: str = Field(description="Current state of the subfield: where the frontier sits, major results, what remains open.")
    landmark_results: List[str] = Field(description="Named theorems, conjectures, and landmark results from the literature directly relevant here. Each entry names the result, authors/paper, and why it matters.")
    settled_claims: List[str] = Field(description="Conjectures, questions, or results that are already resolved — either by this paper, mentioned in the paper as known, or established in the broader literature. Each entry names the claim and its status: 'FALSE: [name] — disproved by [paper/author]', 'TRUE: [name] — proved by [paper/author]', or 'KNOWN: [name] — [why it is settled]'. Any claim on this list is FORBIDDEN as a research proposal. If nothing is settled in this subfield, return an empty list.")
    open_territory: str = Field(description="Where the frontier currently sits: what has been tried, what failed, known obstructions, what the community believes is open.")
    available_techniques: List[str] = Field(description="Key techniques from this subfield likely relevant. Each names the technique, where it was developed, and why it may apply.")
    cross_field_bridges: str = Field(description="Specific connections between this subfield and other areas that this paper illuminates.")


class SingleProposal(BaseModel):
    """One research proposal from an expert (no approach sketch)."""
    title: str = Field(description="Concise title.")
    problem_statement: str = Field(description="Precise, rigorous mathematical claim with exact conditions and goal.")
    motivation: str = Field(description="Why this problem matters, grounded in the R1 literature survey.")
    connections: str = Field(description="How this connects to the paper's specific results and the broader mathematical landscape.")
    potential_impact: str = Field(description="What solving this would unlock.")


class ExpertProposalResult(BaseModel):
    """R2 output: two expert-authored research proposals."""
    proposals: List[SingleProposal] = Field(min_length=2, max_length=2, description="Exactly 2 research proposals.")


class ProposalVerdict(BaseModel):
    """Verdict on one proposal from the R2 critic."""
    proposal_index: int = Field(description="0-based index of the proposal within the expert's pair.")
    approved: bool = Field(description="True if this proposal meets the quality bar.")
    blocking_issues: List[str] = Field(description="Issues preventing approval. Empty if approved.")
    suggestions: List[str] = Field(description="Specific improvement suggestions.")


class ExpertR2CritiqueResult(BaseModel):
    """Critique of one expert's two R2 proposals."""
    verdicts: List[ProposalVerdict] = Field(min_length=2, max_length=2, description="One verdict per proposal (exactly 2 entries).")
    overall_approved: bool = Field(description="True only if ALL proposals are approved.")
    summary: str = Field(description="1-2 sentence summary of the review.")


class ReportResult(BaseModel):
    problem_statement: str = Field(description="Formal, rigorous statement of the problem.")
    motivation: str = Field(description="Why this problem is interesting and worth pursuing.")
    connections: str = Field(description="How this connects to the paper's results and existing work.")
    potential_impact: str = Field(description="What success would mean and enable — novelty, field advancement, publication potential.")


class JudgeResult(BaseModel):
    ps_coherence: int = Field(ge=1, le=5, description="Mathematical coherence / logical consistency (1-5)")
    ps_motivation: int = Field(ge=1, le=5, description="Derived from / motivated by original paper (1-5)")
    ps_derivation: int = Field(ge=1, le=5, description="Clearly derived / well-scoped from original paper (1-5)")
    ps_depth: int = Field(ge=1, le=5, description="Structural / conceptual depth vs surface-level (1-5)")
    pi_novelty: int = Field(ge=1, le=5, description="Genuinely novel vs known / established results (1-5)")
    pi_advancement: int = Field(ge=1, le=5, description="Would advance field understanding if solved (1-5)")
    pi_publication: int = Field(ge=1, le=5, description="Publication potential in a strong venue (1-5)")
    strengths: List[str] = Field(description="Key strengths of the proposal.")
    weaknesses: List[str] = Field(description="Key weaknesses or areas for improvement.")
    justification: str = Field(description="Detailed explanation of the scores.")
