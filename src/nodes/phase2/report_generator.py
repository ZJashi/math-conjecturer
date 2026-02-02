"""Report Generator node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import BASE_SYSTEM_PROMPT, REPORT_GENERATOR_PROMPT
from schema.phase2 import Phase2State, ReportResult
from ._common import get_model, PAPERS_DIR


def report_generator_node(state: Phase2State) -> Dict[str, Any]:
    """
    Node 4: Report Generator

    Converts the final proposal into a polished report.
    """
    print("--- Report Generator: Creating final report ---")

    model = get_model()
    prompt = ChatPromptTemplate.from_messages([
        ("system", BASE_SYSTEM_PROMPT),
        ("human", REPORT_GENERATOR_PROMPT)
    ])

    chain = prompt | model.with_structured_output(ReportResult)

    result = chain.invoke({
        "proposal": state["current_proposal"],
        "paper_summary": state["summary"],
        "mechanisms": state["mechanism"],
        "iterations": state.get("phase2_iteration", 1),
    })

    # Format as markdown report
    report = f"""# {result.title}

## Executive Summary
{result.executive_summary}

## Problem Statement
{result.problem_statement}

## Background and Motivation
{result.background_and_motivation}

## Proposed Approach
{result.proposed_approach}

## Expected Challenges
{result.expected_challenges}

## Potential Impact
{result.potential_impact}

## References and Connections
{result.references_and_connections}
"""

    print(f"Generated report: {result.title}")

    # Save report to file if arxiv_id is available
    arxiv_id = state.get("arxiv_id")
    if arxiv_id:
        report_dir = PAPERS_DIR / arxiv_id / "step4_phase2"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "final_report.md"
        report_path.write_text(report, encoding="utf-8")
        print(f"  > Saved report to {report_path}")

    return {
        "final_report": report,
    }
