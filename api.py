"""
FastAPI server for the Agentic GraphRAG pipeline.
Exposes a simple POST /ask endpoint for the frontend.

Usage:
    pip install fastapi uvicorn
    python api.py
"""
import os, json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load .env
_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if _line.strip() and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from agent import answer as agent_answer
from retriever import Retriever

app = FastAPI(title="Taxxa GraphRAG API", version="1.0")

# Allow CORS for Lovable frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your Lovable domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load retriever once at startup
retriever = None

@app.on_event("startup")
def startup():
    global retriever
    print("Loading retriever...")
    retriever = Retriever()
    print("Retriever ready!")


class AskRequest(BaseModel):
    question: str


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
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Retriever not loaded yet")
    if len(req.question) > 2000:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Question too long (max 2000 chars)")
    try:
        result = agent_answer(req.question, retriever, verbose=False)
        return AskResponse(**result)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)[:200]}")


@app.get("/health")
def health():
    return {"status": "ok", "retriever_loaded": retriever is not None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
