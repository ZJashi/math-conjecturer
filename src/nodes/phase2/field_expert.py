"""Field Expert nodes for Phase 2 — two-round cross-field discussion."""

import json
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import (
    FIELD_EXPERT_SYSTEM,
    FIELD_EXPERT_R1_PROMPT,
    FIELD_EXPERT_R2_PROMPT,
)
from schema.phase2 import Phase2State, ExpertContributionResult
from ._common import PAPERS_DIR, invoke_with_structured_output


def _format_agenda(state: Phase2State) -> str:
    agenda = state.get("agenda", [])
    return "\n".join(f"{i}. {d}" for i, d in enumerate(agenda, 1)) if agenda else "No agenda available."


def _field_expert_r1(state: Phase2State, expert_index: int) -> Dict[str, Any]:
    """Round 1: independent field analysis."""
    subfields = state.get("subfields", [])
    if expert_index >= len(subfields):
        print(f"  WARNING: No subfield at index {expert_index}, skipping.")
        return {"expert_contributions_r1": []}

    subfield = subfields[expert_index]
    print(f"--- Field Expert R1 [{subfield}]: Generating initial analysis ---")

    prompt = ChatPromptTemplate.from_messages([
        ("system", FIELD_EXPERT_SYSTEM),
        ("human", FIELD_EXPERT_R1_PROMPT),
    ])

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=ExpertContributionResult,
        inputs={
            "subfield": subfield,
            "paper_summary": state["summary"],
            "mechanisms": state["mechanism"],
            "agenda": _format_agenda(state),
        },
        temperature=0.8,
    )

    contribution = {
        "round": 1,
        "expert_index": expert_index,
        "subfield": result.subfield,
        "relevant_context": result.relevant_context,
        "open_problems": result.open_problems,
        "techniques": result.techniques,
        "cross_connections": result.cross_connections,
    }

    print(f"  [{subfield}] R1 complete: {len(result.open_problems)} problems identified.")

    _save_expert_output(state, expert_index, 1, contribution)
    return {"expert_contributions_r1": [contribution]}


def _field_expert_r2(state: Phase2State, expert_index: int) -> Dict[str, Any]:
    """Round 2: cross-field discussion, each expert sees all R1 outputs."""
    subfields = state.get("subfields", [])
    if expert_index >= len(subfields):
        print(f"  WARNING: No subfield at index {expert_index}, skipping.")
        return {"expert_contributions_r2": []}

    subfield = subfields[expert_index]
    r1_contributions = state.get("expert_contributions_r1", [])

    print(f"--- Field Expert R2 [{subfield}]: Cross-field discussion ---")

    # Split into my contribution vs others
    my_r1 = next(
        (c for c in r1_contributions if c.get("expert_index") == expert_index),
        None,
    )
    others_r1 = [c for c in r1_contributions if c.get("expert_index") != expert_index]

    my_r1_text = _format_r1_contribution(my_r1) if my_r1 else "No Round 1 contribution found."
    others_text = "\n\n---\n\n".join(
        f"**Expert in {c['subfield']}**\n\n" + _format_r1_contribution(c)
        for c in others_r1
    ) if others_r1 else "No other expert contributions available."

    prompt = ChatPromptTemplate.from_messages([
        ("system", FIELD_EXPERT_SYSTEM),
        ("human", FIELD_EXPERT_R2_PROMPT),
    ])

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=ExpertDiscussionResult,
        inputs={
            "subfield": subfield,
            "paper_summary": state["summary"],
            "mechanisms": state["mechanism"],
            "my_r1_contribution": my_r1_text,
            "other_r1_contributions": others_text,
        },
        temperature=0.7,
    )

    contribution = {
        "round": 2,
        "expert_index": expert_index,
        "subfield": subfield,
        "discussion": result.discussion,
        "synthesis_problems": result.synthesis_problems,
        "refined_problems": result.refined_problems,
        "key_insight": result.key_insight,
    }

    print(
        f"  [{subfield}] R2 complete: "
        f"{len(result.refined_problems)} refined problems, "
        f"{len(result.synthesis_problems)} synthesis problems."
    )

    _save_expert_output(state, expert_index, 2, contribution)
    return {"expert_contributions_r2": [contribution]}


def _format_r1_contribution(c: dict) -> str:
    lines = [
        f"Relevant Context: {c.get('relevant_context', '')}",
        "",
        "Open Problems:",
        *[f"  - {p}" for p in c.get("open_problems", [])],
        "",
        "Techniques:",
        *[f"  - {t}" for t in c.get("techniques", [])],
        "",
        f"Cross-connections: {c.get('cross_connections', '')}",
    ]
    return "\n".join(lines)


def _save_expert_output(state: Phase2State, expert_index: int, round_num: int, data: dict) -> None:
    arxiv_id = state.get("arxiv_id")
    if not arxiv_id:
        return
    experts_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / "4b_experts"
    experts_dir.mkdir(parents=True, exist_ok=True)
    path = experts_dir / f"expert_{expert_index}_r{round_num}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  > Saved to {path}")


# ---------------------------------------------------------------------------
# Round 2 Pydantic model (imported here to avoid circular imports)
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field
from typing import List


class ExpertDiscussionResult(BaseModel):
    """Output from a field expert's Round 2 discussion."""
    discussion: List[str] = Field(
        description="Specific responses to other experts' problems — challenges, endorsements, clarifications."
    )
    synthesis_problems: List[str] = Field(
        description="New problems that emerge from the interaction between multiple subfields."
    )
    refined_problems: List[str] = Field(
        description="Updated and sharpened versions of the expert's own Round 1 problems."
    )
    key_insight: str = Field(
        description="The single most important mathematical insight from this cross-field discussion."
    )


# ---------------------------------------------------------------------------
# Round 1 node functions (4 experts)
# ---------------------------------------------------------------------------

def field_expert_0_r1_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r1(state, 0)

def field_expert_1_r1_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r1(state, 1)

def field_expert_2_r1_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r1(state, 2)

def field_expert_3_r1_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r1(state, 3)


# ---------------------------------------------------------------------------
# Round 2 sync (barrier — no-op join before fan-out)
# ---------------------------------------------------------------------------

def r2_sync_node(state: Phase2State) -> Dict[str, Any]:
    """Barrier node: waits for all R1 experts to complete, then signals R2 fan-out."""
    r1 = state.get("expert_contributions_r1", [])
    print(f"--- R2 Sync: {len(r1)} Round 1 contributions collected, starting Round 2 discussion ---")
    return {}


# ---------------------------------------------------------------------------
# Round 2 node functions (4 experts)
# ---------------------------------------------------------------------------

def field_expert_0_r2_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r2(state, 0)

def field_expert_1_r2_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r2(state, 1)

def field_expert_2_r2_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r2(state, 2)

def field_expert_3_r2_node(state: Phase2State) -> Dict[str, Any]:
    return _field_expert_r2(state, 3)
