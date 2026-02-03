"""
FastAPI application for Math Conjecturer.

This replaces the Chainlit interface with a faster FastAPI + SSE approach.
"""

import os
import sys
from pathlib import Path

# Disable LangSmith tracing to avoid threading/async context errors
# Set this BEFORE importing any LangChain modules
os.environ["LANGCHAIN_TRACING_V2"] = "false"

# Add src to path for imports
src_path = Path(__file__).resolve().parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.workflow import router as workflow_router

app = FastAPI(
    title="Math Conjecturer API",
    description="API for analyzing arXiv papers and generating research proposals",
    version="1.0.0"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(workflow_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Math Conjecturer API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
