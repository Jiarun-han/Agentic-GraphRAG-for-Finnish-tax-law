"""
Centralized LLM client with retry logic, timeout, and connection pooling.
All agents use this instead of creating their own OpenAI clients.
"""
import time
import json
import re
from typing import Optional

from config import config, logger

# Singleton OpenAI client (connection pooling)
_client = None


def _get_client():
    """Get or create the singleton OpenAI client."""
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            timeout=config.llm_timeout,
        )
    return _client


def llm(system: str, user: str, model: Optional[str] = None, max_tokens: int = None) -> str:
    """
    Single LLM call with retry logic and error handling.

    Args:
        system: System prompt
        user: User message
        model: Override model (uses config default if None)
        max_tokens: Override max tokens

    Returns:
        LLM response text (stripped)

    Raises:
        RuntimeError: After all retries exhausted
    """
    model = model or config.llm_model
    max_tokens = max_tokens or config.llm_max_tokens
    client = _get_client()

    last_error = None
    for attempt in range(config.llm_max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            content = resp.choices[0].message.content
            return content.strip() if content else ""

        except Exception as e:
            last_error = e
            error_msg = str(e)

            # Rate limit: wait and retry
            if "429" in error_msg or "rate" in error_msg.lower():
                wait = 2 ** attempt
                logger.warning(f"Rate limited (attempt {attempt+1}/{config.llm_max_retries}), waiting {wait}s")
                time.sleep(wait)
                continue

            # Concurrency limit: wait longer
            if "concurrency" in error_msg.lower():
                wait = 5 * (attempt + 1)
                logger.warning(f"Concurrency limit (attempt {attempt+1}), waiting {wait}s")
                time.sleep(wait)
                continue

            # Other transient errors: retry once
            if attempt < config.llm_max_retries - 1:
                logger.warning(f"LLM error (attempt {attempt+1}): {error_msg[:100]}")
                time.sleep(1)
                continue

            # Final attempt failed
            raise RuntimeError(f"LLM call failed after {config.llm_max_retries} attempts: {error_msg[:200]}") from e

    raise RuntimeError(f"LLM call failed: {last_error}")


def parse_json_response(raw: str) -> dict | list | None:
    """
    Robustly parse JSON from LLM response.
    Handles: markdown code blocks, missing brackets, partial JSON.
    """
    # Try direct parse
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass

    # Strip markdown code blocks
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        if len(parts) >= 2:
            cleaned = parts[1].strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

    # Try again
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try to find JSON object/array in text
    for pattern in [r'\{[^{}]*\}', r'\[.*\]']:
        m = re.search(pattern, raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except (json.JSONDecodeError, TypeError):
                continue

    return None
