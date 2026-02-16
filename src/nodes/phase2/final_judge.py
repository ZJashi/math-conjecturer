"""Final Judge node for Phase 2."""

import json
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import JUDGE_SYSTEM, FINAL_JUDGE_PROMPT
from schema.phase2 import Phase2State, JudgeResult, QualityAssessment
from ._common import PAPERS_DIR, invoke_with_structured_output


def final_judge_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 5: Final Judge

    Independently evaluates the report.
    """
    print("--- Final Judge: Evaluating report ---")

    prompt = ChatPromptTemplate.from_messages([
        ("system", JUDGE_SYSTEM),
        ("human", FINAL_JUDGE_PROMPT)
    ])

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=JudgeResult,
        inputs={
            "report": state["final_report"],
            "paper_summary": state["summary"],
            "mechanisms": state["mechanism"],
        },
        temperature=0.5,
    )

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
          f"novelty={result.novelty_score}, rigor={result.rigor_score}")
    print(f"Verdict: {result.verdict}")

    # Save assessment to file if arxiv_id is available
    arxiv_id = state.get("arxiv_id")
    proposal_num = state.get("proposal_num", 1)
    if arxiv_id:
        judge_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / f"proposal_{proposal_num}"
        judge_dir.mkdir(parents=True, exist_ok=True)

        # Save as markdown
        assessment_md = f"""# Quality Assessment

## Scores

| Dimension | Score |
|-----------|-------|
| Clarity | {result.clarity_score}/10 |
| Feasibility | {result.feasibility_score}/10 |
| Novelty | {result.novelty_score}/10 |
| Rigor | {result.rigor_score}/10 |
| **Overall** | **{result.overall_score}/10** |

## Verdict: {result.verdict.upper()}

## Justification
{result.justification}

## Strengths
{chr(10).join(f'- {s}' for s in result.strengths) if result.strengths else '- None'}

## Weaknesses
{chr(10).join(f'- {w}' for w in result.weaknesses) if result.weaknesses else '- None'}
"""
        assessment_path = judge_dir / "quality_assessment.md"
        assessment_path.write_text(assessment_md, encoding="utf-8")
        print(f"  > Saved assessment to {assessment_path}")

        # Also save as JSON for programmatic access
        assessment_json = {
            "clarity_score": result.clarity_score,
            "feasibility_score": result.feasibility_score,
            "novelty_score": result.novelty_score,
            "rigor_score": result.rigor_score,
            "overall_score": result.overall_score,
            "verdict": result.verdict,
            "justification": result.justification,
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
        }
        json_path = judge_dir / "quality_assessment.json"
        json_path.write_text(json.dumps(assessment_json, indent=2), encoding="utf-8")

    return {
        "quality_assessment": assessment,
    }
