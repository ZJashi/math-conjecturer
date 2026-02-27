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

    Evaluates the report on 14 criteria across 4 sections (1-5 scale each).
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
        ps_coherence=result.ps_coherence,
        ps_motivation=result.ps_motivation,
        ps_derivation=result.ps_derivation,
        ps_depth=result.ps_depth,
        pa_coherence=result.pa_coherence,
        pa_alignment=result.pa_alignment,
        pa_feasibility=result.pa_feasibility,
        ec_identification=result.ec_identification,
        ec_technical_depth=result.ec_technical_depth,
        ec_complexity=result.ec_complexity,
        ec_strategies=result.ec_strategies,
        pi_novelty=result.pi_novelty,
        pi_advancement=result.pi_advancement,
        pi_publication=result.pi_publication,
        justification=result.justification,
    )

    print(
        f"Judge scores — "
        f"PS: {result.ps_coherence}/{result.ps_motivation}/{result.ps_derivation}/{result.ps_depth} | "
        f"PA: {result.pa_coherence}/{result.pa_alignment}/{result.pa_feasibility} | "
        f"EC: {result.ec_identification}/{result.ec_technical_depth}/{result.ec_complexity}/{result.ec_strategies} | "
        f"PI: {result.pi_novelty}/{result.pi_advancement}/{result.pi_publication}"
    )

    # Save assessment to file if arxiv_id is available
    arxiv_id = state.get("arxiv_id")
    proposal_num = state.get("proposal_num", 1)
    if arxiv_id:
        judge_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / f"proposal_{proposal_num}"
        judge_dir.mkdir(parents=True, exist_ok=True)

        assessment_md = f"""# Quality Assessment

## Scores by Section

### Problem Statement
| Criterion | Score |
|-----------|-------|
| Mathematical coherence | {result.ps_coherence}/5 |
| Motivation from paper | {result.ps_motivation}/5 |
| Clarity of formulation | {result.ps_derivation}/5 |
| Conceptual depth | {result.ps_depth}/5 |

### Proposed Approach
| Criterion | Score |
|-----------|-------|
| Internal coherence | {result.pa_coherence}/5 |
| Alignment with problem | {result.pa_alignment}/5 |
| Technical feasibility | {result.pa_feasibility}/5 |

### Expected Challenges
| Criterion | Score |
|-----------|-------|
| Obstacle identification | {result.ec_identification}/5 |
| Technical depth of analysis | {result.ec_technical_depth}/5 |
| Complexity calibration | {result.ec_complexity}/5 |
| Strategy plausibility | {result.ec_strategies}/5 |

### Potential Impact
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
        assessment_path = judge_dir / "quality_assessment.md"
        assessment_path.write_text(assessment_md, encoding="utf-8")
        print(f"  > Saved assessment to {assessment_path}")

        assessment_json = {
            "problem_statement": {
                "ps_coherence": result.ps_coherence,
                "ps_motivation": result.ps_motivation,
                "ps_derivation": result.ps_derivation,
                "ps_depth": result.ps_depth,
            },
            "proposed_approach": {
                "pa_coherence": result.pa_coherence,
                "pa_alignment": result.pa_alignment,
                "pa_feasibility": result.pa_feasibility,
            },
            "expected_challenges": {
                "ec_identification": result.ec_identification,
                "ec_technical_depth": result.ec_technical_depth,
                "ec_complexity": result.ec_complexity,
                "ec_strategies": result.ec_strategies,
            },
            "potential_impact": {
                "pi_novelty": result.pi_novelty,
                "pi_advancement": result.pi_advancement,
                "pi_publication": result.pi_publication,
            },
            "justification": result.justification,
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
        }
        json_path = judge_dir / "quality_assessment.json"
        json_path.write_text(json.dumps(assessment_json, indent=2), encoding="utf-8")

    return {
        "quality_assessment": assessment,
    }
