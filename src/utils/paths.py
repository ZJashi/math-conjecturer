"""Shared filesystem constants for the project."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
PAPERS_DIR = BASE_DIR / "papers"
