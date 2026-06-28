"""Baseline proposer: single few-shot API call → 2 research proposals."""

from typing import Any, Dict

from prompts import BASELINE_SYSTEM, BASELINE_PROMPT
from utils.openrouter import call_openrouter
from utils.parse import extract_json
from utils.output import save_proposals


def baseline_proposer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    print("--- Baseline Proposer: Single few-shot API call ---")

    prompt = BASELINE_PROMPT.replace("{paper}", state["tex"])
    messages = [
        {"role": "system", "content": BASELINE_SYSTEM},
        {"role": "user",   "content": prompt},
    ]

    response = call_openrouter(messages, temperature=0.8, json_mode=True)
    data = extract_json(response)

    if data is None:
        print(f"  WARNING: JSON extraction failed. Full raw response:\n{response}")
    proposals = data.get("proposals", []) if data else []
    print(f"  Received {len(proposals)} proposal(s)")

    save_proposals(state["arxiv_id"], proposals)

    return {**state, "proposals": proposals}