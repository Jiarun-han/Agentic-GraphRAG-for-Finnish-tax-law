"""
User feedback collection and storage.
Enables continuous improvement through user corrections.
"""
import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

from config import config, logger

FEEDBACK_DIR = config.data_dir / "feedback"
FEEDBACK_FILE = FEEDBACK_DIR / "feedback.jsonl"


@dataclass
class FeedbackEntry:
    """A single piece of user feedback."""
    request_id: str
    rating: str  # "correct" | "partially_correct" | "wrong"
    correction: str = ""
    missing_info: str = ""
    timestamp: float = 0.0
    question: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


def save_feedback(entry: FeedbackEntry) -> None:
    """Append feedback to the JSONL log."""
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    logger.info(f"Feedback saved: req-{entry.request_id} → {entry.rating}")


def get_feedback_stats() -> dict:
    """Return aggregate feedback statistics."""
    if not FEEDBACK_FILE.exists():
        return {"total": 0, "correct": 0, "partially_correct": 0, "wrong": 0, "accuracy": 0.0}

    total = correct = partial = wrong = 0
    with FEEDBACK_FILE.open(encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            total += 1
            r = entry.get("rating", "")
            if r == "correct":
                correct += 1
            elif r == "partially_correct":
                partial += 1
            elif r == "wrong":
                wrong += 1

    accuracy = (correct + partial * 0.5) / total if total > 0 else 0.0
    return {
        "total": total,
        "correct": correct,
        "partially_correct": partial,
        "wrong": wrong,
        "accuracy": round(accuracy * 100, 1),
    }


def get_recent_feedback(limit: int = 20) -> list[dict]:
    """Return the most recent feedback entries."""
    if not FEEDBACK_FILE.exists():
        return []

    entries = []
    with FEEDBACK_FILE.open(encoding="utf-8") as f:
        for line in f:
            entries.append(json.loads(line))

    return entries[-limit:]
