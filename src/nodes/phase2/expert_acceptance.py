"""Expert Acceptance node for Phase 2 — filters proposals by critic verdicts."""

from typing import Any, Dict

from schema.phase2 import Phase2State
from ._common import PAPERS_DIR, get_latest_r2_proposals, get_latest_r2_critiques, save_json

_EXPERTS_DIR = "step4_open_problems/4b_experts"


def _make_entry(expert_idx: int, subfield: str, i: int, p: dict) -> dict:
    return {
        "expert_index": expert_idx, "subfield": subfield, "proposal_index": i,
        "title": p.get("title", "Untitled"),
        "problem_statement": p.get("problem_statement", ""),
        "potential_impact": p.get("potential_impact", ""),
    }


def expert_acceptance_node(state: Phase2State) -> Dict[str, Any]:
    latest_proposals = get_latest_r2_proposals(state.get("expert_proposals_r2", []))
    latest_critiques = get_latest_r2_critiques(state.get("expert_r2_critiques", []))
    critiques_by_expert = {c["expert_index"]: c for c in latest_critiques}

    accepted, rejection_summary = [], []

    for entry in latest_proposals:
        expert_idx = entry.get("expert_index")
        subfield = entry.get("subfield", f"expert_{expert_idx}")
        proposals_list = entry.get("proposals", [])
        critique = critiques_by_expert.get(expert_idx)

        if critique is None:
            print(f"  WARNING: No critique for expert {expert_idx} ({subfield}). Accepting all.")
            accepted.extend(_make_entry(expert_idx, subfield, i, p) for i, p in enumerate(proposals_list))
            continue

        verdicts_by_idx = {v["proposal_index"]: v for v in critique.get("verdicts", [])}
        for i, p in enumerate(proposals_list):
            verdict = verdicts_by_idx.get(i)
            if verdict is None or verdict.get("approved", False):
                accepted.append(_make_entry(expert_idx, subfield, i, p))
                print(f"  ACCEPTED: [{subfield}] proposal {i} — {p.get('title', 'Untitled')[:60]}")
            else:
                blocking = verdict.get("blocking_issues", [])
                print(f"  REJECTED: [{subfield}] proposal {i} — {blocking[0][:80] if blocking else 'No reason'}")
                rejection_summary.append({"expert_index": expert_idx, "subfield": subfield,
                                          "proposal_index": i, "title": p.get("title", ""),
                                          "blocking_issues": blocking})

    total = sum(len(e.get("proposals", [])) for e in latest_proposals)
    print(f"--- Expert Acceptance: {len(accepted)}/{total} proposals accepted ---")

    # Fallback: accept everything if nothing passed
    if not accepted and latest_proposals:
        print("  FALLBACK: accepting all proposals.")
        for entry in latest_proposals:
            expert_idx = entry.get("expert_index")
            subfield = entry.get("subfield", f"expert_{expert_idx}")
            accepted.extend(_make_entry(expert_idx, subfield, i, p)
                            for i, p in enumerate(entry.get("proposals", [])))

    save_json(state, _EXPERTS_DIR, "acceptance_report.json", {
        "total_proposals": total, "accepted_count": len(accepted),
        "accepted": [{"expert_index": p["expert_index"], "subfield": p["subfield"],
                      "proposal_index": p["proposal_index"], "title": p["title"]} for p in accepted],
        "rejected": rejection_summary,
    })

    return {"accepted_proposals": accepted}
