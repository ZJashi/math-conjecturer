from pathlib import Path

import chainlit as cl

from utils import app
from utils.critic_node import critic_node
from utils.revision_node import revision_node
from utils.mechanism_node import mechanism_node



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

    # Run the initial pipeline: ingest → summarize → critic
    state = await cl.make_async(app.invoke)({
        "arxiv_id": arxiv_id,
        "tex": "",
        "summary": "",
        "iteration": 1,
    })


    await cl.Message(
        content="**Step 2:** Initial summary generated. Running critic evaluation..."
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

    # Step 3: Mechanism Extraction
    await cl.Message(
        content="**Step 3:** Extracting core mechanisms from summary..."
    ).send()

    state = await cl.make_async(mechanism_node)(state)

    mechanism_xml = state.get("mechanism", "No mechanism extracted.")
    await cl.Message(
        content=f"## Mechanism Graph (XML)\n\n```xml\n{mechanism_xml}\n```"
    ).send()

    await cl.Message(
        content="Pipeline complete! Files saved to `papers/{arxiv_id}/`"
    ).send()

