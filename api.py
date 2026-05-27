"""
FastAPI server for the Agentic GraphRAG pipeline.
Exposes a simple POST /ask endpoint for the frontend.

Usage:
    python api.py
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import config, logger
from agent import answer as agent_answer
from retriever import Retriever

app = FastAPI(title="Taxxa GraphRAG API", version="2.0", description="Agentic GraphRAG for Finnish Tax Law")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load retriever once at startup
retriever = None

@app.on_event("startup")
def startup():
    global retriever
    logger.info("Loading retriever...")
    retriever = Retriever()
    logger.info("Retriever ready!")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000, description="Tax law question")


class Citation(BaseModel):
    source_id: str
    doc_title: str
    section: str | None = None
    file: str | None = None
    url: str | None = None
    claim: str | None = None


class AskResponse(BaseModel):
    question: str
    answer: str
    assumption: str | None = None
    sub_queries: list[str] = []
    citations: list[Citation] = []
    unverified_claims: list[str] = []
    conflicts: list[str] = []
    logic_issues: list[str] = []
    confidence: float = 0.5
    confidence_label: str = "medium"
    context_node_count: int = 0


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not loaded yet")
    try:
        logger.info(f"Processing question: {req.question[:80]}...")
        result = agent_answer(req.question, retriever, verbose=False)
        logger.info(f"Answer generated (confidence: {result.get('confidence_label', '?')})")
        return AskResponse(**result)
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)[:200]}")


@app.get("/health")
def health():
    return {"status": "ok", "retriever_loaded": retriever is not None}


# ── Feedback endpoints ────────────────────────────────────────────────────────

from feedback import FeedbackEntry, save_feedback, get_feedback_stats


class FeedbackRequest(BaseModel):
    request_id: str
    rating: str = Field(..., pattern="^(correct|partially_correct|wrong)$")
    correction: str = ""
    missing_info: str = ""


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    entry = FeedbackEntry(
        request_id=req.request_id,
        rating=req.rating,
        correction=req.correction,
        missing_info=req.missing_info,
    )
    save_feedback(entry)
    return {"status": "saved"}


@app.get("/feedback/stats")
def feedback_stats():
    return get_feedback_stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.api_host, port=config.api_port)
