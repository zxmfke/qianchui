import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.providers.base import ModelProvider

logger = logging.getLogger("app.llm")


class OpenAIProvider(ModelProvider):
    """OpenAI API compatible provider — works with any OpenAI-compatible backend."""

    def __init__(self, api_key: str, api_base: str, model: str, http_proxy: str = ""):
        super().__init__(api_key, api_base, model)
        kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "base_url": self.api_base,
            "timeout": httpx.Timeout(120.0, connect=10.0),
            "max_retries": 2,
        }
        if http_proxy:
            kwargs["http_client"] = httpx.AsyncClient(
                proxy=http_proxy,
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        self.client = AsyncOpenAI(**kwargs)

    async def chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        response_format: dict | None = None,
    ) -> dict:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        msg_count = len(messages)
        last_user = next(
            (m["content"][:100] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )

        logger.info(
            "→ LLM call  model=%s msgs=%d temp=%.1f prompt=%s",
            self.model, msg_count, temperature,
            repr(last_user),
        )

        t0 = time.perf_counter()
        try:
            response = await self.client.chat.completions.create(**kwargs)
        except Exception as e:
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            logger.error(
                "✗ LLM error model=%s %.0fms %s: %s",
                self.model, elapsed, type(e).__name__, e,
                extra={"llm_provider": self.api_base, "llm_model": self.model, "llm_latency_ms": elapsed},
            )
            raise

        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        choice = response.choices[0]
        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }

        content = choice.message.content or ""
        content_preview = content[:150].replace("\n", " ")

        logger.info(
            "← LLM done model=%s %.0fms tokens=%d/%d/%d finish=%s content=%s",
            self.model, elapsed,
            usage["prompt_tokens"], usage["completion_tokens"], usage["total_tokens"],
            choice.finish_reason,
            repr(content_preview),
            extra={
                "llm_provider": self.api_base,
                "llm_model": self.model,
                "llm_latency_ms": elapsed,
                "prompt_tokens": usage["prompt_tokens"],
                "completion_tokens": usage["completion_tokens"],
                "total_tokens": usage["total_tokens"],
            },
        )

        self._trace_generation(
            name="chat_completion",
            messages=messages,
            response_content=content,
            usage=usage,
            duration_ms=elapsed,
        )

        return {
            "content": content,
            "role": choice.message.role,
            "finish_reason": choice.finish_reason,
            "usage": usage,
        }

    async def chat_completion_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        logger.info(
            "→ LLM stream model=%s msgs=%d temp=%.1f",
            self.model, len(messages), temperature,
        )

        t0 = time.perf_counter()
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
        except Exception as e:
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            logger.error(
                "✗ LLM stream error model=%s %.0fms %s: %s",
                self.model, elapsed, type(e).__name__, e,
            )
            raise

        chunk_count = 0
        full_text = []
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_text.append(text)
                chunk_count += 1
                yield text

        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        total_text = "".join(full_text)
        logger.info(
            "← LLM stream done model=%s %.0fms chunks=%d chars=%d",
            self.model, elapsed, chunk_count, len(total_text),
            extra={"llm_model": self.model, "llm_latency_ms": elapsed},
        )

        self._trace_generation(
            name="chat_completion_stream",
            messages=messages,
            response_content=total_text,
            usage=None,
            duration_ms=elapsed,
        )

    def _trace_generation(
        self,
        name: str,
        messages: list[dict],
        response_content: str,
        usage: dict | None,
        duration_ms: float,
    ) -> None:
        """Send generation event to Langfuse (if enabled)."""
        try:
            from app.observability import create_trace, log_llm_call, is_enabled
            if not is_enabled():
                return
            trace = create_trace(
                name=f"provider.{name}",
                metadata={"model": self.model, "api_base": self.api_base},
            )
            log_llm_call(
                trace=trace,
                name=name,
                model=self.model,
                messages=messages,
                response_content=response_content,
                usage=usage,
                duration_ms=duration_ms,
            )
        except Exception:
            pass
