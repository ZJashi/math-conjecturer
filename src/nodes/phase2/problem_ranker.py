"""Problem Ranker node for Phase 2 — orders accepted proposals by promise."""

import json
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from prompts.phase2 import PROBLEM_RANKER_SYSTEM, PROBLEM_RANKER_PROMPT
from schema.phase2 import Phase2State
from ._common import PAPERS_DIR, invoke_with_structured_output


class ProblemRankerResult(BaseModel):
    ranked_indices: List[int] = Field(
        description="0-based indices of accepted_proposals in ranked order, most promising first."
    )
    ranking_rationale: str = Field(description="Brief explanation of the ranking.")


def problem_ranker_node(state: Phase2State) -> Dict[str, Any]:
    """
    Ranks accepted_proposals by promise so finalization runs the strongest proposals first.
    Uses 0-based indices rather than problem text to avoid issues with proposal size/content.
    """
    accepted_proposals = state.get("accepted_proposals", [])

    if len(accepted_proposals) <= 1:
        print(f"--- Problem Ranker: {len(accepted_proposals)} proposal(s) — skipping rank ---")
        return {}

    print(f"--- Problem Ranker: Ranking {len(accepted_proposals)} accepted proposals ---")

    # Build a numbered summary for the LLM
    numbered = "\n".join(
        f"{i}. [{p.get('subfield', '?')}] {p.get('title', 'Untitled')}: "
        f"{p.get('problem_statement', '')[:150]}..."
        for i, p in enumerate(accepted_proposals, 1)
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", PROBLEM_RANKER_SYSTEM),
        ("human", PROBLEM_RANKER_PROMPT),
    ])

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=ProblemRankerResult,
        inputs={
            "paper_summary": state["summary"],
            "mechanisms": state["mechanism"],
            "vetted_problems": numbered,
        },
        temperature=0.2,
    )

    # Validate: ranked_indices must be a permutation of range(len(accepted_proposals))
    expected = set(range(len(accepted_proposals)))
    got = set(result.ranked_indices)
    if got != expected:
        print(
            f"  WARNING: Ranker returned indices {sorted(got)} "
            f"(expected permutation of {sorted(expected)}) — keeping original order"
        )
        return {}

    reordered = [accepted_proposals[i] for i in result.ranked_indices]

    print(f"  Ranked. Top proposal: {reordered[0].get('title', '?')[:80]}")
    print(f"  Rationale: {result.ranking_rationale[:150]}")

    # Save ranking
    arxiv_id = state.get("arxiv_id")
    if arxiv_id:
        experts_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / "4b_experts"
        experts_dir.mkdir(parents=True, exist_ok=True)
        ranking_path = experts_dir / "proposal_ranking.json"
        ranking_path.write_text(
            json.dumps({
                "ranked_indices": result.ranked_indices,
                "ranking_rationale": result.ranking_rationale,
                "ranked_titles": [p.get("title") for p in reordered],
            }, indent=2),
            encoding="utf-8",
        )
        print(f"  > Saved ranking to {ranking_path}")

    return {"accepted_proposals": reordered}
