import chainlit as cl
from pathlib import Path
from utils import app


@cl.on_chat_start
async def chat_start():
    """
    Runs once when a new chat session starts.
    """
    md_path = Path(__file__).parent / "chainlit.md"

    content = (
        md_path.read_text()
        if md_path.exists()
        else "👋 Welcome! Please enter an arXiv ID (e.g. 2301.12345)."
    )

    await cl.Message(content=content).send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    Runs ingestion + summarization in one shot.
    """
    arxiv_id = message.content.strip()

    if not arxiv_id:
        await cl.Message(
            content="⚠️ Please provide a valid arXiv ID."
        ).send()
        return

    await cl.Message(
        content=f"📄 Downloading, cleaning LaTeX, and summarizing `{arxiv_id}`..."
    ).send()

    # Run the full LangGraph (ingest → summarize)
    final_state = app.invoke({
        "arxiv_id": arxiv_id,
        "tex": "",
        "summary": ""
    })

    summary = final_state.get("summary", "❌ No summary produced.")

    await cl.Message(
        content=summary
    ).send()
