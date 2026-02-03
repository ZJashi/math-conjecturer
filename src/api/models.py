"""Pydantic request/response models for the API."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkflowStartRequest(BaseModel):
    """Request to start a new workflow."""
    arxiv_id: str = Field(..., description="arXiv paper ID (e.g., '2301.12345')")


class WorkflowStartResponse(BaseModel):
    """Response after starting a workflow."""
    job_id: str = Field(..., description="Unique job identifier")
    stream_url: str = Field(..., description="URL for SSE stream")


class JobStatus(str, Enum):
    """Possible job statuses."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_USER = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


class JobStatusResponse(BaseModel):
    """Response for job status query."""
    job_id: str
    status: JobStatus
    current_step: Optional[str] = None
    phase: Optional[int] = None
    iteration: Optional[int] = None
    error: Optional[str] = None


class UserAction(str, Enum):
    """User actions for workflow control."""
    CONTINUE = "continue"
    STOP = "stop"
    START_PHASE2 = "start_phase2"
    SKIP_PHASE2 = "skip_phase2"


class UserActionRequest(BaseModel):
    """Request to send a user action."""
    action: UserAction


class UserActionResponse(BaseModel):
    """Response after user action."""
    status: str = "ok"
    message: Optional[str] = None


# SSE Event Types
class SSEEventType(str, Enum):
    """Types of SSE events."""
    STEP_START = "step_start"
    STEP_PROGRESS = "step_progress"
    STEP_COMPLETE = "step_complete"
    USER_ACTION_REQUIRED = "user_action_required"
    PHASE_COMPLETE = "phase_complete"
    ERROR = "error"
    COMPLETE = "complete"


class SSEEvent(BaseModel):
    """Base SSE event model."""
    type: SSEEventType
    step: Optional[str] = None
    message: Optional[str] = None
    output: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class UserActionRequiredEvent(SSEEvent):
    """Event requiring user action."""
    type: SSEEventType = SSEEventType.USER_ACTION_REQUIRED
    action: str
    options: List[str]


class PhaseCompleteEvent(SSEEvent):
    """Event for phase completion."""
    type: SSEEventType = SSEEventType.PHASE_COMPLETE
    phase: int
    summary: Optional[str] = None
    mechanism: Optional[str] = None


class WorkflowCompleteEvent(SSEEvent):
    """Event for workflow completion."""
    type: SSEEventType = SSEEventType.COMPLETE
    final_report: Optional[str] = None
    quality_score: Optional[float] = None
    quality_category: Optional[str] = None
    quality_assessment: Optional[Dict[str, Any]] = None
