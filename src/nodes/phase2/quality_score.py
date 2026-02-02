"""Quality Score node for Phase 2."""

from typing import Any, Dict

from schema.phase2 import Phase2State
from ._common import PAPERS_DIR


def quality_score_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 6: Quality Score

    Computes the final numerical quality score.
    """
    print("--- Quality Score: Computing final score ---")

    assessment = state["quality_assessment"]

    # Compute weighted score (equal weights)
    clarity = assessment["clarity_score"]
    feasibility = assessment["feasibility_score"]
    novelty = assessment["novelty_score"]
    rigor = assessment["rigor_score"]

    # Scale from 1-10 to 0-100
    numerical_score = (clarity + feasibility + novelty + rigor) / 4 * 10

    # Determine category
    if numerical_score >= 85:
        category = "excellent"
    elif numerical_score >= 70:
        category = "good"
    elif numerical_score >= 55:
        category = "acceptable"
    elif numerical_score >= 40:
        category = "needs_work"
    else:
        category = "poor"

    print(f"Final Score: {numerical_score:.1f}/100 ({category})")

    # Save quality assessment to file if arxiv_id is available
    arxiv_id = state.get("arxiv_id")
    if arxiv_id:
        score_dir = PAPERS_DIR / arxiv_id / "step4_phase2"
        score_dir.mkdir(parents=True, exist_ok=True)
        score_path = score_dir / "quality_assessment.md"

        score_content = f"""# Quality Assessment

## Scores
- **Clarity:** {clarity}/10
- **Feasibility:** {feasibility}/10
- **Novelty:** {novelty}/10
- **Rigor:** {rigor}/10
- **Overall:** {assessment['overall_score']}/10

## Final Score: {numerical_score:.1f}/100 ({category.upper()})

## Verdict: {assessment['verdict'].upper()}

## Justification
{assessment['justification']}
"""
        score_path.write_text(score_content, encoding="utf-8")
        print(f"  > Saved quality assessment to {score_path}")

    return {
        "quality_score": numerical_score,
        "quality_category": category,
    }
