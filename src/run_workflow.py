#!/usr/bin/env python
"""
Simple script to run the workflow directly without UI.
Usage: python run_workflow.py <arxiv_id>
"""

import os
import sys
from pathlib import Path

# Disable LangSmith tracing to avoid noisy errors
os.environ["LANGCHAIN_TRACING_V2"] = "false"

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from workflow.phase1 import build_phase1_workflow
from workflow.phase2 import run_phase2_workflow
from nodes.phase1 import critic_node, revision_node, mechanism_node


def run_phase1(arxiv_id: str, max_revisions: int = 10):
    """Run Phase 1 workflow and return final state."""
    print(f"\n{'='*60}")
    print(f"PHASE 1: Processing arXiv paper {arxiv_id}")
    print(f"{'='*60}\n")

    # Build and run initial pipeline
    phase1_app = build_phase1_workflow()

    initial_state = {
        "arxiv_id": arxiv_id,
        "tex": "",
        "summary": "",
        "iteration": 1,
    }
    print("Running initial pipeline: ingest → summarize → critic → mechanism...")
    state = phase1_app.invoke(initial_state)

    # Interactive critic loop
    iteration = 1
    while iteration <= max_revisions:
        print(f"\n{'='*60}")
        print(f"ITERATION {iteration}")
        print(f"{'='*60}")

        print(f"\n--- SUMMARY ---")
        print(state.get("summary", "No summary"))

        print(f"\n--- CRITIC EVALUATION ---")
        print(f"Status: {state.get('critic_status', 'UNKNOWN')}")
        print(state.get("critique", "No critique"))

        # If critic says PASS, we're done
        if state.get("critic_status") == "PASS":
            print("\n✅ Summary APPROVED by critic!")
            break

        # Ask user what to do
        print(f"\n--- DECISION ---")
        print("The critic found issues. What would you like to do?")
        print("  [c] Continue refinement")
        print("  [a] Accept current summary")
        print("  [q] Quit")

        choice = input("\nYour choice (c/a/q): ").strip().lower()

        if choice == 'q':
            print("Quitting...")
            sys.exit(0)
        elif choice == 'a':
            print("Accepting current summary.")
            break
        elif choice == 'c':
            iteration += 1
            print(f"\n--- Running Revision {iteration} ---")

            print("Revising summary...")
            state = revision_node(state)

            print("Running critic evaluation...")
            state = critic_node(state)
        else:
            print("Invalid choice, please enter c, a, or q")

    # Re-run mechanism if revised
    if state.get("iteration", 1) > 1:
        print("\n--- Re-extracting mechanism from revised summary ---")
        state = mechanism_node(state)

    print(f"\n{'='*60}")
    print("PHASE 1 COMPLETE")
    print(f"{'='*60}")
    print(f"Final iteration: {state.get('iteration', 1)}")
    print(f"Critic status: {state.get('critic_status', 'UNKNOWN')}")

    return state


def run_phase2(phase1_state: dict, max_iterations: int = 5):
    """Run Phase 2 workflow, generating 3 proposals."""
    print(f"\n{'='*60}")
    print("PHASE 2: Open Problem Formulation (3 Proposals)")
    print(f"{'='*60}\n")

    result = run_phase2_workflow(
        summary=phase1_state["summary"],
        mechanism=phase1_state["mechanism"],
        arxiv_id=phase1_state.get("arxiv_id"),
        max_iterations=max_iterations,
    )

    print(f"\n{'='*60}")
    print("PHASE 2 COMPLETE")
    print(f"{'='*60}")
    proposals = result.get("proposals", [])
    for p in proposals:
        print(
            f"  Proposal {p['proposal_num']}: "
            f"PS={p.get('ps_score', 0)}/5 | PA={p.get('pa_score', 0)}/5 | "
            f"EC={p.get('ec_score', 0)}/5 | PI={p.get('pi_score', 0)}/5"
        )

    return result


