"""
Request tracing and token counting for the Taxxa pipeline.
Tracks LLM calls, latency, and token usage per request.
"""
import time
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4
from contextvars import ContextVar

from config import logger


@dataclass
class LLMCall:
    """Record of a single LLM API call."""
    agent: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    success: bool = True
    error: str = ""


@dataclass
class RequestTrace:
    """Full trace of a single user request through the pipeline."""
    request_id: str = field(default_factory=lambda: uuid4().hex[:12])
    question: str = ""
    start_time: float = field(default_factory=time.time)
    llm_calls: list[LLMCall] = field(default_factory=list)
    total_retrieval_nodes: int = 0
    graph_hops_used: int = 0
    retry_triggered: bool = False
    confidence_label: str = ""

    @property
    def elapsed_ms(self) -> int:
        return int((time.time() - self.start_time) * 1000)

    @property
    def total_tokens(self) -> int:
        return sum(c.prompt_tokens + c.completion_tokens for c in self.llm_calls)

    @property
    def total_cost_usd(self) -> float:
        """Rough cost estimate (adjust per model pricing)."""
        # DeepSeek Flash: ~$0.14/M input, ~$0.28/M output
        input_tokens = sum(c.prompt_tokens for c in self.llm_calls)
        output_tokens = sum(c.completion_tokens for c in self.llm_calls)
        return (input_tokens * 0.14 + output_tokens * 0.28) / 1_000_000

    def add_llm_call(self, call: LLMCall):
        self.llm_calls.append(call)

    def summary(self) -> str:
        return (
            f"req-{self.request_id} | "
            f"{len(self.llm_calls)} LLM calls | "
            f"{self.total_tokens} tokens | "
            f"${self.total_cost_usd:.4f} | "
            f"{self.elapsed_ms}ms | "
            f"confidence={self.confidence_label}"
        )

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "question": self.question[:100],
            "elapsed_ms": self.elapsed_ms,
            "llm_calls": len(self.llm_calls),
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "retry_triggered": self.retry_triggered,
            "confidence_label": self.confidence_label,
            "calls": [
                {
                    "agent": c.agent,
                    "model": c.model,
                    "tokens": c.prompt_tokens + c.completion_tokens,
                    "latency_ms": c.latency_ms,
                    "success": c.success,
                }
                for c in self.llm_calls
            ],
        }


# Context variable to hold the current request trace
_current_trace: ContextVar[Optional[RequestTrace]] = ContextVar("_current_trace", default=None)


def start_trace(question: str = "") -> RequestTrace:
    """Start a new request trace."""
    trace = RequestTrace(question=question)
    _current_trace.set(trace)
    return trace


def get_trace() -> Optional[RequestTrace]:
    """Get the current request trace."""
    return _current_trace.get()


def end_trace() -> Optional[RequestTrace]:
    """End and log the current trace."""
    trace = _current_trace.get()
    if trace:
        logger.info(trace.summary())
        _current_trace.set(None)
    return trace
