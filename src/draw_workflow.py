"""Render the full end-to-end workflow as a single PNG."""

import base64
import requests
from pathlib import Path

MERMAID = """
flowchart TD
    subgraph P1["Phase 1: Paper Processing"]
        ingest([Ingest]) --> summarize([Summarize])
        summarize --> critic([Critic])
        critic --> p1dec{Accept?}
        p1dec -->|needs revision| revision([Revision])
        revision --> summarize
        p1dec -->|accepted| mechanism([Mechanism Extractor])
    end

    subgraph P2A["Phase 2A: Expert Literature Survey — Round 1 (parallel)"]
        e0r1([Expert 0 · R1\nLiterature Survey])
        e1r1([Expert 1 · R1\nLiterature Survey])
        e2r1([Expert 2 · R1\nLiterature Survey])
        e3r1([Expert 3 · R1\nLiterature Survey])
    end

    subgraph P2B["Phase 2B: Expert Proposal Writing — Round 2 (parallel, with revision loop)"]
        e0r2([Expert 0 · R2\n2 Proposals])
        e1r2([Expert 1 · R2\n2 Proposals])
        e2r2([Expert 2 · R2\n2 Proposals])
        e3r2([Expert 3 · R2\n2 Proposals])
    end

    subgraph P2C["Phase 2C: Per-Expert R2 Critic Review (parallel)"]
        c0([Critic 0\nNovelty · Precision\nFeasibility · Grounding])
        c1([Critic 1\nNovelty · Precision\nFeasibility · Grounding])
        c2([Critic 2\nNovelty · Precision\nFeasibility · Grounding])
        c3([Critic 3\nNovelty · Precision\nFeasibility · Grounding])
    end

    subgraph P2D["Phase 2D: Finalization — per accepted proposal"]
        report([Report Generator])
        judge([Final Judge\nPS + PI scores])
        mech_up([Mechanism Updater])
    end

    mechanism --> agenda([Agenda Creator\nDirections + Subfields])

    agenda --> e0r1
    agenda --> e1r1
    agenda --> e2r1
    agenda --> e3r1

    e0r1 & e1r1 & e2r1 & e3r1 --> r2sync([R2 Sync])

    r2sync --> e0r2
    r2sync --> e1r2
    r2sync --> e2r2
    r2sync --> e3r2

    e0r2 & e1r2 & e2r2 & e3r2 --> propsync([R2 Proposals Sync])

    propsync --> c0
    propsync --> c1
    propsync --> c2
    propsync --> c3

    c0 & c1 & c2 & c3 --> agg([R2 Critic Aggregate\nAll approved?])

    agg -->|approved or max iterations| accept([Expert Acceptance\nFlat list of approved proposals])
    agg -->|needs revision| dispatch([R2 Revision Dispatch])

    dispatch --> e0r2
    dispatch --> e1r2
    dispatch --> e2r2
    dispatch --> e3r2

    accept --> ranker([Problem Ranker\nBest-first order])

    ranker -->|"top N accepted proposals"| report
    report --> judge
    judge --> mech_up
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