def load_phase1_outputs(arxiv_id: str) -> dict:
    """Load existing Phase 1 outputs from papers directory."""
    papers_dir = Path(__file__).parent.parent / "papers" / arxiv_id

    # Try to load summary
    summary_dir = papers_dir / "step2_summary"
    summary = ""
    if summary_dir.exists():
        # Get the latest iteration
        summary_files = sorted(summary_dir.glob("iteration_*.md"), reverse=True)
        if summary_files:
            summary = summary_files[0].read_text()
            print(f"Loaded summary from {summary_files[0]}")

    # Try to load mechanism
    mechanism_file = papers_dir / "step3_mechanism" / "mechanism.xml"
    mechanism = ""
    if mechanism_file.exists():
        mechanism = mechanism_file.read_text()
        print(f"Loaded mechanism from {mechanism_file}")

    if not summary or not mechanism:
        print(f"ERROR: Could not find Phase 1 outputs in {papers_dir}")
        print("Make sure you've run Phase 1 first, or check the directory structure.")
        sys.exit(1)

    return {
        "arxiv_id": arxiv_id,
        "summary": summary,
        "mechanism": mechanism,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_workflow.py <arxiv_id> [--phase2-only]")
        print("Example: python run_workflow.py 2512.01868")
        print("         python run_workflow.py 2512.01868 --phase2-only")
        sys.exit(1)

    arxiv_id = sys.argv[1]
    phase2_only = "--phase2-only" in sys.argv

    if phase2_only:
        # Load existing Phase 1 outputs and go directly to Phase 2
        print(f"\n{'='*60}")
        print(f"Loading Phase 1 outputs for {arxiv_id}")
        print(f"{'='*60}\n")
        phase1_state = load_phase1_outputs(arxiv_id)
    else:
        # Run Phase 1
        phase1_state = run_phase1(arxiv_id)

        # Print Phase 1 outputs
        print("\n" + "="*60)
        print("PHASE 1 OUTPUTS")
        print("="*60)

        print("\n--- FINAL SUMMARY ---")
        print(phase1_state.get("summary", "No summary"))

        print("\n--- MECHANISM (XML) ---")
        print(phase1_state.get("mechanism", "No mechanism"))

        # Ask about Phase 2
        print(f"\n{'='*60}")
        print("PHASE 2: Open Problem Formulation")
        print(f"{'='*60}")
        print("\nWould you like to proceed to Phase 2?")
        print("This will generate research proposals based on the summary.")
        print("  [y] Yes, run Phase 2")
        print("  [n] No, exit")

        choice = input("\nYour choice (y/n): ").strip().lower()

        if choice != 'y':
            print(f"Exiting. Files saved to papers/{arxiv_id}/")
            return

    # Run Phase 2
    phase2_result = run_phase2(phase1_state)

    # Print Phase 2 outputs
    proposals = phase2_result.get("proposals", [])

    for p in proposals:
        print("\n" + "="*60)
        print(f"PROPOSAL {p['proposal_num']} OUTPUT")
        print("="*60)

        print(f"\n--- Direction ---")
        print(p.get("direction", "N/A"))

        print(f"\n--- Report ---")
        print(p.get("final_report", "No report"))

        print(f"\n--- Quality Assessment ---")
        assessment = p.get("quality_assessment", {})
        print(f"Problem Statement:  coherence={assessment.get('ps_coherence','N/A')} motivation={assessment.get('ps_motivation','N/A')} derivation={assessment.get('ps_derivation','N/A')} depth={assessment.get('ps_depth','N/A')}")
        print(f"Proposed Approach:  coherence={assessment.get('pa_coherence','N/A')} alignment={assessment.get('pa_alignment','N/A')} feasibility={assessment.get('pa_feasibility','N/A')}")
        print(f"Expected Challenges: identification={assessment.get('ec_identification','N/A')} tech_depth={assessment.get('ec_technical_depth','N/A')} complexity={assessment.get('ec_complexity','N/A')} strategies={assessment.get('ec_strategies','N/A')}")
        print(f"Potential Impact:   novelty={assessment.get('pi_novelty','N/A')} advancement={assessment.get('pi_advancement','N/A')} publication={assessment.get('pi_publication','N/A')}")
        print(f"Section scores: PS={p.get('ps_score',0)}/5 | PA={p.get('pa_score',0)}/5 | EC={p.get('ec_score',0)}/5 | PI={p.get('pi_score',0)}/5")

    # Summary table
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for p in proposals:
        print(
            f"  Proposal {p['proposal_num']}: "
            f"PS={p.get('ps_score',0)}/5 | PA={p.get('pa_score',0)}/5 | "
            f"EC={p.get('ec_score',0)}/5 | PI={p.get('pi_score',0)}/5 "
            f"- {p.get('iterations', 0)} iterations"
        )

    print(f"\nFiles saved to papers/{arxiv_id}/")


if __name__ == "__main__":
    main()
