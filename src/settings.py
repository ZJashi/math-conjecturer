import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-5.3-chat")
NUM_PROPOSALS: int = int(os.getenv("NUM_PROPOSALS", "2"))