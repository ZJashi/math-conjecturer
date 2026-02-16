"""Report Generator node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import REPORT_GENERATOR_SYSTEM, REPORT_GENERATOR_PROMPT
from schema.phase2 import Phase2State, ReportResult
from ._common import PAPERS_DIR, invoke_with_structured_output


def report_generator_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 4: Report Generator

    Converts the final proposal into a polished report.
    """
    print("--- Report Generator: Creating final report ---")

    prompt = ChatPromptTemplate.from_messages([
        ("system", REPORT_GENERATOR_SYSTEM),
        ("human", REPORT_GENERATOR_PROMPT)
    ])

    result = invoke_with_structured_output(
        prompt=prompt,
        output_class=ReportResult,
        inputs={
            "proposal": state["current_proposal"],
            "paper_summary": state["summary"],
            "mechanisms": state["mechanism"],
            "iterations": state.get("phase2_iteration", 1),
        },
        temperature=0.4,
    )

    # Format as markdown report
    report = f"""# Problem Statement
{result.problem_statement}

## Proposed Approach
{result.proposed_approach}

## Expected Challenges
{result.expected_challenges}

## Potential Impact
{result.potential_impact}
"""

    print(f"Generated report for proposal {state.get('proposal_num', '?')}")

    # Save report to file if arxiv_id is available
    arxiv_id = state.get("arxiv_id")
    proposal_num = state.get("proposal_num", 1)
    if arxiv_id:
        report_dir = PAPERS_DIR / arxiv_id / "step4_open_problems" / f"proposal_{proposal_num}"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "final_report.md"
        report_path.write_text(report, encoding="utf-8")
        print(f"  > Saved report to {report_path}")

    return {
        "final_report": report,
    }
