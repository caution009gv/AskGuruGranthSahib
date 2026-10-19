"""
AskGuruGranthSahib - FastAPI Backend Server
Serves the chat API and static frontend files.
"""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_engine import RAGEngine

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AskGuruGranthSahib")

# --- Global RAG engine ---
rag_engine: RAGEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the RAG engine on startup."""
    global rag_engine
    try:
        logger.info("🙏 Initializing AskGuruGranthSahib RAG engine...")
        rag_engine = RAGEngine()
        stats = rag_engine.get_collection_stats()
        logger.info(f"✅ Knowledge base loaded: {stats['total_chunks']} chunks")
        yield
    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        logger.error("   Run 'python ingest.py <pdf-path>' first to build the knowledge base.")
        rag_engine = None
        yield
    except Exception as e:
        logger.error(f"❌ Failed to initialize RAG engine: {e}")
        rag_engine = None
        yield


# --- FastAPI App ---
app = FastAPI(
    title="AskGuruGranthSahib",
    description="AI-powered Q&A based on Sri Guru Granth Sahib Ji",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---
class QuestionRequest(BaseModel):
    question: str


class SourceReference(BaseModel):
    ang: int | str
    text: str


class AnswerResponse(BaseModel):
    answer: str
    sources: list[SourceReference]


class StatsResponse(BaseModel):
    total_chunks: int
    collection_name: str
    status: str


# --- API Endpoints ---
@app.post("/api/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question about Sri Guru Granth Sahib Ji."""
    if rag_engine is None:
        raise HTTPException(
            status_code=503,
            detail="Knowledge base not initialized. Run ingest.py first.",
        )

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        logger.info(f"📝 Question: {request.question[:100]}...")
        result = rag_engine.ask(request.question)
        logger.info(f"✅ Answer generated with {len(result['sources'])} source references")
        return AnswerResponse(**result)
    except Exception as e:
        logger.error(f"❌ Error processing question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reset")
async def reset_conversation():
    """Reset the conversation history."""
    if rag_engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized.")

    rag_engine.reset_memory()
    return {"message": "Conversation history cleared."}


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get knowledge base statistics."""
    if rag_engine is None:
        return StatsResponse(
            total_chunks=0,
            collection_name="N/A",
            status="not_initialized",
        )

    stats = rag_engine.get_collection_stats()
    return StatsResponse(**stats, status="ready")


# --- Serve Frontend ---
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# --- Run with uvicorn ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
