"""Phase 2 Prompts: Open Problem Formulation workflow."""

from .base import BASE_SYSTEM_PROMPT
from .agenda_creator import AGENDA_CREATOR_SYSTEM, AGENDA_CREATOR_PROMPT
from .brainstormer import (
    BRAINSTORMER_SYSTEM,
    BRAINSTORMER_PROMPT,
    BRAINSTORMER_REVISION_PROMPT,
)
from .critics import (
    CRITIC_SYSTEM,
    SANITY_CHECKER_PROMPT,
    EXAMPLE_TESTER_PROMPT,
    REVERSE_REASONER_PROMPT,
    OBSTRUCTION_ANALYZER_PROMPT,
)
from .feedback_consolidator import FEEDBACK_CONSOLIDATOR_PROMPT
from .done_decision import DONE_DECISION_PROMPT
from .report_generator import REPORT_GENERATOR_PROMPT
from .final_judge import JUDGE_SYSTEM, FINAL_JUDGE_PROMPT

__all__ = [
    # Base
    "BASE_SYSTEM_PROMPT",
    # Agenda Creator
    "AGENDA_CREATOR_SYSTEM",
    "AGENDA_CREATOR_PROMPT",
    # Brainstormer
    "BRAINSTORMER_SYSTEM",
    "BRAINSTORMER_PROMPT",
    "BRAINSTORMER_REVISION_PROMPT",
    # Critics
    "CRITIC_SYSTEM",
    "SANITY_CHECKER_PROMPT",
    "EXAMPLE_TESTER_PROMPT",
    "REVERSE_REASONER_PROMPT",
    "OBSTRUCTION_ANALYZER_PROMPT",
    # Feedback
    "FEEDBACK_CONSOLIDATOR_PROMPT",
    # Decision
    "DONE_DECISION_PROMPT",
    # Report
    "REPORT_GENERATOR_PROMPT",
    # Judge
    "JUDGE_SYSTEM",
    "FINAL_JUDGE_PROMPT",
]
