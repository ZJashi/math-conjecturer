import os
import time
from typing import Dict, List

import requests

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model options (set via OPENROUTER_MODEL env var or change default here):
# - "tngtech/deepseek-r1t2-chimera:free"  # Free but unreliable for JSON
# - "google/gemini-2.0-flash-001"         # Fast, good for JSON
# - "anthropic/claude-3.5-sonnet"         # Best quality
# - "openai/gpt-4o-mini"                  # Good balance
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

MAX_RETRIES = 5
INITIAL_BACKOFF = 2  # seconds


def call_openrouter(messages: List[Dict[str, str]],
                    model: str = DEFAULT_MODEL,
                    temperature: float = 0.0) -> str:

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set. Add it to src/.env")

    model_name = model.split("/")[-1]
    print(f"  [LLM] Calling {model_name}...", flush=True)

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                },
                timeout=180,
            )

            if response.status_code == 429:
                wait_time = INITIAL_BACKOFF * (2 ** attempt)
                print(f"  [LLM] Rate limited. Waiting {wait_time}s... (retry {attempt + 1}/{MAX_RETRIES})", flush=True)
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            print(f"  [LLM] Response received", flush=True)
            return response.json()["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_time = INITIAL_BACKOFF * (2 ** attempt)
                print(f"  [LLM] Error: {e}. Retrying in {wait_time}s...", flush=True)
                time.sleep(wait_time)

    raise RuntimeError(f"LLM call failed after {MAX_RETRIES} retries: {last_error}")
