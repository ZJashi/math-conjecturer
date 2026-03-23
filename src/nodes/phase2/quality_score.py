"""Quality Score node for Phase 2."""

import json
from typing import Any, Dict

from schema.phase2 import Phase2State
from ._common import PAPERS_DIR


def quality_score_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 6: Quality Score

    Computes the two section-level average scores (1-5) from the judge's criteria.
    """
    print("--- Quality Score: Computing section averages ---")

    a = state["quality_assessment"]

    ps_score = round((a["ps_coherence"] + a["ps_motivation"] + a["ps_derivation"] + a["ps_depth"]) / 4, 2)
    pi_score = round((a["pi_novelty"] + a["pi_advancement"] + a["pi_publication"]) / 3, 2)

    print(f"Section scores — Problem Statement: {ps_score}/5 | Potential Impact: {pi_score}/5")

    arxiv_id = state.get("arxiv_id")
    proposal_num = state.get("proposal_num", 1)
    if arxiv_id:
        summary_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / f"proposal_{proposal_num}"
        summary_dir.mkdir(parents=True, exist_ok=True)

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
        summary_path = summary_dir / "summary.md"
        summary_path.write_text(summary_md, encoding="utf-8")
        print(f"  > Saved proposal summary to {summary_path}")

        json_path = summary_dir / "summary.json"
        json_path.write_text(json.dumps({
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

    return {
        "ps_score": ps_score,
        "pi_score": pi_score,
    }
