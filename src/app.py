from pathlib import Path

import chainlit as cl

from workflow.phase1 import build_phase1_workflow
from workflow.phase2 import run_phase2_workflow
from nodes.phase1 import critic_node, revision_node, mechanism_node

# Build the Phase 1 workflow
phase1_app = build_phase1_workflow()



from dotenv import load_dotenv
load_dotenv()


@cl.on_chat_start
async def chat_start():
    """
    Runs once when a new chat session starts.
    """
    md_path = Path(__file__).parent / "chainlit.md"

    content = (
        md_path.read_text()
        if md_path.exists()
        else "Welcome! Please enter an arXiv ID (e.g. 2301.12345)."
    )

    await cl.Message(content=content).send()






@cl.on_message
async def on_message(message: cl.Message):
    arxiv_id = message.content.strip()

    if not arxiv_id:
        await cl.Message(
            content="Please provide a valid arXiv ID."
        ).send()
        return

    # Step 1: Download and ingest
    await cl.Message(
        content=f"**Step 1:** Downloading and cleaning LaTeX for `{arxiv_id}`..."
    ).send()

    # Run the initial pipeline: ingest → summarize → critic → mechanism
    state = await cl.make_async(phase1_app.invoke)({
        "arxiv_id": arxiv_id,
        "tex": "",
        "summary": "",
        "iteration": 1,
    })

    await cl.Message(
        content="**Step 2:** Initial summary and mechanism extracted. Running critic evaluation..."
    ).send()

    # Enter the critic loop
    max_iterations = 10  # Safety limit

    while state.get("iteration", 1) <= max_iterations:
        critic_status = state.get("critic_status", "NEEDS_REVISION")
        iteration = state.get("iteration", 1)

        # Show iteration progress
        await cl.Message(
            content=f"---\n### Iteration {iteration} Complete\n---"
        ).send()

        # Show current summary
        await cl.Message(
            content=f"## Summary (Iteration {iteration})\n\n{state.get('summary', 'No summary produced.')}"
        ).send()

        # Show critic evaluation
        await cl.Message(
            content=f"## Critic Evaluation (Iteration {iteration})\n\n**Status:** {critic_status}\n\n{state.get('critique', 'No critique available.')}"
        ).send()

        # If critic says PASS, we're done
        if critic_status == "PASS":
            await cl.Message(
                content="The summary has been approved by the critic. Process complete!"
            ).send()
            break

        # Ask user if they want to continue refinement
        actions = [
            cl.Action(
                name="continue_refinement",
                payload={"action": "continue"},
                label="Continue Refinement",
                description="Let the agent revise the summary based on the critique"
            ),
            cl.Action(
                name="stop_refinement",
                payload={"action": "stop"},
                label="Accept Current Summary",
                description="Accept the current summary and stop refinement"
            ),
        ]

        response = await cl.AskActionMessage(
            content=f"**Iteration {iteration}:** The critic found issues with the summary. Would you like to continue refinement or accept the current summary?",
            actions=actions,
        ).send()

        if response is None or response.get("payload", {}).get("action") == "stop":
            await cl.Message(
                content="Stopping refinement. Using current summary."
            ).send()
            break

        # User wants to continue - run revision and critic
        await cl.Message(
            content=f"**Starting Iteration {iteration + 1}:** Revising summary based on critique..."
        ).send()

        # Run revision node
        state = await cl.make_async(revision_node)(state)

        await cl.Message(
            content=f"**Iteration {iteration + 1}:** Summary revised. Running critic evaluation..."
        ).send()

        # Run critic node on the revised summary
        state = await cl.make_async(critic_node)(state)

    # Final output
    if state.get("iteration", 1) > max_iterations:
        await cl.Message(
            content=f"Reached maximum iterations ({max_iterations}). Returning current summary."
        ).send()

    final_summary = state.get("summary", "No summary produced.")
    await cl.Message(
        content=f"## Final Summary\n\n{final_summary}"
    ).send()

    # Re-run mechanism extraction if there were revisions (iteration > 1)
    # Otherwise, mechanism was already extracted in the initial workflow
    if state.get("iteration", 1) > 1:
        await cl.Message(
            content="**Step 3:** Re-extracting mechanisms from revised summary..."
        ).send()
        state = await cl.make_async(mechanism_node)(state)

    mechanism_xml = state.get("mechanism", "No mechanism extracted.")
    await cl.Message(
        content=f"## Mechanism Graph (XML)\n\n```xml\n{mechanism_xml}\n```"
    ).send()

    await cl.Message(
        content=f"**Phase 1 complete!** Files saved to `papers/{arxiv_id}/` (step1_ingest, step2_summary, step2_critique, step3_mechanism)"
    ).send()

    # Ask user if they want to proceed to Phase 2
    phase2_actions = [
        cl.Action(
            name="start_phase2",
            payload={"action": "start"},
            label="Generate Open Problems",
            description="Proceed to Phase 2: Generate research proposals based on the summary"
        ),
        cl.Action(
            name="skip_phase2",
            payload={"action": "skip"},
            label="Skip Phase 2",
            description="End the session without generating open problems"
        ),
    ]

    phase2_response = await cl.AskActionMessage(
        content="Would you like to proceed to **Phase 2: Open Problem Formulation**? This will generate research proposals based on the summary and mechanism.",
        actions=phase2_actions,
    ).send()

    if phase2_response is None or phase2_response.get("payload", {}).get("action") == "skip":
        await cl.Message(
            content="Session complete. You can start a new session to analyze another paper."
        ).send()
        return

    # =========================================================================
    # PHASE 2: Open Problem Formulation
    # =========================================================================

    await cl.Message(
        content="---\n# Phase 2: Open Problem Formulation\n---"
    ).send()

    await cl.Message(
        content="Starting iterative proposal generation..."
    ).send()

    # Run Phase 2 workflow
    phase2_state = await cl.make_async(run_phase2_workflow)(
        summary=state["summary"],
        mechanism=state["mechanism"],
        arxiv_id=state["arxiv_id"],
        max_iterations=5,
    )

    # Display Phase 2 results
    await cl.Message(
        content=f"## Final Research Proposal\n\n{phase2_state.get('final_report', 'No report generated.')}"
    ).send()

    # Display quality assessment
    assessment = phase2_state.get("quality_assessment", {})
    score = phase2_state.get("quality_score", 0)
    category = phase2_state.get("quality_category", "N/A")

    await cl.Message(
        content=f"""## Quality Assessment

| Metric | Score |
|--------|-------|
| Clarity | {assessment.get('clarity_score', 'N/A')}/10 |
| Feasibility | {assessment.get('feasibility_score', 'N/A')}/10 |
| Novelty | {assessment.get('novelty_score', 'N/A')}/10 |
| Rigor | {assessment.get('rigor_score', 'N/A')}/10 |
| **Overall** | **{score:.1f}/100** |

**Verdict:** {assessment.get('verdict', 'N/A').upper()}

**Justification:** {assessment.get('justification', 'N/A')}
"""
    ).send()

    await cl.Message(
        content=f"**Phase 2 complete!** Files saved to `papers/{arxiv_id}/step4_open_problems/`"
    ).send()

