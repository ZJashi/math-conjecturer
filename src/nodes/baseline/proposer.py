"""Baseline proposer: single few-shot API call → 2 research proposals."""

import json
import re
from pathlib import Path
from typing import Any, Dict

from prompts.baseline import BASELINE_SYSTEM, BASELINE_PROMPT
from utils.openrouter import call_openrouter

BASE_DIR = Path(__file__).resolve().parents[3]
PAPERS_DIR = BASE_DIR / "papers"


def _try_parse(raw: str) -> dict | None:
    # Try as-is first, then escape lone backslashes (common when model writes LaTeX)
    for transform in [
        lambda s: s,
        lambda s: re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', s),
    ]:
        try:
            return json.loads(transform(raw))
        except json.JSONDecodeError:
            pass
    return None


def _extract_json(text: str) -> dict | None:
    for pattern in [r"```json\s*([\s\S]*?)\s*```", r"```\s*([\s\S]*?)\s*```", r"(\{[\s\S]*\})"]:
        m = re.search(pattern, text)
        if m:
            raw = m.group(1) if "```" in pattern else m.group(0)
            result = _try_parse(raw)
            if result:
                return result
    return None


def baseline_proposer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    print("--- Baseline Proposer: Single few-shot API call ---")

    prompt = BASELINE_PROMPT.replace("{paper}", state["tex"])
    messages = [
        {"role": "system", "content": BASELINE_SYSTEM},
        {"role": "user",   "content": prompt},
    ]

    response = call_openrouter(messages, temperature=1.2, json_mode=True)
    data = _extract_json(response)

    if data is None:
        print(f"  WARNING: JSON extraction failed. Full raw response:\n{response}")
    proposals = data.get("proposals", []) if data else []
    print(f"  Received {len(proposals)} proposal(s)")

    # Save outputs
    arxiv_id = state.get("arxiv_id")
    if arxiv_id:
        out_dir = PAPERS_DIR / arxiv_id / "baseline"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Raw JSON
        (out_dir / "proposals.json").write_text(
            json.dumps({"proposals": proposals}, indent=2), encoding="utf-8"
        )

        # Human-readable Markdown
        md = "# Baseline Proposals\n\n"
        for i, p in enumerate(proposals, 1):
            md += f"## Proposal {i}: {p.get('title', 'Untitled')}\n\n"
            md += f"### Problem Statement\n{p.get('problem_statement', '')}\n\n"
            md += f"### Potential Impact\n{p.get('potential_impact', '')}\n\n"
        (out_dir / "proposals.md").write_text(md, encoding="utf-8")
        print(f"  > Saved to papers/{arxiv_id}/baseline/")

    return {**state, "proposals": proposals}
