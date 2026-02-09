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

# Model configuration
# Options (uncomment one):
# MODEL_NAME = "tngtech/deepseek-r1t2-chimera:free"  # Free but unreliable for JSON
# MODEL_NAME = "google/gemini-2.0-flash-001"         # Fast, good for JSON, ~$0.10/1M tokens
# MODEL_NAME = "anthropic/claude-3.5-sonnet"         # Best quality, ~$3/1M tokens
# MODEL_NAME = "openai/gpt-4o-mini"                  # Good balance, ~$0.15/1M tokens
MODEL_NAME = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Project paths
BASE_DIR = Path(__file__).resolve().parents[3]
PAPERS_DIR = BASE_DIR / "papers"

T = TypeVar('T', bound=BaseModel)


def try_parse_json(json_str: str) -> dict | None:
    """Try various strategies to parse JSON with potential escape issues."""

    # Strategy 1: Parse as-is
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Escape single backslashes followed by letters (LaTeX commands)
    # \alpha -> \\alpha, but \\alpha stays as \\alpha
    try:
        # Only escape single backslashes (not already escaped)
        fixed = re.sub(r'(?<!\\)\\([a-zA-Z])', r'\\\\' + r'\1', json_str)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Replace all backslashes with forward slashes (lose the math but get the structure)
    try:
        fixed = json_str.replace('\\', '/')
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Strategy 4: Remove all backslashes
    try:
        fixed = json_str.replace('\\', '')
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    return None


def extract_json_from_response(response_text: str) -> dict | None:
    """Extract and parse JSON from model response, handling various formats."""

    # Try different patterns to find JSON
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
        r'```\s*([\s\S]*?)\s*```',       # ``` ... ```
        r'(\{[\s\S]*\})',                 # Raw JSON object
    ]

    for pattern in patterns:
        match = re.search(pattern, response_text)
        if match:
            json_str = match.group(1) if '```' in pattern else match.group(0)

            # Try parsing with various escape handling strategies
            result = try_parse_json(json_str)
            if result:
                return result

    # Last resort: try to find any {...} and parse more aggressively
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if json_match:
        json_str = json_match.group(0)
        # Replace LaTeX commands with placeholders before parsing
        cleaned = re.sub(r'\\([a-zA-Z]+)', r'LATEX_\1', json_str)
        result = try_parse_json(cleaned)
        if result:
            return result

    return None


def call_openrouter_direct(
    messages: list,
    temperature: float = 0.0,
    json_schema: dict | None = None,
) -> str:
    """Call OpenRouter API directly with optional JSON schema enforcement."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
    }

    # Try structured output with JSON schema if provided
    if json_schema:
        # Method 1: OpenAI-compatible structured outputs (for supported models)
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": json_schema.get("title", "response"),
                "strict": True,
                "schema": json_schema,
            }
        }

    response = requests.post(
        OPENROUTER_API_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=180,
    )

    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def call_openrouter_json_mode(messages: list, temperature: float = 0.0) -> str:
    """Call OpenRouter with basic JSON mode (simpler, more compatible)."""
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
            "response_format": {"type": "json_object"},
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
    temperature: float = 0.0,
) -> T:
    """
    Invoke the model and parse response into structured output.

    Tries multiple strategies:
    1. JSON schema mode (strict structured output)
    2. JSON object mode (basic JSON enforcement)
    3. Prompt engineering fallback
    """
    # Get the schema for the output class
    schema = output_class.model_json_schema()

    # Format the prompt messages
    formatted_messages = prompt.format_messages(**inputs)

    # Convert to OpenRouter format
    messages = []
    for msg in formatted_messages:
        role = "user" if msg.type == "human" else msg.type
        if role == "human":
            role = "user"
        messages.append({"role": role, "content": msg.content})

    # Strategy 1: Try with JSON schema (strict mode)
    print(f"  Trying JSON schema mode...")
    for attempt in range(max_retries):
        try:
            response_text = call_openrouter_direct(
                messages, temperature=temperature, json_schema=schema
            )
            data = extract_json_from_response(response_text)
            if data:
                return output_class.model_validate(data)
        except requests.exceptions.RequestException as e:
            if "response_format" in str(e) or "json_schema" in str(e):
                print(f"  JSON schema not supported, trying JSON mode...")
                break
            print(f"  Schema attempt {attempt + 1} failed: {str(e)[:60]}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        except Exception as e:
            if "response_format" in str(e) or "json_schema" in str(e):
                print(f"  JSON schema not supported, trying JSON mode...")
                break
            print(f"  Schema attempt {attempt + 1} failed: {str(e)[:60]}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

    # Strategy 2: Try with basic JSON mode
    print(f"  Trying JSON object mode...")
    for attempt in range(max_retries):
        try:
            response_text = call_openrouter_json_mode(messages, temperature=temperature)
            data = extract_json_from_response(response_text)
            if data:
                return output_class.model_validate(data)
        except requests.exceptions.RequestException as e:
            if "response_format" in str(e) or "json" in str(e).lower():
                print(f"  JSON mode not supported, trying prompt fallback...")
                break
            print(f"  JSON mode attempt {attempt + 1} failed: {str(e)[:60]}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        except Exception as e:
            print(f"  JSON mode attempt {attempt + 1} failed: {str(e)[:60]}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

    # Strategy 3: Prompt engineering fallback
    print(f"  Trying prompt engineering fallback...")
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

CRITICAL: You MUST respond with ONLY a valid JSON object. No other text.

Required fields:
{chr(10).join(f'- {f}' for f in required_fields)}

Output ONLY valid JSON, nothing else."""

    messages[-1]["content"] += json_instruction

    for attempt in range(max_retries):
        try:
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
            response_text = response.json()["choices"][0]["message"]["content"]

            data = extract_json_from_response(response_text)
            if data:
                return output_class.model_validate(data)
            else:
                raise ValueError("No valid JSON found in response")

        except Exception as e:
            print(f"  Fallback attempt {attempt + 1} failed: {str(e)[:80]}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))

    # Last resort: return a default/empty result
    print("  WARNING: All strategies failed, returning default values")
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
