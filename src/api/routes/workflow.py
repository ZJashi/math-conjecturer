"""Workflow API routes with SSE streaming."""

import asyncio
import uuid
import threading
import logging
from queue import Queue
from typing import Dict, Optional, Any

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)

from ..models import (
    JobStatus,
    JobStatusResponse,
    UserAction,
    UserActionRequest,
    UserActionResponse,
    WorkflowStartRequest,
    WorkflowStartResponse,
)
from ..sse import SSEEmitter

# Import workflow components
from workflow.phase1 import build_phase1_workflow
from workflow.phase2 import create_phase2_workflow
from nodes.phase1 import critic_node, revision_node, mechanism_node

router = APIRouter(prefix="/api/workflow", tags=["workflow"])

# Node name to display name mapping
PHASE1_NODE_NAMES = {
    "ingest": "Download & Process Paper",
    "summarize": "Generate Summary",
    "critic": "Critic Evaluation",
    "mechanism": "Extract Mechanism",
}

PHASE2_NODE_NAMES = {
    "context_ingestion": "Context Ingestion",
    "agenda_creator": "Create Research Agenda",
    "brainstormer": "Generate Proposal",
    "sanity_checker": "Sanity Check",
    "example_tester": "Example Testing",
    "reverse_reasoner": "Reverse Reasoning",
    "obstruction_analyzer": "Obstruction Analysis",
    "feedback_consolidator": "Consolidate Feedback",
    "done_decision": "Done Decision",
    "report_generator": "Generate Report",
    "final_judge": "Final Judgment",
    "quality_score": "Quality Assessment",
}


class JobState:
    """State for a workflow job."""

    def __init__(self, job_id: str, arxiv_id: str):
        self.job_id = job_id
        self.arxiv_id = arxiv_id
        self.status = JobStatus.PENDING
        self.current_step: Optional[str] = None
        self.phase: int = 1
        self.iteration: int = 1
        self.error: Optional[str] = None

        # Workflow state
        self.phase1_state: Optional[Dict] = None
        self.phase2_state: Optional[Dict] = None

        # User action handling
        self.user_action_event = asyncio.Event()
        self.user_action: Optional[UserAction] = None

        # SSE emitter
        self.emitter = SSEEmitter()

        # Event queue for real-time streaming from sync threads
        self.event_queue: Queue = Queue()


# In-memory job storage
jobs: Dict[str, JobState] = {}


def run_phase1_stream_thread(job: JobState, initial_state: dict):
    """Run Phase 1 workflow in a thread, pushing events to queue."""
    try:
        phase1_app = build_phase1_workflow()
        state = dict(initial_state)

        for event in phase1_app.stream(initial_state):
            for node_name, state_update in event.items():
                state.update(state_update)
                job.event_queue.put(("node_complete", node_name, dict(state)))

        job.event_queue.put(("phase1_done", None, state))

    except Exception as e:
        job.event_queue.put(("error", str(e), None))


def run_phase2_stream_thread(job: JobState, summary: str, mechanism: str, arxiv_id: str, max_iterations: int):
    """Run Phase 2 workflow in a thread, pushing events to queue."""
    try:
        workflow = create_phase2_workflow(
            max_iterations=max_iterations,
            save_visualization=False,
        )

        initial_state = {
            "summary": summary,
            "mechanism": mechanism,
            "arxiv_id": arxiv_id,
            "max_iterations": max_iterations,
            "critiques": [],
        }

        state = {}
        for event in workflow.stream(initial_state):
            for node_name, state_update in event.items():
                state.update(state_update)
                job.event_queue.put(("node_complete", node_name, dict(state)))

        job.event_queue.put(("phase2_done", None, state))

    except Exception as e:
        job.event_queue.put(("error", str(e), None))


@router.post("/start", response_model=WorkflowStartResponse)
async def start_workflow(request: WorkflowStartRequest) -> WorkflowStartResponse:
    """Start a new workflow job."""
    job_id = str(uuid.uuid4())
    job = JobState(job_id, request.arxiv_id)
    jobs[job_id] = job

    # Start the workflow in background
    asyncio.create_task(run_workflow(job))

    return WorkflowStartResponse(
        job_id=job_id,
        stream_url=f"/api/workflow/{job_id}/stream"
    )


@router.get("/{job_id}/stream")
async def stream_workflow(job_id: str):
    """SSE stream for workflow progress."""
    logger.info(f"Stream requested for job {job_id}")
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    logger.info(f"Job found, status={job.status}, emitter queue size={job.emitter._queue.qsize()}")

    async def event_generator():
        logger.info("Event generator started")
        async for event in job.emitter.events():
            logger.info(f"Yielding to SSE: {event[:50]}...")
            yield event
        logger.info("Event generator finished")

    return EventSourceResponse(event_generator())


