"""Expert Critic nodes for Phase 2 — subfield-specialized proposal critique."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import EXPERT_CRITIC_SYSTEM, EXPERT_CRITIC_PROMPT
from schema.phase2 import Phase2State, CritiqueResult, Critique
from ._common import PAPERS_DIR, invoke_with_structured_output, get_latest_r1_contributions


def _expert_critic_node(state: Phase2State, expert_index: int) -> Dict[str, Any]:
    """
    Subfield-specialized critic for the proposal loop.

    Uses the subfield assigned to this expert during the agenda phase to critique
    the current proposal from a domain-specific perspective.
    """
    subfields = state.get("subfields", [])
    if expert_index >= len(subfields):
        print(f"  WARNING: No subfield at index {expert_index}, skipping expert critic.")
        return {"critiques": []}

    subfield = subfields[expert_index]
    print(f"--- Expert Critic [{subfield}]: Reviewing proposal from subfield perspective ---")

    # Build expert context: pull this expert's R1/R2 contributions from the agenda phase.
    # Use get_latest_r1_contributions to always get the most recent revision (not the original).
    r1_contributions = get_latest_r1_contributions(state.get("expert_contributions_r1", []))
    r2_contributions = state.get("expert_contributions_r2", [])
    my_r1 = next((c for c in r1_contributions if c.get("expert_index") == expert_index), None)
    my_r2 = next((c for c in r2_contributions if c.get("expert_index") == expert_index), None)

    expert_context_parts = []
    if my_r1:
        expert_context_parts.append(
            f"**Round 1 Analysis ({subfield}):**\n"
            f"Relevant context: {my_r1.get('relevant_context', '')}\n"
            f"Open problems identified: {'; '.join(my_r1.get('open_problems', []))}\n"
            f"Key techniques: {'; '.join(my_r1.get('techniques', []))}\n"
            f"Cross-connections: {my_r1.get('cross_connections', '')}"
        )
    if my_r2:
        expert_context_parts.append(
            f"**Round 2 Synthesis ({subfield}):**\n"
            f"Key insight: {my_r2.get('key_insight', '')}\n"
            f"Refined problems: {'; '.join(my_r2.get('refined_problems', []))}\n"
            f"Synthesis problems: {'; '.join(my_r2.get('synthesis_problems', []))}"
        )

    expert_context = (
        "\n\n".join(expert_context_parts)
        if expert_context_parts
        else state.get("consolidated_expert_context", "No prior expert analysis available.")
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXPERT_CRITIC_SYSTEM),
        ("human", EXPERT_CRITIC_PROMPT),
    ])

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=CritiqueResult,
        inputs={
            "subfield": subfield,
            "proposal": state["current_proposal"],
            "paper_summary": state["summary"],
            "mechanisms": state["mechanism"],
            "expert_context": expert_context,
        },
        temperature=0.5,
    )

    source = f"expert_critic_{subfield.lower().replace(' ', '_')}"
    print(f"Expert Critic [{subfield}]: {len(result.issues)} issues, severity={result.severity}")

    critique = Critique(
        source=source,
        issues=result.issues,
        strengths=result.strengths,
        suggestions=result.suggestions,
    )

    # Save critique to file if arxiv_id is available
    arxiv_id = state.get("arxiv_id")
    iteration = state.get("phase2_iteration", 1)
    proposal_num = state.get("proposal_num", 1)
    if arxiv_id:
        critique_dir = (
            PAPERS_DIR / arxiv_id / "step4_open_problems"
            / f"proposal_{proposal_num}" / "critiques" / f"iteration_{iteration}"
        )
        critique_dir.mkdir(parents=True, exist_ok=True)

        critique_md = f"""# Expert Critic Critique: {subfield} (Iteration {iteration})

## Summary
{result.summary}

## Severity: {result.severity}

## Issues Found
{chr(10).join(f'- {issue}' for issue in result.issues) if result.issues else '- None'}

## Strengths Identified
{chr(10).join(f'- {s}' for s in result.strengths) if result.strengths else '- None'}

## Suggestions
{chr(10).join(f'- {s}' for s in result.suggestions) if result.suggestions else '- None'}
"""
        safe_name = subfield.lower().replace(" ", "_").replace("/", "_")
        critique_path = critique_dir / f"expert_critic_{safe_name}.md"
        critique_path.write_text(critique_md, encoding="utf-8")
        print(f"  > Saved critique to {critique_path}")

    return {"critiques": [critique]}


def expert_critic_0_node(state: Phase2State) -> Dict[str, Any]:
    return _expert_critic_node(state, 0)

def expert_critic_1_node(state: Phase2State) -> Dict[str, Any]:
    return _expert_critic_node(state, 1)

def expert_critic_2_node(state: Phase2State) -> Dict[str, Any]:
    return _expert_critic_node(state, 2)

def expert_critic_3_node(state: Phase2State) -> Dict[str, Any]:
    return _expert_critic_node(state, 3)
