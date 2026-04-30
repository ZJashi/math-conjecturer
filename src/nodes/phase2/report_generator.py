"""Report Generator node for Phase 2."""

from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from prompts.phase2 import REPORT_GENERATOR_SYSTEM, REPORT_GENERATOR_PROMPT
from schema.phase2 import Phase2State, ReportResult
from ._common import invoke_with_structured_output, save_text


def report_generator_node(state: Phase2State) -> Dict[str, Any]:
    print("--- Report Generator: Creating final report ---")

    prompt = ChatPromptTemplate.from_messages([("system", REPORT_GENERATOR_SYSTEM), ("human", REPORT_GENERATOR_PROMPT)])
    result = invoke_with_structured_output(
        prompt=prompt, output_class=ReportResult,
        inputs={"proposal": state["current_proposal"], "paper_summary": state["summary"], "mechanisms": state["mechanism"]},
        temperature=0.4,
    )

    report = f"# Problem Statement\n{result.problem_statement}\n\n## Potential Impact\n{result.potential_impact}\n"
    print(f"Generated report for proposal {state.get('proposal_num', '?')}")

    save_text(state, f"step4_open_problems/proposal_{state.get('proposal_num', 1)}", "final_report.md", report)
    return {"final_report": report}
