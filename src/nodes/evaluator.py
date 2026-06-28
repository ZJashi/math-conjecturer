from prompts import EVALUATOR_SYSTEM, EVALUATOR_PROMPT
from schema.state import GraphState
from utils.format import format_proposals
from utils.openrouter import call_openrouter
from utils.output import save_evaluations
from utils.parse import extract_json


def baseline_evaluator_node(state: GraphState) -> dict:
    print("--- Baseline Evaluator ---")

    proposals = state.get("proposals") or []
    prompt = (EVALUATOR_PROMPT
              .replace("{paper}", state["tex"])
              .replace("{proposals}", format_proposals(proposals)))
    messages = [
        {"role": "system", "content": EVALUATOR_SYSTEM},
        {"role": "user",   "content": prompt},
    ]

    response = call_openrouter(messages, temperature=0.3, json_mode=True)
    data = extract_json(response)

    if data is None:
        print(f"  WARNING: JSON extraction failed. Full raw response:\n{response}")
    evaluations = data.get("evaluations", []) if data else []
    print(f"  Evaluated {len(evaluations)} proposal(s)")

    save_evaluations(state["arxiv_id"], evaluations)

    return {"evaluations": evaluations}
