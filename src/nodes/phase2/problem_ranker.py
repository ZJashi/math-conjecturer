"""Problem Ranker node for Phase 2 — orders accepted proposals by promise."""

from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from prompts.phase2 import PROBLEM_RANKER_SYSTEM, PROBLEM_RANKER_PROMPT
from schema.phase2 import Phase2State
from ._common import invoke_with_structured_output, save_json


class ProblemRankerResult(BaseModel):
    ranked_indices: List[int] = Field(description="0-based indices in ranked order, most promising first.")
    ranking_rationale: str = Field(description="Brief explanation of the ranking.")


def problem_ranker_node(state: Phase2State) -> Dict[str, Any]:
    accepted_proposals = state.get("accepted_proposals", [])
    if len(accepted_proposals) <= 1:
        print(f"--- Problem Ranker: {len(accepted_proposals)} proposal(s) — skipping ---")
        return {}

    print(f"--- Problem Ranker: Ranking {len(accepted_proposals)} proposals ---")

    prompt = ChatPromptTemplate.from_messages([("system", PROBLEM_RANKER_SYSTEM), ("human", PROBLEM_RANKER_PROMPT)])
    result = invoke_with_structured_output(
        prompt=prompt, output_class=ProblemRankerResult,
        inputs={
            "paper_summary": state["summary"],
            "mechanisms": state["mechanism"],
            "vetted_problems": "\n".join(
                f"{i}. [{p.get('subfield', '?')}] {p.get('title', 'Untitled')}: "
                f"{p.get('problem_statement', '')[:150]}..."
                for i, p in enumerate(accepted_proposals, 1)
            ),
        },
        temperature=0.2,
    )

    expected = set(range(len(accepted_proposals)))
    if set(result.ranked_indices) != expected:
        print(f"  WARNING: Invalid ranking indices — keeping original order")
        return {}

    reordered = [accepted_proposals[i] for i in result.ranked_indices]
    print(f"  Top: {reordered[0].get('title', '?')[:80]}")
    print(f"  Rationale: {result.ranking_rationale[:150]}")

    save_json(state, "step4_open_problems/4b_experts", "proposal_ranking.json", {
        "ranked_indices": result.ranked_indices,
        "ranking_rationale": result.ranking_rationale,
        "ranked_titles": [p.get("title") for p in reordered],
    })
    return {"accepted_proposals": reordered}
