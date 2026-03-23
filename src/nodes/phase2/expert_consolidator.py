"""Expert Consolidator node for Phase 2 — synthesizes cross-field discussion."""

import json
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from prompts.phase2 import EXPERT_CONSOLIDATOR_SYSTEM, EXPERT_CONSOLIDATOR_PROMPT
from schema.phase2 import Phase2State
from ._common import PAPERS_DIR, invoke_with_structured_output


class ConsolidationResult(BaseModel):
    """Output from the Expert Consolidator."""
    top_problems: List[str] = Field(
        description="The 5-8 strongest open problems distilled from the full cross-field discussion."
    )
    key_insights: List[str] = Field(
        description="Major mathematical observations that emerged from the cross-field discussion."
    )
    technical_landscape: str = Field(
        description="Overview of tools, techniques, and connections available across all subfields."
    )
    cross_field_opportunities: List[str] = Field(
        description="Specific bridges between subfields and what they could unlock."
    )
    expert_tensions: str = Field(
        description="Where experts disagreed and what those tensions reveal."
    )
    synthesis_narrative: str = Field(
        description="Paragraph-length narrative of the overarching themes and most exciting directions."
    )


def _format_r1_contributions(contributions: list) -> str:
    if not contributions:
        return "No Round 1 contributions available."
    sections = []
    for c in contributions:
        lines = [
            f"### Expert: {c.get('subfield', 'Unknown')}",
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


def _format_r2_contributions(contributions: list) -> str:
    if not contributions:
        return "No Round 2 contributions available."
    sections = []
    for c in contributions:
        lines = [
            f"### Expert: {c.get('subfield', 'Unknown')}",
            "",
            "**Discussion (responses to other experts):**",
            *[f"- {d}" for d in c.get("discussion", [])],
            "",
            "**Synthesis Problems (cross-field):**",
            *[f"- {p}" for p in c.get("synthesis_problems", [])],
            "",
            "**Refined Problems:**",
            *[f"- {p}" for p in c.get("refined_problems", [])],
            "",
            f"**Key Insight:** {c.get('key_insight', '')}",
        ]
        sections.append("\n".join(lines))
    return "\n\n---\n\n".join(sections)


def expert_consolidator_node(state: Phase2State) -> Dict[str, Any]:
    """
    Consolidation node: synthesizes all expert R1 + R2 outputs into a unified
    research context for the brainstormer.
    """
    r1 = state.get("expert_contributions_r1", [])
    r2 = state.get("expert_contributions_r2", [])
    print(f"--- Expert Consolidator: Synthesizing {len(r1)} R1 + {len(r2)} R2 contributions ---")

    agenda = state.get("agenda", [])
    agenda_str = "\n".join(f"{i}. {d}" for i, d in enumerate(agenda, 1)) if agenda else "No agenda."

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXPERT_CONSOLIDATOR_SYSTEM),
        ("human", EXPERT_CONSOLIDATOR_PROMPT),
    ])

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=ConsolidationResult,
        inputs={
            "paper_summary": state["summary"],
            "agenda": agenda_str,
            "r1_contributions": _format_r1_contributions(r1),
            "r2_contributions": _format_r2_contributions(r2),
        },
        temperature=0.5,
    )

    # Build the consolidated context string for the brainstormer
    context_parts = [
        "# Cross-Field Expert Synthesis\n",
        f"## Synthesis Narrative\n{result.synthesis_narrative}\n",
        "## Top Open Problems Identified by Experts\n" +
        "\n".join(f"{i}. {p}" for i, p in enumerate(result.top_problems, 1)),
        "\n## Key Mathematical Insights\n" +
        "\n".join(f"- {ins}" for ins in result.key_insights),
        f"\n## Technical Landscape\n{result.technical_landscape}",
        "\n## Cross-Field Opportunities\n" +
        "\n".join(f"- {opp}" for opp in result.cross_field_opportunities),
        f"\n## Expert Tensions and Debates\n{result.expert_tensions}",
    ]
    consolidated_context = "\n".join(context_parts)

    print(f"  Consolidated {len(result.top_problems)} top problems from expert discussion.")

    # Save to file
    arxiv_id = state.get("arxiv_id")
    if arxiv_id:
        experts_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / "4b_experts"
        experts_dir.mkdir(parents=True, exist_ok=True)

        context_path = experts_dir / "consolidated_context.md"
        context_path.write_text(consolidated_context, encoding="utf-8")
        print(f"  > Saved consolidated context to {context_path}")

        json_path = experts_dir / "consolidation.json"
        json_path.write_text(
            json.dumps({
                "top_problems": result.top_problems,
                "key_insights": result.key_insights,
                "technical_landscape": result.technical_landscape,
                "cross_field_opportunities": result.cross_field_opportunities,
                "expert_tensions": result.expert_tensions,
                "synthesis_narrative": result.synthesis_narrative,
            }, indent=2),
            encoding="utf-8",
        )

    return {"consolidated_expert_context": consolidated_context}