@router.post("/{job_id}/action", response_model=UserActionResponse)
async def send_action(job_id: str, request: UserActionRequest) -> UserActionResponse:
    """Send a user action to resume workflow."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job.status != JobStatus.WAITING_FOR_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not waiting for user action. Current status: {job.status}"
        )

    job.user_action = request.action
    job.user_action_event.set()

    return UserActionResponse(status="ok", message=f"Action '{request.action.value}' received")


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_status(job_id: str) -> JobStatusResponse:
    """Get the current status of a workflow job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=job.status,
        current_step=job.current_step,
        phase=job.phase,
        iteration=job.iteration,
        error=job.error
    )


async def run_workflow(job: JobState) -> None:
    """Run the complete workflow with SSE streaming."""
    try:
        job.status = JobStatus.RUNNING
        await run_phase1(job)

        # After phase 1, ask user if they want phase 2
        if job.status == JobStatus.RUNNING:
            await job.emitter.emit_user_action_required(
                action="phase2_decision",
                options=["start_phase2", "skip_phase2"],
                message="Phase 1 complete! Would you like to proceed to Phase 2: Open Problem Formulation?"
            )

            job.status = JobStatus.WAITING_FOR_USER
            await job.user_action_event.wait()
            job.user_action_event.clear()

            if job.user_action == UserAction.START_PHASE2:
                job.status = JobStatus.RUNNING
                await run_phase2(job)
            else:
                await job.emitter.emit_complete()

        job.status = JobStatus.COMPLETED

    except Exception as e:
        job.status = JobStatus.ERROR
        job.error = str(e)
        await job.emitter.emit_error(str(e), job.current_step)

    finally:
        await job.emitter.close()


async def run_phase1(job: JobState) -> None:
    """Run Phase 1: Paper processing pipeline with critic loop."""
    logger.info(f"run_phase1 started for job {job.job_id}")
    emitter = job.emitter
    job.phase = 1

    # Initial state
    initial_state = {
        "arxiv_id": job.arxiv_id,
        "tex": "",
        "summary": "",
        "iteration": 1,
    }

    # Emit start for first step
    job.current_step = "ingest"
    logger.info("Emitting step_start for ingest...")
    await emitter.emit_step_start("ingest", f"Downloading and processing arXiv paper {job.arxiv_id}...")
    logger.info("step_start emitted")

    # Start streaming thread
    thread = threading.Thread(
        target=run_phase1_stream_thread,
        args=(job, initial_state)
    )
    thread.start()

    # Process events from queue in real-time
    state = dict(initial_state)
    last_node = None

    while True:
        # Check queue with timeout to allow async operations
        await asyncio.sleep(0.1)

        while not job.event_queue.empty():
            event_type, node_name, event_state = job.event_queue.get_nowait()

            if event_type == "error":
                raise Exception(node_name)  # node_name contains error message

            if event_type == "phase1_done":
                state = event_state
                # Emit final step complete if needed
                if last_node:
                    await emitter.emit_step_complete(
                        last_node,
                        output=state.get(last_node, ""),
                        message=f"{PHASE1_NODE_NAMES.get(last_node, last_node)} complete"
                    )
                break

            if event_type == "node_complete":
                state = event_state
                job.current_step = node_name
                display_name = PHASE1_NODE_NAMES.get(node_name, node_name)

                # Emit step complete for previous node
                if last_node and last_node != node_name:
                    output = None
                    if last_node == "summarize":
                        output = state.get("summary", "")
                    elif last_node == "critic":
                        output = state.get("critique", "")
                    elif last_node == "mechanism":
                        output = state.get("mechanism", "")

                    await emitter.emit_step_complete(
                        last_node,
                        output=output,
                        message=f"{PHASE1_NODE_NAMES.get(last_node, last_node)} complete"
                    )

                # Emit step start for current node
                await emitter.emit_step_start(node_name, f"Running {display_name}...")
                last_node = node_name
        else:
            # Queue was empty, check if thread is done
            if not thread.is_alive() and job.event_queue.empty():
                break
            continue

        break  # Exit after processing phase1_done

    thread.join()

    # Emit outputs for last node
    if last_node:
        output = None
        if last_node == "summarize":
            output = state.get("summary", "")
        elif last_node == "critic":
            output = state.get("critique", "")
        elif last_node == "mechanism":
            output = state.get("mechanism", "")

        await emitter.emit_step_complete(
            last_node,
            output=output,
            message=f"{PHASE1_NODE_NAMES.get(last_node, last_node)} complete"
        )

    # Now handle critic revision loop
    max_iterations = 10
    while state.get("iteration", 1) <= max_iterations:
        critic_status = state.get("critic_status", "NEEDS_REVISION")
        iteration = state.get("iteration", 1)
        job.iteration = iteration

        # Emit current state
        await emitter.emit_phase_complete(
            phase=1,
            summary=state.get("summary", ""),
            critique=state.get("critique", ""),
            critic_status=critic_status,
            iteration=iteration
        )

        # If critic says PASS, we're done with revision loop
        if critic_status == "PASS":
            await emitter.emit_step_progress("critic", "Summary approved by critic!")
            break

        # Ask user for action
        await emitter.emit_user_action_required(
            action="refinement_decision",
            options=["continue", "stop"],
            message=f"Iteration {iteration}: The critic found issues. Continue refinement or accept current summary?"
        )

        job.status = JobStatus.WAITING_FOR_USER
        await job.user_action_event.wait()
        job.user_action_event.clear()
        job.status = JobStatus.RUNNING

        if job.user_action == UserAction.STOP:
            await emitter.emit_step_progress("critic", "User accepted current summary")
            break

        # Continue revision
        job.current_step = "revision"
        await emitter.emit_step_start("revision", f"Revising summary (iteration {iteration + 1})...")

        # Run revision node in thread
        def run_revision():
            return revision_node(state)

        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(None, run_revision)
        await emitter.emit_step_complete("revision", message="Summary revised")

        # Run critic on revised summary
        job.current_step = "critic"
        await emitter.emit_step_start("critic", "Running critic evaluation...")

        def run_critic():
            return critic_node(state)

        state = await loop.run_in_executor(None, run_critic)
        await emitter.emit_step_complete(
            "critic",
            output=state.get("critique", ""),
            message=f"Critic status: {state.get('critic_status', 'UNKNOWN')}"
        )

    # Re-run mechanism extraction if there were revisions
    if state.get("iteration", 1) > 1:
        job.current_step = "mechanism"
        await emitter.emit_step_start("mechanism", "Re-extracting mechanism from revised summary...")

        def run_mechanism():
            return mechanism_node(state)

        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(None, run_mechanism)
        await emitter.emit_step_complete(
            "mechanism",
            output=state.get("mechanism", ""),
            message="Mechanism graph extracted"
        )

    # Store phase 1 state
    job.phase1_state = state

    # Emit phase 1 complete
    await emitter.emit_phase_complete(
        phase=1,
        summary=state.get("summary", ""),
        mechanism=state.get("mechanism", ""),
        iteration=state.get("iteration", 1)
    )


