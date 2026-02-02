"""
Utils package - shared utilities.

Note: Most functionality has been moved to dedicated packages:
- prompts/ - LLM prompts for both phases
- nodes/ - Node implementations for both phases
- workflow/ - LangGraph workflow definitions
- schema/ - State definitions and Pydantic models

This package now only contains shared utilities like OpenRouter.
"""

from .openrouter import call_openrouter

__all__ = [
    "call_openrouter",
]


def get_app():
    """Lazy import to avoid circular dependency."""
    from workflow.phase1 import build_phase1_workflow
    return build_phase1_workflow()


# Backward compatibility: provide app as a property
# Note: Use workflow.phase1.build_phase1_workflow() directly instead
app = None


def _init_app():
    global app
    if app is None:
        from workflow.phase1 import build_phase1_workflow
        app = build_phase1_workflow()
    return app
