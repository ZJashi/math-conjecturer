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

    Evaluates the report on 7 criteria across 2 sections (1-5 scale each).
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
        pi_novelty=result.pi_novelty,
        pi_advancement=result.pi_advancement,
        pi_publication=result.pi_publication,
        justification=result.justification,
    )

    ps_score = round((result.ps_coherence + result.ps_motivation + result.ps_derivation + result.ps_depth) / 4, 2)
    pi_score = round((result.pi_novelty + result.pi_advancement + result.pi_publication) / 3, 2)

    print(
        f"Judge scores — "
        f"PS: {result.ps_coherence}/{result.ps_motivation}/{result.ps_derivation}/{result.ps_depth} | "
        f"PI: {result.pi_novelty}/{result.pi_advancement}/{result.pi_publication}"
    )
    print(f"Section scores — Problem Statement: {ps_score}/5 | Potential Impact: {pi_score}/5")

    arxiv_id = state.get("arxiv_id")
    proposal_num = state.get("proposal_num", 1)
    if arxiv_id:
        judge_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / f"proposal_{proposal_num}"
        judge_dir.mkdir(parents=True, exist_ok=True)

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
        assessment_path = judge_dir / "quality_assessment.md"
        assessment_path.write_text(assessment_md, encoding="utf-8")
        print(f"  > Saved assessment to {assessment_path}")

        json_path = judge_dir / "quality_assessment.json"
        json_path.write_text(json.dumps({
            "problem_statement": {
                "ps_coherence": result.ps_coherence,
                "ps_motivation": result.ps_motivation,
                "ps_derivation": result.ps_derivation,
                "ps_depth": result.ps_depth,
            },
            "potential_impact": {
                "pi_novelty": result.pi_novelty,
                "pi_advancement": result.pi_advancement,
                "pi_publication": result.pi_publication,
            },
            "justification": result.justification,
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
        }, indent=2), encoding="utf-8")

        # Save summary files (previously in quality_score_node)
        a = assessment
        summary_md = f"""# Proposal {proposal_num} Summary

## Process Overview
- **Total Iterations:** {state.get('phase2_iteration', 'N/A')}
- **Exit Reason:** {state.get('done_reason', 'N/A')}
- **Research Direction:** {state.get('current_direction', 'N/A')}

## Quality Assessment

### Section Scores (1–5 scale)
| Section | Score |
|---------|-------|
| Problem Statement | {ps_score}/5 |
| Potential Impact | {pi_score}/5 |

### Problem Statement Detail
| Criterion | Score |
|-----------|-------|
| Mathematical coherence | {a['ps_coherence']}/5 |
| Motivation from paper | {a['ps_motivation']}/5 |
| Clarity of formulation | {a['ps_derivation']}/5 |
| Conceptual depth | {a['ps_depth']}/5 |

### Potential Impact Detail
| Criterion | Score |
|-----------|-------|
| Novelty | {a['pi_novelty']}/5 |
| Field advancement | {a['pi_advancement']}/5 |
| Publication potential | {a['pi_publication']}/5 |

## Justification
{a['justification']}

## Output Files
- `proposals/` - Proposal iterations
- `critiques/` - Feedback from all critics per iteration
- `feedback/` - Consolidated feedback per iteration
- `decisions/` - Loop continuation decisions
- `final_report.md` - Final polished report
- `quality_assessment.md` - Quality assessment details
"""
        summary_path = judge_dir / "summary.md"
        summary_path.write_text(summary_md, encoding="utf-8")
        print(f"  > Saved proposal summary to {summary_path}")

        summary_json_path = judge_dir / "summary.json"
        summary_json_path.write_text(json.dumps({
            "arxiv_id": arxiv_id,
            "proposal_num": proposal_num,
            "direction": state.get("current_direction"),
            "total_iterations": state.get("phase2_iteration"),
            "exit_reason": state.get("done_reason"),
            "section_scores": {
                "problem_statement": ps_score,
                "potential_impact": pi_score,
            },
            "criterion_scores": {
                "ps_coherence": a["ps_coherence"],
                "ps_motivation": a["ps_motivation"],
                "ps_derivation": a["ps_derivation"],
                "ps_depth": a["ps_depth"],
                "pi_novelty": a["pi_novelty"],
                "pi_advancement": a["pi_advancement"],
                "pi_publication": a["pi_publication"],
            },
        }, indent=2), encoding="utf-8")

    return {"quality_assessment": assessment, "ps_score": ps_score, "pi_score": pi_score}
