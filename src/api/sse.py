"""SSE (Server-Sent Events) streaming utilities."""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional

from .models import SSEEventType

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def format_sse_event(event_type: SSEEventType, data: Dict[str, Any]) -> str:
    """Format an event as SSE message."""
    event_data = {"type": event_type.value, **data}
    return f"data: {json.dumps(event_data)}\n\n"


class SSEEmitter:
    """
    SSE event emitter for streaming workflow progress.

    Usage:
        emitter = SSEEmitter()

        # In workflow:
        await emitter.emit_step_start("ingest", "Downloading paper...")

        # In SSE endpoint:
        async for event in emitter.events():
            yield event
    """

    def __init__(self):
        self._queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        self._closed = False

    async def emit(self, event_type: SSEEventType, **kwargs) -> None:
        """Emit an SSE event."""
        if self._closed:
            logger.warning(f"SSE Emitter closed, dropping: {event_type.value}")
            return
        event = format_sse_event(event_type, kwargs)
        logger.info(f"SSE EMIT: {event_type.value} step={kwargs.get('step', 'N/A')}")
        await self._queue.put(event)
        logger.info(f"SSE QUEUED: queue size={self._queue.qsize()}")

    async def emit_step_start(self, step: str, message: str) -> None:
        """Emit step start event."""
        await self.emit(SSEEventType.STEP_START, step=step, message=message)

    async def emit_step_progress(self, step: str, message: str, progress: Optional[int] = None) -> None:
        """Emit step progress event."""
        data = {"step": step, "message": message}
        if progress is not None:
            data["progress"] = progress
        await self.emit(SSEEventType.STEP_PROGRESS, **data)

    async def emit_step_complete(self, step: str, output: Any = None, message: str = None) -> None:
        """Emit step complete event."""
        data = {"step": step}
        if output is not None:
            data["output"] = output if isinstance(output, str) else json.dumps(output)
        if message:
            data["message"] = message
        await self.emit(SSEEventType.STEP_COMPLETE, **data)

    async def emit_user_action_required(self, action: str, options: list, message: str) -> None:
        """Emit user action required event."""
        await self.emit(
            SSEEventType.USER_ACTION_REQUIRED,
            action=action,
            options=options,
            message=message
        )

    async def emit_phase_complete(
        self,
        phase: int,
        summary: str = None,
        mechanism: str = None,
        iteration: int = None,
        critique: str = None,
        critic_status: str = None
    ) -> None:
        """Emit phase complete event."""
        data = {"phase": phase}
        if summary:
            data["summary"] = summary
        if mechanism:
            data["mechanism"] = mechanism
        if iteration is not None:
            data["iteration"] = iteration
        if critique:
            data["critique"] = critique
        if critic_status:
            data["critic_status"] = critic_status
        await self.emit(SSEEventType.PHASE_COMPLETE, **data)

    async def emit_error(self, error: str, step: str = None) -> None:
        """Emit error event."""
        data = {"error": error}
        if step:
            data["step"] = step
        await self.emit(SSEEventType.ERROR, **data)

    async def emit_complete(
        self,
        final_report: str = None,
        quality_score: float = None,
        quality_category: str = None,
        quality_assessment: dict = None
    ) -> None:
        """Emit workflow complete event."""
        data = {}
        if final_report:
            data["final_report"] = final_report
        if quality_score is not None:
            data["quality_score"] = quality_score
        if quality_category:
            data["quality_category"] = quality_category
        if quality_assessment:
            data["quality_assessment"] = quality_assessment
        await self.emit(SSEEventType.COMPLETE, **data)

    async def close(self) -> None:
        """Close the emitter and signal end of stream."""
        self._closed = True
        await self._queue.put(None)

    async def events(self) -> AsyncGenerator[str, None]:
        """Async generator that yields SSE events."""
        logger.info("SSE events() generator started")
        while True:
            logger.info(f"SSE waiting for event, queue size={self._queue.qsize()}")
            event = await self._queue.get()
            if event is None:
                logger.info("SSE received None, closing stream")
                break
            logger.info(f"SSE YIELDING event: {event[:80]}...")
            yield event
