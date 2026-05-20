"""Common utilities for Phase 2 nodes."""

import json
import re
import time
import types as _types
from typing import Any, Dict, Type, TypeVar

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ValidationError

from utils.openrouter import DEFAULT_MODEL, call_openrouter, call_openrouter_json_schema, call_openrouter_json_mode
from utils.io import save_json, save_text  # noqa: F401 — re-exported for node convenience

EXPERTS_DIR = "step4_open_problems/4b_experts"

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
# Structured output invocation with fallback strategies
# ---------------------------------------------------------------------------

_ROLE_MAP = {"human": "user", "ai": "assistant"}


def _to_openrouter_messages(prompt: ChatPromptTemplate, inputs: dict) -> list[dict]:
    return [
        {"role": _ROLE_MAP.get(msg.type, msg.type), "content": msg.content}
        for msg in prompt.format_messages(**inputs)
    ]


def _try_invoke(call_fn, output_class: Type[T], max_retries: int, retry_delay: float,
                break_on: tuple = ()) -> T | None:
    """Retry call_fn, return parsed result or None.

    Breaks immediately on:
    - known unsupported-feature errors (break_on keywords)
    - Pydantic ValidationError: the response was valid JSON but wrong schema;
      retrying the same payload at low temperature won't help.
    """
    for attempt in range(max_retries):
        try:
            data = extract_json_from_response(call_fn())
            if data:
                return output_class.model_validate(data)
            # No JSON found in response — sleep before retry
            if attempt < max_retries - 1:
                print(f"  Attempt {attempt + 1}: no JSON in response, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
        except ValidationError as e:
            print(f"  Schema mismatch (not retrying): {str(e)[:120]}")
            return None
        except Exception as e:
            msg = str(e)
            if any(kw in msg for kw in break_on):
                return None
            # 4xx client errors are permanent — no point sleeping before the next attempt
            is_client_error = msg.startswith("4") and "Client Error" in msg
            print(f"  Attempt {attempt + 1} failed: {msg[:80]}")
            if attempt < max_retries - 1 and not is_client_error:
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
    messages = _to_openrouter_messages(prompt, inputs)

    print("  Trying JSON schema mode...")
    result = _try_invoke(
        lambda: call_openrouter_json_schema(messages, schema=schema, model=DEFAULT_MODEL, temperature=temperature),
        output_class, max_retries, retry_delay, break_on=("response_format", "json_schema", "400 Client Error"),
    )
    if result:
        return result

    print("  Trying JSON object mode...")
    result = _try_invoke(
        lambda: call_openrouter_json_mode(messages, model=DEFAULT_MODEL, temperature=temperature),
        output_class, max_retries, retry_delay, break_on=("response_format", "json", "400 Client Error"),
    )
    if result:
        return result

    print("  Trying prompt fallback...")
    required = schema.get("required", [])
    fallback_suffix = (
        f"\n\nCRITICAL: Respond with ONLY a valid JSON object. "
        f"Required fields: {', '.join(required)}. No other text."
    )
    fallback_messages = [
        *messages[:-1],
        {**messages[-1], "content": messages[-1]["content"] + fallback_suffix},
    ]
    result = _try_invoke(
        lambda: call_openrouter(fallback_messages, model=DEFAULT_MODEL, temperature=temperature),
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
        origin = getattr(annotation, '__origin__', None)
        # Optional[X] is Union[X, None] — use None
        is_optional = origin is _types.UnionType or str(origin) in ("<class 'typing.Union'>", "typing.Union")
        if is_optional:
            defaults[field_name] = None
        elif annotation == str:
            defaults[field_name] = "Unable to generate - model returned empty response"
        elif annotation == int:
            defaults[field_name] = 5
        elif annotation == float:
            defaults[field_name] = 50.0
        elif annotation == bool:
            defaults[field_name] = False
        elif origin is list:
            args = getattr(annotation, '__args__', None)
            item_type = args[0] if args else None
            if item_type is not None and isinstance(item_type, type) and issubclass(item_type, BaseModel):
                defaults[field_name] = [create_default_result(item_type)]
            else:
                defaults[field_name] = ["Unable to generate - model returned empty response"]
        else:
            defaults[field_name] = None
    return output_class.model_validate(defaults)
