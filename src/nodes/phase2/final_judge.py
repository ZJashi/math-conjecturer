"""Final Judge node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import JUDGE_SYSTEM, FINAL_JUDGE_PROMPT
from schema.phase2 import Phase2State, JudgeResult, QualityAssessment
from ._common import get_model


def final_judge_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 5: Final Judge

    Independently evaluates the report.
    """
    print("--- Final Judge: Evaluating report ---")

    model = get_model()
    prompt = ChatPromptTemplate.from_messages([
        ("system", JUDGE_SYSTEM),
        ("human", FINAL_JUDGE_PROMPT)
    ])

    chain = prompt | model.with_structured_output(JudgeResult)

    result = chain.invoke({
        "report": state["final_report"],
        "paper_summary": state["summary"],
        "mechanisms": state["mechanism"],
    })

    assessment = QualityAssessment(
        clarity_score=result.clarity_score,
        feasibility_score=result.feasibility_score,
        novelty_score=result.novelty_score,
        rigor_score=result.rigor_score,
        overall_score=result.overall_score,
        justification=result.justification,
        verdict=result.verdict,
    )

    print(f"Judge scores: clarity={result.clarity_score}, feasibility={result.feasibility_score}, "
          f"novelty={result.novelty_score}, rigor={result.rigor_score}, overall={result.overall_score}")

    return {
        "quality_assessment": assessment,
    }
