"""Quality Score node for Phase 2."""

import json
from typing import Any, Dict

from schema.phase2 import Phase2State
from ._common import PAPERS_DIR


def quality_score_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 6: Quality Score

    Computes the final numerical quality score using weighted average.
    Saves a summary of the entire Phase 2 process.
    """
    print("--- Quality Score: Computing final score ---")

    assessment = state["quality_assessment"]

    # Extract individual scores
    clarity = assessment["clarity_score"]
    feasibility = assessment["feasibility_score"]
    novelty = assessment["novelty_score"]
    rigor = assessment["rigor_score"]

    # Compute weighted score (same weights as final_judge)
    # Novelty weighted highest (30%), Feasibility and Rigor (25% each), Clarity (20%)
    weighted_score = (
        clarity * 0.2 +
        feasibility * 0.25 +
        novelty * 0.3 +
        rigor * 0.25
    ) * 10  # Scale to 0-100

    # Determine category based on weighted score
    if weighted_score >= 85:
        category = "excellent"
    elif weighted_score >= 70:
        category = "good"
    elif weighted_score >= 55:
        category = "acceptable"
    elif weighted_score >= 40:
        category = "needs_work"
    else:
        category = "poor"

    print(f"Final Score: {weighted_score:.1f}/100 ({category})")

    # Save final summary to file if arxiv_id is available
    arxiv_id = state.get("arxiv_id")
    proposal_num = state.get("proposal_num", 1)
    if arxiv_id:
        summary_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / f"proposal_{proposal_num}"
        summary_dir.mkdir(parents=True, exist_ok=True)

        # Save comprehensive summary
        summary_md = f"""# Proposal {proposal_num} Summary

## Process Overview
- **Total Iterations:** {state.get('phase2_iteration', 'N/A')}
- **Exit Reason:** {state.get('done_reason', 'N/A')}
- **Research Direction:** {state.get('current_direction', 'N/A')}

## Quality Assessment

### Individual Scores
| Dimension | Score | Weight |
|-----------|-------|--------|
| Clarity | {clarity}/10 | 20% |
| Feasibility | {feasibility}/10 | 25% |
| Novelty | {novelty}/10 | 30% |
| Rigor | {rigor}/10 | 25% |

### Final Score: {weighted_score:.1f}/100

### Category: {category.upper()}

### Verdict: {assessment['verdict'].upper()}

## Justification
{assessment['justification']}

## Output Files
- `proposals/` - Proposal iterations
- `critiques/` - Feedback from all critics per iteration
- `feedback/` - Consolidated feedback per iteration
- `decisions/` - Loop continuation decisions
- `report.md` - Final polished report
- `quality_assessment.md` - Quality assessment details
"""
        summary_path = summary_dir / "summary.md"
        summary_path.write_text(summary_md, encoding="utf-8")
        print(f"  > Saved proposal summary to {summary_path}")

        # Also save as JSON
        summary_json = {
            "arxiv_id": arxiv_id,
            "proposal_num": proposal_num,
            "direction": state.get("current_direction"),
            "total_iterations": state.get("phase2_iteration"),
            "exit_reason": state.get("done_reason"),
            "scores": {
                "clarity": clarity,
                "feasibility": feasibility,
                "novelty": novelty,
                "rigor": rigor,
                "overall": assessment.get("overall_score"),
            },
            "weighted_score": weighted_score,
            "category": category,
            "verdict": assessment["verdict"],
        }
        json_path = summary_dir / "summary.json"
        json_path.write_text(json.dumps(summary_json, indent=2), encoding="utf-8")

    return {
        "quality_score": weighted_score,
        "quality_category": category,
    }
