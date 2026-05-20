import os
import time
from typing import Dict, List

import requests
from dotenv import find_dotenv, load_dotenv
from requests import HTTPError

load_dotenv(find_dotenv())

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model options (set via OPENROUTER_MODEL env var or change default here):
# - "tngtech/deepseek-r1t2-chimera:free"  # Free but unreliable for JSON
# - "google/gemini-2.0-flash-001"         # Fast, good for JSON
# - "anthropic/claude-3.5-sonnet"         # Best quality
# - "openai/gpt-4o-mini"                  # Good balance
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-5.3-chat")

MAX_RETRIES = 5
INITIAL_BACKOFF = 2  # seconds


def _call_with_retry(payload: dict) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set. Add it to src/.env")

    model_name = payload.get("model", "").split("/")[-1]
    print(f"  [LLM] Calling {model_name}...", flush=True)

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        wait_time = INITIAL_BACKOFF * (2 ** attempt)
        try:
            response = requests.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=180,
            )

            if response.status_code == 429:
                last_error = HTTPError(f"429 Rate Limited", response=response)
                print(f"  [LLM] Rate limited. Waiting {wait_time}s... (retry {attempt + 1}/{MAX_RETRIES})", flush=True)
                time.sleep(wait_time)
                continue

            response.raise_for_status()

            body = response.json()
            choices = body.get("choices") or []
            if not choices:
                # Provider returned 200 with an error body or empty choices
                err_msg = body.get("error", {}).get("message", "empty choices in response")
                last_error = RuntimeError(f"API error in response body: {err_msg}")
                print(f"  [LLM] Bad response body: {err_msg}. Retrying in {wait_time}s...", flush=True)
                time.sleep(wait_time)
                continue

            print(f"  [LLM] Response received", flush=True)
            return choices[0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                print(f"  [LLM] Error: {e}. Retrying in {wait_time}s...", flush=True)
                time.sleep(wait_time)

    raise RuntimeError(f"LLM call failed after {MAX_RETRIES} retries: {last_error}")


def call_openrouter(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
) -> str:
    return _call_with_retry({"model": model, "messages": messages, "temperature": temperature})


def call_openrouter_json_schema(
    messages: List[Dict[str, str]],
    schema: dict,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
) -> str:
    return _call_with_retry({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema.get("title", "response"), "strict": True, "schema": schema},
        },
    })


def call_openrouter_json_mode(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
) -> str:
    return _call_with_retry({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    })
