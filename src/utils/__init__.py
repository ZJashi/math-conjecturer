"""Shared utilities: LLM client, filesystem paths, and I/O helpers."""

from .openrouter import call_openrouter, call_openrouter_json_schema, call_openrouter_json_mode
from .paths import BASE_DIR, PAPERS_DIR
from .io import save_text, save_json

__all__ = [
    "call_openrouter",
    "call_openrouter_json_schema",
    "call_openrouter_json_mode",
    "BASE_DIR",
    "PAPERS_DIR",
    "save_text",
    "save_json",
]
