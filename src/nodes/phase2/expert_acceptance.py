"""Expert Acceptance node for Phase 2 — filters individual proposals from R2 expert pairs by critic verdicts."""

import json
from typing import Any, Dict

from schema.phase2 import Phase2State
from ._common import PAPERS_DIR, get_latest_r2_proposals, get_latest_r2_critiques


def expert_acceptance_node(state: Phase2State) -> Dict[str, Any]:
    """
    Builds a flat list of accepted individual proposals from all expert pairs.

    For each expert's pair of proposals, finds the corresponding critique verdicts.
    If a verdict approves proposal i, that individual proposal is added to accepted.
    If no critique is found, all proposals from that expert are accepted defensively.
    Fallback: if nothing was accepted, accept all individual proposals.
    """
    latest_proposals = get_latest_r2_proposals(state.get("expert_proposals_r2", []))
    latest_critiques = get_latest_r2_critiques(state.get("expert_r2_critiques", []))

    critiques_by_expert: Dict[int, dict] = {
        c["expert_index"]: c for c in latest_critiques
    }

    accepted = []
    rejection_summary = []

    for proposal_entry in latest_proposals:
        expert_idx = proposal_entry.get("expert_index")
        subfield = proposal_entry.get("subfield", f"expert_{expert_idx}")
        proposals_list = proposal_entry.get("proposals", [])
        critique = critiques_by_expert.get(expert_idx)

        if critique is None:
            # No critique — accept all proposals from this expert defensively
            print(f"  WARNING: No critique found for expert {expert_idx} ({subfield}). Accepting all proposals.")
            for i, p in enumerate(proposals_list):
                accepted.append({
                    "expert_index": expert_idx,
                    "subfield": subfield,
                    "proposal_index": i,
                    "title": p.get("title", "Untitled"),
                    "problem_statement": p.get("problem_statement", ""),
                    "motivation": p.get("motivation", ""),
                    "connections": p.get("connections", ""),
                    "potential_impact": p.get("potential_impact", ""),
                })
        else:
            verdicts = critique.get("verdicts", [])
            verdicts_by_idx: Dict[int, dict] = {v["proposal_index"]: v for v in verdicts}

            for i, p in enumerate(proposals_list):
                verdict = verdicts_by_idx.get(i)
                if verdict is None or verdict.get("approved", False):
                    accepted.append({
                        "expert_index": expert_idx,
                        "subfield": subfield,
                        "proposal_index": i,
                        "title": p.get("title", "Untitled"),
                        "problem_statement": p.get("problem_statement", ""),
                        "motivation": p.get("motivation", ""),
                        "connections": p.get("connections", ""),
                        "potential_impact": p.get("potential_impact", ""),
                    })
                    print(f"  ACCEPTED: [{subfield}] proposal {i} — {p.get('title', 'Untitled')[:60]}")
                else:
                    blocking = verdict.get("blocking_issues", [])
                    print(f"  REJECTED: [{subfield}] proposal {i} — "
                          f"{blocking[0][:80] if blocking else 'No reason given'}")
                    rejection_summary.append({
                        "expert_index": expert_idx,
                        "subfield": subfield,
                        "proposal_index": i,
                        "title": p.get("title", ""),
                        "blocking_issues": blocking,
                    })

    total_proposals = sum(len(e.get("proposals", [])) for e in latest_proposals)
    print(f"--- Expert Acceptance: {len(accepted)}/{total_proposals} individual proposals accepted ---")

    # Fallback: if nothing was accepted, accept all individual proposals
    if not accepted and latest_proposals:
        print("  FALLBACK: No proposals accepted — accepting all to ensure workflow produces output.")
        for proposal_entry in latest_proposals:
            expert_idx = proposal_entry.get("expert_index")
            subfield = proposal_entry.get("subfield", f"expert_{expert_idx}")
            for i, p in enumerate(proposal_entry.get("proposals", [])):
                accepted.append({
                    "expert_index": expert_idx,
                    "subfield": subfield,
                    "proposal_index": i,
                    "title": p.get("title", "Untitled"),
                    "problem_statement": p.get("problem_statement", ""),
                    "motivation": p.get("motivation", ""),
                    "connections": p.get("connections", ""),
                    "potential_impact": p.get("potential_impact", ""),
                })

    # Save acceptance report
    arxiv_id = state.get("arxiv_id")
    if arxiv_id:
        experts_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / "4b_experts"
        experts_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "total_proposals": total_proposals,
            "accepted_count": len(accepted),
            "accepted": [
                {
                    "expert_index": p.get("expert_index"),
                    "subfield": p.get("subfield"),
                    "proposal_index": p.get("proposal_index"),
                    "title": p.get("title"),
                }
                for p in accepted
            ],
            "rejected": rejection_summary,
        }
        path = experts_dir / "acceptance_report.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"  > Saved acceptance report to {path}")

    return {"accepted_proposals": accepted}
