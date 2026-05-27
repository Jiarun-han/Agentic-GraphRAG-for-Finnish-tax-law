"""
Centralized configuration for the Taxxa GraphRAG system.
Single source of truth for all settings, paths, and environment variables.
"""
import os
import logging
from pathlib import Path
from dataclasses import dataclass, field

# ── Load .env once ────────────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).parent
_env_file = _BASE_DIR / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


# ── Logging setup ─────────────────────────────────────────────────────────────

def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure structured logging for the application."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)-12s | %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("taxxa")


logger = setup_logging(os.getenv("LOG_LEVEL", "INFO"))


# ── Configuration dataclass ───────────────────────────────────────────────────

@dataclass(frozen=True)
class Config:
    """Immutable application configuration."""

    # Paths
    base_dir: Path = _BASE_DIR
    data_dir: Path = field(default_factory=lambda: _BASE_DIR / "data")
    nodes_file: Path = field(default_factory=lambda: _BASE_DIR / "data/parsed_nodes.jsonl")
    graph_file: Path = field(default_factory=lambda: _BASE_DIR / "data/graph.pkl")
    embed_file: Path = field(default_factory=lambda: _BASE_DIR / "data/embeddings.npz")
    index_file: Path = field(default_factory=lambda: _BASE_DIR / "data/node_ids.json")
    corpus_root: Path = field(default_factory=lambda: _BASE_DIR / "data/raw/finland_kb")

    # LLM
    llm_api_key: str = field(default_factory=lambda: os.getenv("FEATHERLESS_API_KEY", ""))
    llm_base_url: str = field(default_factory=lambda: os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1"))
    llm_model: str = field(default_factory=lambda: os.getenv("FEATHERLESS_MODEL", "deepseek-ai/DeepSeek-V4-Flash"))
    llm_max_tokens: int = 4096
    llm_timeout: int = 120
    llm_max_retries: int = 3

    # Embeddings
    embed_model: str = "intfloat/multilingual-e5-small"
    embed_batch_size: int = 256

    # Retrieval
    retrieval_top_k: int = 10
    retrieval_graph_hops: int = 2
    retrieval_max_results: int = 25
    keyword_cap_per_term: int = 100

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_max_question_length: int = 2000
    cors_origins: list[str] = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(","))

    def validate(self) -> list[str]:
        """Return list of configuration errors."""
        errors = []
        if not self.llm_api_key:
            errors.append("FEATHERLESS_API_KEY not set in .env")
        if not self.nodes_file.exists():
            errors.append(f"Nodes file not found: {self.nodes_file}")
        return errors


# Singleton config instance
config = Config()
