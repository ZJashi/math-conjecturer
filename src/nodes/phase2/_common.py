"""Common utilities for Phase 2 nodes."""

import os
import json
import re
import time
import requests
from pathlib import Path
from typing import Any, Dict, Type, TypeVar

from dotenv import find_dotenv, load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

load_dotenv(find_dotenv())
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Options: "tngtech/deepseek-r1t2-chimera:free" | "google/gemini-2.0-flash-001" | "anthropic/claude-3.5-sonnet"
MODEL_NAME = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

BASE_DIR = Path(__file__).resolve().parents[3]
PAPERS_DIR = BASE_DIR / "papers"

T = TypeVar('T', bound=BaseModel)


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def try_parse_json(json_str: str) -> dict | None:
    for transform in [
        lambda s: s,
        lambda s: re.sub(r'(?<!\\)\\([a-zA-Z])', r'\\\\' + r'\1', s),
        lambda s: s.replace('\\', '/'),
        lambda s: s.replace('\\', ''),
    ]:
        try:
            return json.loads(transform(json_str))
        except json.JSONDecodeError:
            pass
    return None


def extract_json_from_response(response_text: str) -> dict | None:
    for pattern in [r'```json\s*([\s\S]*?)\s*```', r'```\s*([\s\S]*?)\s*```', r'(\{[\s\S]*\})']:
        match = re.search(pattern, response_text)
        if match:
            result = try_parse_json(match.group(1) if '```' in pattern else match.group(0))
            if result:
                return result

    # Last resort: strip LaTeX and retry
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if json_match:
        result = try_parse_json(re.sub(r'\\([a-zA-Z]+)', r'LATEX_\1', json_match.group(0)))
        if result:
            return result

    return None


# ---------------------------------------------------------------------------
# OpenRouter API calls
# ---------------------------------------------------------------------------

def _post(payload: dict) -> str:
    response = requests.post(
        OPENROUTER_API_URL,
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=180,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def call_openrouter_direct(messages: list, temperature: float = 0.0, json_schema: dict | None = None) -> str:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    payload = {"model": MODEL_NAME, "messages": messages, "temperature": temperature}
    if json_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": json_schema.get("title", "response"), "strict": True, "schema": json_schema},
        }
    return _post(payload)


def call_openrouter_json_mode(messages: list, temperature: float = 0.0) -> str:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    return _post({"model": MODEL_NAME, "messages": messages, "temperature": temperature,
                  "response_format": {"type": "json_object"}})


# ---------------------------------------------------------------------------
# Structured output invocation with fallback strategies
# ---------------------------------------------------------------------------

def _try_invoke(call_fn, output_class: Type[T], max_retries: int, retry_delay: float,
                break_on: tuple = ()) -> T | None:
    """Retry call_fn, return parsed result or None. Breaks early if a known-unsupported error fires."""
    for attempt in range(max_retries):
        try:
            data = extract_json_from_response(call_fn())
            if data:
                return output_class.model_validate(data)
        except Exception as e:
            msg = str(e)
            if any(kw in msg for kw in break_on):
                return None
            print(f"  Attempt {attempt + 1} failed: {msg[:60]}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    return None


def invoke_with_structured_output(
    prompt: ChatPromptTemplate,
    output_class: Type[T],
    inputs: Dict[str, Any],
    max_retries: int = 3,
    retry_delay: float = 2.0,
    temperature: float = 0.0,
) -> T:
    schema = output_class.model_json_schema()
    messages = [
        {"role": "user" if msg.type == "human" else msg.type, "content": msg.content}
        for msg in prompt.format_messages(**inputs)
    ]

    print("  Trying JSON schema mode...")
    result = _try_invoke(
        lambda: call_openrouter_direct(messages, temperature=temperature, json_schema=schema),
        output_class, max_retries, retry_delay, break_on=("response_format", "json_schema"),
    )
    if result:
        return result

    print("  Trying JSON object mode...")
    result = _try_invoke(
        lambda: call_openrouter_json_mode(messages, temperature=temperature),
        output_class, max_retries, retry_delay, break_on=("response_format", "json"),
    )
    if result:
        return result

    print("  Trying prompt fallback...")
    required = schema.get("required", [])
    messages[-1]["content"] += (
        f"\n\nCRITICAL: Respond with ONLY a valid JSON object. "
        f"Required fields: {', '.join(required)}. No other text."
    )
    result = _try_invoke(
        lambda: call_openrouter_direct(messages, temperature=temperature),
        output_class, max_retries, retry_delay * 2,
    )
    if result:
        return result

    print("  WARNING: All strategies failed, returning default values")
    return create_default_result(output_class)


# ---------------------------------------------------------------------------
# Shared formatting helpers
# ---------------------------------------------------------------------------

def format_survey_as_text(survey: dict) -> str:
    settled = survey.get("settled_claims", [])
    return "\n".join([
        f"**Subfield: {survey.get('subfield', 'Unknown')}**", "",
        f"Paper Connections: {survey.get('paper_connections', '')}", "",
        f"State of the Art: {survey.get('state_of_the_art', '')}", "",
        "Landmark Results:",
        *[f"  - {r}" for r in survey.get("landmark_results", [])], "",
        "SETTLED CLAIMS (FORBIDDEN — do not propose anything on this list):",
        *([f"  - {s}" for s in settled] if settled else ["  (none identified)"]), "",
        f"Open Territory: {survey.get('open_territory', '')}", "",
        "Available Techniques:",
        *[f"  - {t}" for t in survey.get("available_techniques", [])], "",
        f"Cross-Field Bridges: {survey.get('cross_field_bridges', '')}",
    ])


def format_proposals_as_text(proposals: list) -> str:
    parts = []
    for i, p in enumerate(proposals):
        parts.append("\n".join([
            f"Proposal {i + 1}:",
            f"Title: {p.get('title', 'Untitled')}", "",
            "Problem Statement:", p.get("problem_statement", ""), "",
            "Potential Impact:", p.get("potential_impact", ""),
        ]))
    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# File saving
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def get_latest_r2_proposals(proposals: list) -> list:
    latest: dict = {}
    for p in proposals:
        idx = p.get("expert_index")
        if idx is not None:
            latest[idx] = p
    return list(latest.values())


def get_latest_r2_critiques(critiques: list) -> list:
    latest: dict = {}
    for c in critiques:
        idx = c.get("expert_index")
        if idx is not None:
            latest[idx] = c
    return list(latest.values())


def create_default_result(output_class: Type[T]) -> T:
    defaults = {}
    for field_name, field_info in output_class.model_fields.items():
        annotation = field_info.annotation
        if annotation == str:
            defaults[field_name] = "Unable to generate - model returned empty response"
        elif annotation == int:
            defaults[field_name] = 5
        elif annotation == float:
            defaults[field_name] = 50.0
        elif annotation == bool:
            defaults[field_name] = False
        elif hasattr(annotation, '__origin__') and annotation.__origin__ == list:
            defaults[field_name] = ["Unable to generate - model returned empty response"]
        elif hasattr(annotation, '__args__'):
            defaults[field_name] = annotation.__args__[0]
        else:
            defaults[field_name] = None
    return output_class.model_validate(defaults)
