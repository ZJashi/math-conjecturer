from .graph_state import GraphState
from .openrouter import call_openrouter
from prompts.paper_summarizer import CONTEXT_EXTRACTOR_SYSTEM_PROMPT, CONTEXT_EXTRACTOR_USER_PROMPT


def summarizer_node(state: GraphState) -> GraphState:
    print(">>> SUMMARIZER NODE ENTERED")
    print("LATEX LENGTH:", len(state["tex"]))

    messages = [
        {
         "role": "system",
         "content": CONTEXT_EXTRACTOR_SYSTEM_PROMPT.strip(),
        },
        {
        "role": "user",
        "content": CONTEXT_EXTRACTOR_USER_PROMPT.format(input_paper=state["tex"]),
        },
    ]

    summary = call_openrouter(messages, temperature=0.0,)

    print(">>> SUMMARY RECEIVED, LENGTH:", len(summary))

    return {"summary": summary}