async def run_phase2(job: JobState) -> None:
    """Run Phase 2: Open Problem Formulation with streaming updates."""
    emitter = job.emitter
    job.phase = 2
    job.iteration = 1

    if not job.phase1_state:
        raise ValueError("Phase 1 state not available")

    # Clear event queue
    while not job.event_queue.empty():
        job.event_queue.get_nowait()

    # Start Phase 2
    await emitter.emit_step_start("phase2", "Starting Phase 2: Open Problem Formulation...")

    # Start streaming thread
    thread = threading.Thread(
        target=run_phase2_stream_thread,
        args=(
            job,
            job.phase1_state["summary"],
            job.phase1_state["mechanism"],
            job.phase1_state.get("arxiv_id"),
            5  # max_iterations
        )
    )
    thread.start()

    # Process events from queue in real-time
    state: Dict[str, Any] = {}
    last_node = None

    while True:
        await asyncio.sleep(0.1)

        while not job.event_queue.empty():
            event_type, node_name, event_state = job.event_queue.get_nowait()

            if event_type == "error":
                raise Exception(node_name)

            if event_type == "phase2_done":
                state = event_state
                # Emit final step complete
                if last_node:
                    await emitter.emit_step_complete(
                        last_node,
                        message=f"{PHASE2_NODE_NAMES.get(last_node, last_node)} complete"
                    )
                break

            if event_type == "node_complete":
                state = event_state
                job.current_step = node_name
                display_name = PHASE2_NODE_NAMES.get(node_name, node_name)

                # Emit step complete for previous node
                if last_node and last_node != node_name:
                    await emitter.emit_step_complete(
                        last_node,
                        message=f"{PHASE2_NODE_NAMES.get(last_node, last_node)} complete"
                    )

                # Emit step start for current node
                await emitter.emit_step_start(node_name, f"Running {display_name}...")

                # Track iteration from brainstormer
                if node_name == "brainstormer":
                    iteration = state.get("phase2_iteration", 1)
                    job.iteration = iteration
                    await emitter.emit_step_progress(
                        node_name,
                        f"Iteration {iteration}: Generating proposal..."
                    )

                # Emit intermediate outputs for key nodes
                if node_name == "agenda_creator" and state.get("agenda"):
                    await emitter.emit_step_progress(
                        node_name,
                        f"Created {len(state['agenda'])} research directions"
                    )

                if node_name == "done_decision":
                    is_done = state.get("is_done", False)
                    reason = state.get("done_reason", "")
                    if is_done:
                        await emitter.emit_step_progress(node_name, f"Decision: Done - {reason}")
                    else:
                        await emitter.emit_step_progress(node_name, "Decision: Continue refining...")

                last_node = node_name
        else:
            if not thread.is_alive() and job.event_queue.empty():
                break
            continue

        break

    thread.join()

    # Emit final step complete if we didn't already
    if last_node:
        await emitter.emit_step_complete(
            last_node,
            message=f"{PHASE2_NODE_NAMES.get(last_node, last_node)} complete"
        )

    job.phase2_state = state

    # Emit completion with results
    await emitter.emit_step_complete(
        "phase2",
        message="Phase 2 complete"
    )

    await emitter.emit_complete(
        final_report=state.get("final_report"),
        quality_score=state.get("quality_score"),
        quality_category=state.get("quality_category"),
        quality_assessment=state.get("quality_assessment")
    )
