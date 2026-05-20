"""Final Judge node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import JUDGE_SYSTEM, FINAL_JUDGE_PROMPT
from schema.phase2 import Phase2State, JudgeResult, QualityAssessment
from ._common import invoke_with_structured_output, save_json, save_text

_PROPOSAL_DIR = "step4_open_problems"


def _scores(result: JudgeResult) -> tuple[float, float]:
    ps = round((result.ps_coherence + result.ps_motivation + result.ps_derivation + result.ps_depth) / 4, 2)
    pi = round((result.pi_novelty + result.pi_advancement + result.pi_publication) / 3, 2)
    return ps, pi


def _save_results(state: Phase2State, result: JudgeResult, ps_score: float, pi_score: float) -> None:
    proposal_num = state.get("proposal_num", 1)
    rel_dir = f"{_PROPOSAL_DIR}/proposal_{proposal_num}"

    assessment_md = f"""# Quality Assessment

## Problem Statement
| Criterion | Score |
|-----------|-------|
| Mathematical coherence | {result.ps_coherence}/5 |
| Motivation from paper | {result.ps_motivation}/5 |
| Clarity of formulation | {result.ps_derivation}/5 |
| Conceptual depth | {result.ps_depth}/5 |

## Potential Impact
| Criterion | Score |
|-----------|-------|
| Novelty | {result.pi_novelty}/5 |
| Field advancement | {result.pi_advancement}/5 |
| Publication potential | {result.pi_publication}/5 |

## Justification
{result.justification}

## Strengths
{chr(10).join(f'- {s}' for s in result.strengths) if result.strengths else '- None'}

## Weaknesses
{chr(10).join(f'- {w}' for w in result.weaknesses) if result.weaknesses else '- None'}
"""

    summary_md = f"""# Proposal {proposal_num} Summary

## Process Overview
- **Research Direction:** {state.get('current_direction', 'N/A')}

## Quality Assessment
| Section | Score |
|---------|-------|
| Problem Statement | {ps_score}/5 |
| Potential Impact | {pi_score}/5 |

## Justification
{result.justification}

## Output Files
- `final_report.md` - Final polished report
- `quality_assessment.md` - Quality assessment details
"""

    save_text(state, rel_dir, "quality_assessment.md", assessment_md)
    save_json(state, rel_dir, "quality_assessment.json", {
        "problem_statement": {"ps_coherence": result.ps_coherence, "ps_motivation": result.ps_motivation,
                              "ps_derivation": result.ps_derivation, "ps_depth": result.ps_depth},
        "potential_impact": {"pi_novelty": result.pi_novelty, "pi_advancement": result.pi_advancement,
                             "pi_publication": result.pi_publication},
        "justification": result.justification, "strengths": result.strengths, "weaknesses": result.weaknesses,
    })
    save_text(state, rel_dir, "summary.md", summary_md)
    save_json(state, rel_dir, "summary.json", {
        "arxiv_id": state.get("arxiv_id"), "proposal_num": proposal_num,
        "direction": state.get("current_direction"),
        "section_scores": {"problem_statement": ps_score, "potential_impact": pi_score},
        "criterion_scores": {
            "ps_coherence": result.ps_coherence, "ps_motivation": result.ps_motivation,
            "ps_derivation": result.ps_derivation, "ps_depth": result.ps_depth,
            "pi_novelty": result.pi_novelty, "pi_advancement": result.pi_advancement,
            "pi_publication": result.pi_publication,
        },
    })


def final_judge_node(state: Phase2State) -> Dict[str, Any]:
    print("--- Final Judge: Evaluating report ---")

    prompt = ChatPromptTemplate.from_messages([("system", JUDGE_SYSTEM), ("human", FINAL_JUDGE_PROMPT)])
    result = invoke_with_structured_output(
        prompt=prompt, output_class=JudgeResult,
        inputs={"report": state["final_report"], "paper_summary": state["summary"], "mechanisms": state["mechanism"]},
        temperature=0.5,
    )

    ps_score, pi_score = _scores(result)
    print(f"Judge scores — PS: {result.ps_coherence}/{result.ps_motivation}/{result.ps_derivation}/{result.ps_depth} "
          f"| PI: {result.pi_novelty}/{result.pi_advancement}/{result.pi_publication}")
    print(f"Section scores — Problem Statement: {ps_score}/5 | Potential Impact: {pi_score}/5")

    assessment = QualityAssessment(
        ps_coherence=result.ps_coherence, ps_motivation=result.ps_motivation,
        ps_derivation=result.ps_derivation, ps_depth=result.ps_depth,
        pi_novelty=result.pi_novelty, pi_advancement=result.pi_advancement,
        pi_publication=result.pi_publication, justification=result.justification,
    )
    _save_results(state, result, ps_score, pi_score)

    return {"quality_assessment": assessment, "ps_score": ps_score, "pi_score": pi_score}
