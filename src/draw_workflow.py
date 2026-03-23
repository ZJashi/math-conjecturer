"""Render the full end-to-end workflow as a single PNG."""

import base64
import requests
from pathlib import Path

MERMAID = """
flowchart TD
    subgraph P1["⬛ Phase 1: Paper Processing"]
        ingest([Ingest]) --> summarize([Summarize])
        summarize --> critic([Critic])
        critic --> p1dec{Accept?}
        p1dec -->|needs revision| revision([Revision])
        revision --> summarize
        p1dec -->|accepted| mechanism([Mechanism])
    end

    subgraph P2A["⬛ Phase 2A: Agenda + Expert Discussion"]
        ctx([Context Ingestion]) --> agenda([Agenda Creator])

        agenda --> e0r1([Expert 0 · R1])
        agenda --> e1r1([Expert 1 · R1])
        agenda --> e2r1([Expert 2 · R1])
        agenda --> e3r1([Expert 3 · R1])

        e0r1 & e1r1 & e2r1 & e3r1 --> sync([R2 Sync])

        sync --> e0r2([Expert 0 · R2])
        sync --> e1r2([Expert 1 · R2])
        sync --> e2r2([Expert 2 · R2])
        sync --> e3r2([Expert 3 · R2])

        e0r2 & e1r2 & e2r2 & e3r2 --> consolidator([Expert Consolidator])
    end

    subgraph P2B["⬛ Phase 2B: Proposal Loop ×3"]
        brainstorm([Brainstormer]) --> sc([Sanity Checker])
        brainstorm --> et([Example Tester])
        brainstorm --> rr([Reverse Reasoner])
        brainstorm --> oa([Obstruction Analyzer])

        sc & et & rr & oa --> fb([Feedback Consolidator])
        fb --> dec{Done?}
        dec -->|continue| brainstorm
        dec -->|exit| report([Report Generator])
        report --> mech_up([Mechanism Updater])
        mech_up --> judge([Final Judge])
        judge --> score([Quality Score])
    end

    mechanism --> ctx
    consolidator --> brainstorm
"""

def render(mermaid_str: str, out_path: Path, max_retries: int = 5):
    encoded = base64.urlsafe_b64encode(mermaid_str.strip().encode()).decode()
    url = f"https://mermaid.ink/img/{encoded}"
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            out_path.write_bytes(r.content)
            print(f"Saved {out_path}")
            return
        except Exception as e:
            print(f"  Attempt {attempt}/{max_retries} failed: {e}")
    raise RuntimeError("All retries failed")

out_dir = Path("../papers/workflow_diagrams")
out_dir.mkdir(parents=True, exist_ok=True)
render(MERMAID, out_dir / "full_workflow.png")
