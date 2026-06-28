import time
from typing import Dict, List

import requests

from settings import OPENROUTER_API_KEY, OPENROUTER_MODEL

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_RETRIES = 5
INITIAL_BACKOFF = 2


def call_openrouter(messages: List[Dict[str, str]],
                    model: str = OPENROUTER_MODEL,
                    temperature: float = 0.0,
                    json_mode: bool = False) -> str:

    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set. Add it to src/.env")

    model_name = model.split("/")[-1]
    print(f"  [LLM] Calling {model_name}...", flush=True)

    payload: Dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
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
