import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
PAPERS_DIR = BASE_DIR / "papers"


def save_proposals(arxiv_id: str, proposals: list) -> None:
    out_dir = PAPERS_DIR / arxiv_id / "baseline"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "proposals.json").write_text(
        json.dumps({"proposals": proposals}, indent=2), encoding="utf-8"
    )

    md = "# Baseline Proposals\n\n"
    for i, p in enumerate(proposals, 1):
        md += f"## Proposal {i}: {p.get('title', 'Untitled')}\n\n"
        md += f"### Problem Statement\n{p.get('problem_statement', '')}\n\n"
        md += f"### Potential Impact\n{p.get('potential_impact', '')}\n\n"
    (out_dir / "proposals.md").write_text(md, encoding="utf-8")

    print(f"  > Saved to papers/{arxiv_id}/baseline/")