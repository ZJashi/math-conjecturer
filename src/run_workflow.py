#!/usr/bin/env python
"""
Baseline: single few-shot API call for research proposal generation.

Usage:
    uv run python run_workflow.py <arxiv_id> [arxiv_id2 ...]

Example:
    uv run python run_workflow.py 2512.01868
    uv run python run_workflow.py 2512.01868 2501.00001 2501.00002
"""

import os
import sys
from pathlib import Path

os.environ["LANGCHAIN_TRACING_V2"] = "false"
sys.path.insert(0, str(Path(__file__).parent))

import settings  # loads .env and exposes all config
from workflow.baseline import build_baseline_workflow


def run_one(workflow, arxiv_id: str) -> None:
    print(f"\n{'='*60}")
    print(f"BASELINE: Processing arXiv paper {arxiv_id}")
    print(f"{'='*60}\n")

    state = workflow.invoke({"arxiv_id": arxiv_id})

    proposals = state.get("proposals", [])
    evaluations = state.get("evaluations", [])
    print(f"\n{'='*60}")
    print(f"DONE — {len(proposals)} proposal(s), {len(evaluations)} evaluation(s)")
    print(f"{'='*60}")
    for i, p in enumerate(proposals, 1):
        print(f"\n  Proposal {i}: {p.get('title', 'Untitled')}")
        print(f"  {p.get('problem_statement', '')[:200]}...")
    for e in evaluations:
        print(f"\n  Eval {e.get('proposal_index', '?')}: "
              f"TS={e.get('technical_soundness', {}).get('score', '?')} "
              f"G={e.get('grounding', {}).get('score', '?')} "
              f"CD={e.get('conceptual_depth', {}).get('score', '?')} "
              f"→ {e.get('overall', '?')}/5")

    print(f"\nFiles saved to papers/{arxiv_id}/baseline/")


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_workflow.py <arxiv_id> [arxiv_id2 ...]")
        print("Example: python run_workflow.py 2512.01868 2501.00001")
        sys.exit(1)

    arxiv_ids = sys.argv[1:]
    workflow = build_baseline_workflow()

    failed = []
    for arxiv_id in arxiv_ids:
        try:
            run_one(workflow, arxiv_id)
        except Exception as e:
            print(f"\nERROR processing {arxiv_id}: {e}")
            failed.append(arxiv_id)

    if len(arxiv_ids) > 1:
        print(f"\n{'='*60}")
        print(f"Processed {len(arxiv_ids) - len(failed)}/{len(arxiv_ids)} papers successfully")
        if failed:
            print(f"Failed: {', '.join(failed)}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
