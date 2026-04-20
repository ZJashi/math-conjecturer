"""Expert R1 Critic node — reviews field expert Round 1 outputs and triggers revision if needed."""

import json
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2.expert_r1_critic import (
    EXPERT_R1_CRITIC_SYSTEM,
    EXPERT_R1_CRITIC_PROMPT,
    ExpertR1CritiqueResult,
)
from schema.phase2 import Phase2State
from ._common import PAPERS_DIR, invoke_with_structured_output, get_latest_r1_contributions


def _format_r1_for_review(contributions: list) -> str:
    """Format R1 contributions for the critic to review."""
    if not contributions:
        return "No contributions available."
    sections = []
    for c in contributions:
        lines = [
            f"### Expert {c.get('expert_index', '?')} — {c.get('subfield', 'Unknown')}",
            "",
            f"**Relevant Context:** {c.get('relevant_context', '')}",
            "",
            "**Open Problems:**",
            *[f"- {p}" for p in c.get("open_problems", [])],
            "",
            "**Techniques:**",
            *[f"- {t}" for t in c.get("techniques", [])],
            "",
            f"**Cross-connections:** {c.get('cross_connections', '')}",
        ]
        sections.append("\n".join(lines))
    return "\n\n---\n\n".join(sections)


def expert_r1_critic_node(state: Phase2State) -> Dict[str, Any]:
    """
    Reviews all R1 expert outputs for quality: precision, novelty, grounding, substantiveness.
    Sets expert_r1_critiques (per-expert feedback dict) and expert_r1_approved.
    Increments expert_r1_iteration to cap the loop.
    """
    all_r1 = state.get("expert_contributions_r1", [])
    latest_r1 = get_latest_r1_contributions(all_r1)
    iteration = state.get("expert_r1_iteration", 0) + 1
    max_iterations = state.get("expert_r1_max_iterations", 2)

    print(f"--- Expert R1 Critic: Reviewing {len(latest_r1)} R1 outputs "
          f"(iteration {iteration}/{max_iterations}) ---")

    if not latest_r1:
        print("  WARNING: No R1 contributions to review.")
        return {
            "expert_r1_critiques": {},
            "expert_r1_approved": True,
            "expert_r1_iteration": iteration,
        }

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXPERT_R1_CRITIC_SYSTEM),
        ("human", EXPERT_R1_CRITIC_PROMPT),
    ])

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=ExpertR1CritiqueResult,
        inputs={
            "n_experts": len(latest_r1),
            "paper_summary": state["summary"],
            "mechanisms": state["mechanism"],
            "r1_contributions": _format_r1_for_review(latest_r1),
        },
        temperature=0.2,
    )

    # Build per-expert feedback dict (keyed by str(expert_index) for JSON compatibility)
    critiques = {}
    for verdict in result.verdicts:
        critiques[str(verdict.expert_index)] = {
            "subfield": verdict.subfield,
            "needs_revision": not verdict.approved,
            "issues": verdict.issues,
            "suggestions": verdict.suggestions,
        }
        status = "APPROVED" if verdict.approved else "NEEDS REVISION"
        print(f"  Expert {verdict.expert_index} [{verdict.subfield}]: {status} "
              f"({len(verdict.issues)} issue(s))")

    print(f"  Overall: {'APPROVED' if result.overall_approved else 'NEEDS REVISION'} — {result.summary[:100]}")

    # Force approval if we've hit the iteration cap
    force_approved = iteration >= max_iterations
    if force_approved and not result.overall_approved:
        print(f"  NOTE: Iteration cap reached ({max_iterations}), proceeding despite issues.")

    # Save critic output to file
    arxiv_id = state.get("arxiv_id")
    if arxiv_id:
        experts_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / "4b_experts"
        experts_dir.mkdir(parents=True, exist_ok=True)
        path = experts_dir / f"r1_critic_iteration_{iteration}.json"
        path.write_text(json.dumps({
            "iteration": iteration,
            "overall_approved": result.overall_approved,
            "summary": result.summary,
            "critiques": critiques,
        }, indent=2), encoding="utf-8")
        print(f"  > Saved R1 critique to {path}")

    return {
        "expert_r1_critiques": critiques,
        "expert_r1_approved": result.overall_approved or force_approved,
        "expert_r1_iteration": iteration,
    }


def expert_r1_revision_dispatch_node(state: Phase2State) -> Dict[str, Any]:
    """
    No-op barrier: signals that experts should run again with revision feedback.
    The actual feedback is already in state["expert_r1_critiques"].
    """
    critiques = state.get("expert_r1_critiques", {})
    needs_revision = [idx for idx, c in critiques.items() if c.get("needs_revision", False)]
    print(f"--- Expert R1 Revision Dispatch: {len(needs_revision)} expert(s) need revision: "
          f"{needs_revision} ---")
    return {}
