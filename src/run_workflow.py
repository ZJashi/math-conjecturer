#!/usr/bin/env python
"""
Baseline: single few-shot API call for research proposal generation.

Usage:
    uv run python run_workflow.py <arxiv_id>

Example:
    uv run python run_workflow.py 2512.01868
"""

import os
import sys
from pathlib import Path

os.environ["LANGCHAIN_TRACING_V2"] = "false"
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from workflow.baseline import build_baseline_workflow


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_workflow.py <arxiv_id>")
        print("Example: python run_workflow.py 2512.01868")
        sys.exit(1)

    arxiv_id = sys.argv[1]
    print(f"\n{'='*60}")
    print(f"BASELINE: Processing arXiv paper {arxiv_id}")
    print(f"{'='*60}\n")

    workflow = build_baseline_workflow()
    state = workflow.invoke({"arxiv_id": arxiv_id, "tex": "", "summary": "", "iteration": 1})

    proposals = state.get("proposals", [])
    print(f"\n{'='*60}")
    print(f"DONE — {len(proposals)} proposal(s) generated")
    print(f"{'='*60}")
    for i, p in enumerate(proposals, 1):
        print(f"\n  Proposal {i}: {p.get('title', 'Untitled')}")
        print(f"  {p.get('problem_statement', '')[:200]}...")

    print(f"\nFiles saved to papers/{arxiv_id}/baseline/")


if __name__ == "__main__":
    main()
