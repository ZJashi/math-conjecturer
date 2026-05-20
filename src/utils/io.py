"""Shared file I/O utilities for saving node outputs."""

import json
from pathlib import Path

from .paths import PAPERS_DIR


def save_text(state: dict, rel_dir: str, filename: str, text: str) -> Path | None:
    arxiv_id = state.get("arxiv_id")
    if not arxiv_id:
        return None
    out_dir = PAPERS_DIR / arxiv_id / rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    path.write_text(text, encoding="utf-8")
    print(f"  > Saved to {path}")
    return path


def save_json(state: dict, rel_dir: str, filename: str, data: dict) -> Path | None:
    arxiv_id = state.get("arxiv_id")
    if not arxiv_id:
        return None
    out_dir = PAPERS_DIR / arxiv_id / rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  > Saved to {path}")
    return path
