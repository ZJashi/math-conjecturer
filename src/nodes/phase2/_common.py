"""Common utilities for Phase 2 nodes."""

import os
from pathlib import Path
from typing import Any, Dict

from dotenv import find_dotenv, load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Model configuration
MODEL_NAME = "google/gemini-2.5-flash-lite"

# Project paths
BASE_DIR = Path(__file__).resolve().parents[3]
PAPERS_DIR = BASE_DIR / "papers"


def get_model() -> ChatOpenAI:
    """Get the configured LLM model via OpenRouter."""
    return ChatOpenAI(
        model=MODEL_NAME,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
    )
