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

# Load environment variables
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Model configuration - use same as Phase 1
MODEL_NAME = "tngtech/deepseek-r1t2-chimera:free"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Project paths
BASE_DIR = Path(__file__).resolve().parents[3]
PAPERS_DIR = BASE_DIR / "papers"

T = TypeVar('T', bound=BaseModel)


def call_openrouter_direct(messages: list, temperature: float = 0.0) -> str:
    """Call OpenRouter API directly (same as Phase 1 approach)."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    response = requests.post(
        OPENROUTER_API_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
        },
        timeout=180,
    )

    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def invoke_with_structured_output(
    prompt: ChatPromptTemplate,
    output_class: Type[T],
    inputs: Dict[str, Any],
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> T:
    """
    Invoke the model and parse response into structured output.

    Uses direct API calls (like Phase 1) instead of LangChain's structured output
    which doesn't work well with this model.
    """
    # Get the schema for the output class
    schema = output_class.model_json_schema()

    # Simplify schema for the prompt
    required_fields = schema.get("required", [])
    properties = schema.get("properties", {})

    field_descriptions = []
    for field_name, field_info in properties.items():
        field_type = field_info.get("type", "string")
        desc = field_info.get("description", "")
        if field_type == "array":
            field_type = "list of strings"
        field_descriptions.append(f'  - "{field_name}": ({field_type}) {desc}')

    json_instruction = f"""

CRITICAL: You MUST respond with ONLY a valid JSON object. No other text before or after.

Required JSON structure:
{{
{chr(10).join(f'  "{f}": <value>' for f in required_fields)}
}}

Field descriptions:
{chr(10).join(field_descriptions)}

Remember: Output ONLY the JSON object, nothing else."""

    # Format the prompt messages
    formatted_messages = prompt.format_messages(**inputs)

    # Convert to OpenRouter format and add JSON instruction
    messages = []
    for msg in formatted_messages:
        role = "user" if msg.type == "human" else msg.type
        if role == "human":
            role = "user"
        messages.append({"role": role, "content": msg.content})

    # Add JSON instruction to the last message
    messages[-1]["content"] += json_instruction

    for attempt in range(max_retries):
        try:
            response_text = call_openrouter_direct(messages, temperature=0.0)

            # Try to extract JSON from the response
            # First try to find a JSON block
            json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    json_str = json_match.group()
                else:
                    raise ValueError("No JSON found in response")

            data = json.loads(json_str)
            return output_class.model_validate(data)

        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {str(e)[:80]}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))

    # Last resort: return a default/empty result
    print("  WARNING: All attempts failed, returning default values")
    return create_default_result(output_class)


def create_default_result(output_class: Type[T]) -> T:
    """Create a default/empty result for the given Pydantic class."""
    defaults = {}
    for field_name, field_info in output_class.model_fields.items():
        annotation = field_info.annotation
        if annotation == str:
            defaults[field_name] = "Unable to generate - model returned empty response"
        elif annotation == int:
            defaults[field_name] = 5  # Middle value for scores
        elif annotation == float:
            defaults[field_name] = 50.0
        elif annotation == bool:
            defaults[field_name] = False
        elif hasattr(annotation, '__origin__') and annotation.__origin__ == list:
            defaults[field_name] = ["Unable to generate - model returned empty response"]
        else:
            # For Literal types, try to get the first value
            if hasattr(annotation, '__args__'):
                defaults[field_name] = annotation.__args__[0]
            else:
                defaults[field_name] = None

    return output_class.model_validate(defaults)
