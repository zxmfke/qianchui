"""LLM observability via Langfuse.

Provides a thin wrapper around the Langfuse SDK.
Enabled only when LANGFUSE_ENABLED=true and keys are configured.
All tracing is safe to call even when disabled (no-ops).
"""

import logging
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

_langfuse_client = None
_enabled = False


def init_langfuse() -> None:
    """Initialize Langfuse client. Call once at startup."""
    global _langfuse_client, _enabled

    from app.config import get_settings
    settings = get_settings()

    if not settings.LANGFUSE_ENABLED:
        logger.info("Langfuse disabled (LANGFUSE_ENABLED=false)")
        return
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        logger.warning("Langfuse enabled but keys not set, skipping")
        return

    try:
        from langfuse import Langfuse
        _langfuse_client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
        _enabled = True
        logger.info("Langfuse initialized → %s", settings.LANGFUSE_HOST)
    except Exception:
        logger.exception("Failed to initialize Langfuse")


def get_langfuse():
    """Get the Langfuse client instance (may be None)."""
    return _langfuse_client


def is_enabled() -> bool:
    return _enabled


def flush() -> None:
    """Flush pending Langfuse events. Call on shutdown."""
    if _langfuse_client:
        try:
            _langfuse_client.flush()
        except Exception:
            pass


def create_trace(
    name: str,
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict | None = None,
    tags: list[str] | None = None,
):
    """Create a Langfuse trace. Returns trace object or a no-op stub."""
    if not _enabled or not _langfuse_client:
        return _NoOpTrace()

    try:
        return _langfuse_client.trace(
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
            tags=tags or [],
        )
    except Exception:
        logger.debug("Failed to create Langfuse trace", exc_info=True)
        return _NoOpTrace()


def log_llm_call(
    trace,
    name: str,
    model: str,
    messages: list[dict],
    response_content: str,
    usage: dict | None = None,
    duration_ms: float = 0,
    metadata: dict | None = None,
    level: str = "DEFAULT",
) -> None:
    """Log an LLM generation event to Langfuse."""
    if not _enabled or isinstance(trace, _NoOpTrace):
        return

    try:
        trace.generation(
            name=name,
            model=model,
            input=messages,
            output=response_content,
            usage={
                "input": usage.get("prompt_tokens", 0) if usage else 0,
                "output": usage.get("completion_tokens", 0) if usage else 0,
                "total": usage.get("total_tokens", 0) if usage else 0,
            },
            metadata=metadata or {},
            level=level,
        )
    except Exception:
        logger.debug("Failed to log LLM generation to Langfuse", exc_info=True)


class _NoOpTrace:
    """Stub trace that silently ignores all calls when Langfuse is disabled."""

    def generation(self, **kwargs):
        return self

    def span(self, **kwargs):
        return self

    def event(self, **kwargs):
        return self

    def score(self, **kwargs):
        return self

    def update(self, **kwargs):
        return self

    def end(self, **kwargs):
        pass
