import os
import requests
from typing import List, Dict

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "tngtech/deepseek-r1t2-chimera:free"


def call_openrouter(messages: List[Dict[str, str]],
                    model: str = DEFAULT_MODEL,
                    temperature: float = 0.0) -> str:

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

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

    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
