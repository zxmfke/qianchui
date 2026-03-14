"""LLM 代理接口 — 透明转发 OpenAI 兼容的 chat/completions 请求

路由: POST /api/proxy/llm/chat/completions
功能: 接收完整的 OpenAI 格式请求（含 tools / tool_choice），
      透传到配置的 LLM Provider，原样返回响应。
支持: 普通请求 + SSE 流式响应 + function calling (tools)
"""

import json
import logging
import time
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.config import get_settings
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/proxy/llm", tags=["llm-proxy"])

settings = get_settings()

ACTION_ALIASES: dict[str, str] = {
    "click": "click_element_by_index",
    "type": "input_text",
    "type_text": "input_text",
    "input": "input_text",
    "select": "select_dropdown_option",
    "scroll_down": "scroll",
    "scroll_up": "scroll",
    "navigate": "go_to_url",
    "goto": "go_to_url",
    "go_back": "go_back",
    "wait": "wait",
}

PAGE_AGENT_SYSTEM_PROMPT = (
    "You are a browser automation agent. You MUST respond ONLY with tool_calls "
    "using the AgentOutput function. Do NOT respond with plain text or explanations.\n\n"
    "Rules:\n"
    "1. Always use the AgentOutput tool to describe your next action.\n"
    "2. The 'action' field must contain EXACTLY ONE action from the available actions.\n"
    "3. Valid action types: click_element_by_index, input_text, select_dropdown_option, "
    "scroll, go_to_url, go_back, wait, done, send_keys.\n"
    "4. For click_element_by_index: use {\"click_element_by_index\": INDEX_NUMBER}.\n"
    "5. For input_text: use {\"input_text\": {\"index\": INDEX, \"text\": \"content\"}}.\n"
    "6. For scroll: use {\"scroll\": {\"x\": 0, \"y\": PIXELS}}.\n"
    "7. For done: use {\"done\": {\"text\": \"completion message\"}} when the task is finished.\n"
    "8. NEVER output multiple actions. ALWAYS output exactly one action per response.\n"
    "9. The 'current_state' field should contain a brief assessment of the page state.\n"
)


def _fix_action_aliases(body: dict) -> dict:
    """Post-process LLM response: remap common action aliases to valid names."""
    try:
        for choice in body.get("choices", []):
            msg = choice.get("message", {})
            for tc in msg.get("tool_calls", []):
                func = tc.get("function", {})
                if func.get("name") == "AgentOutput" and func.get("arguments"):
                    args = func["arguments"]
                    if isinstance(args, str):
                        parsed = json.loads(args)
                    else:
                        parsed = args

                    action = parsed.get("action")
                    if isinstance(action, dict):
                        for old_name, new_name in ACTION_ALIASES.items():
                            if old_name in action and new_name not in action:
                                action[new_name] = action.pop(old_name)
                                break

                        if isinstance(args, str):
                            func["arguments"] = json.dumps(parsed, ensure_ascii=False)
                        else:
                            func["arguments"] = parsed
    except (json.JSONDecodeError, TypeError, KeyError):
        pass
    return body


@router.post("/chat/completions")
async def proxy_chat_completions(
    request: Request,
    user: User = Depends(get_current_user),
):
    raw_body = await request.json()

    model_name = raw_body.get("model") or settings.LLM_MODEL
    raw_body["model"] = model_name

    if not raw_body.get("messages"):
        raise HTTPException(status_code=400, detail="messages is required")

    has_tools = bool(raw_body.get("tools"))
    is_stream = raw_body.get("stream", False)

    is_page_agent = has_tools and any(
        t.get("function", {}).get("name") == "AgentOutput"
        for t in raw_body.get("tools", [])
    )
    if is_page_agent:
        messages = raw_body["messages"]
        if not messages or messages[0].get("role") != "system" or "AgentOutput" not in messages[0].get("content", ""):
            raw_body["messages"] = [
                {"role": "system", "content": PAGE_AGENT_SYSTEM_PROMPT},
                *messages,
            ]
        if raw_body.get("tool_choice") is None:
            raw_body["tool_choice"] = {"type": "function", "function": {"name": "AgentOutput"}}

    msg_count = len(raw_body.get("messages", []))

    logger.info(
        "→ LLM proxy  model=%s msgs=%d tools=%s stream=%s page_agent=%s user=%s",
        model_name, msg_count, has_tools, is_stream, is_page_agent, user.id,
    )

    api_url = f"{settings.LLM_API_BASE.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
    }

    timeout = httpx.Timeout(120.0, connect=15.0)
    proxy_kwargs: dict = {"timeout": timeout}
    if settings.LLM_HTTP_PROXY:
        proxy_kwargs["proxy"] = settings.LLM_HTTP_PROXY

    if is_stream:
        async def event_stream():
            try:
                async with httpx.AsyncClient(**proxy_kwargs) as client:
                    async with client.stream(
                        "POST", api_url, json=raw_body, headers=headers
                    ) as resp:
                        if resp.status_code != 200:
                            error_body = await resp.aread()
                            logger.error("LLM stream error %d: %s", resp.status_code, error_body[:500])
                            error_chunk = {
                                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": model_name,
                                "choices": [{
                                    "index": 0,
                                    "delta": {"content": f"LLM 服务返回错误 ({resp.status_code})"},
                                    "finish_reason": "stop",
                                }],
                            }
                            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                            yield "data: [DONE]\n\n"
                            return

                        async for line in resp.aiter_lines():
                            if line.strip():
                                yield line + "\n\n"
            except Exception as e:
                logger.exception("LLM stream proxy error: %s", e)
                error_chunk = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": f"LLM 连接失败: {type(e).__name__}"},
                        "finish_reason": "stop",
                    }],
                }
                yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    start_time = time.time()
    try:
        async with httpx.AsyncClient(**proxy_kwargs) as client:
            resp = await client.post(api_url, json=raw_body, headers=headers)

        if resp.status_code != 200:
            logger.error("LLM proxy error %d: %s", resp.status_code, resp.text[:500])
            raise HTTPException(
                status_code=502,
                detail={
                    "message": f"LLM 服务返回错误 (HTTP {resp.status_code})",
                    "upstream": resp.text[:300],
                    "hint": "请检查 LLM_API_KEY、LLM_API_BASE 配置及网络连通性。",
                },
            )

        result = resp.json()
        result = _fix_action_aliases(result)

        usage = result.get("usage", {})
        content_preview = ""
        try:
            choice = result.get("choices", [{}])[0]
            msg = choice.get("message", {})
            content_preview = (msg.get("content") or "")[:120]
            if msg.get("tool_calls"):
                content_preview = f"[tool_calls: {len(msg['tool_calls'])}]"
        except (IndexError, KeyError):
            pass

        duration_ms = round((time.time() - start_time) * 1000, 1)
        logger.info(
            "← LLM proxy done  model=%s %.0fms tokens=%s reply=%r",
            model_name, duration_ms, usage.get("total_tokens", "?"), content_preview,
            extra={
                "llm_model": model_name,
                "llm_latency_ms": duration_ms,
                "total_tokens": usage.get("total_tokens", 0),
            },
        )

        _trace_proxy_call(model_name, raw_body.get("messages", []), content_preview, usage, duration_ms)

        return result

    except httpx.ConnectError as e:
        logger.error("LLM connect error: %s", e)
        raise HTTPException(
            status_code=502,
            detail={
                "message": "无法连接 LLM 服务",
                "hint": f"请确认网络能访问 {settings.LLM_API_BASE}，或在 .env 中配置 LLM_HTTP_PROXY。",
            },
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="LLM 服务响应超时")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("LLM proxy unexpected error: %s", e)
        raise HTTPException(
            status_code=502,
            detail={"message": f"LLM 代理异常: {type(e).__name__}: {e}"},
        )


def _trace_proxy_call(model: str, messages: list, content: str, usage: dict, duration_ms: float) -> None:
    try:
        from app.observability import create_trace, log_llm_call, is_enabled
        if not is_enabled():
            return
        trace = create_trace(name="llm_proxy", metadata={"model": model})
        log_llm_call(
            trace=trace, name="proxy_chat_completions", model=model,
            messages=messages, response_content=content,
            usage=usage, duration_ms=duration_ms,
        )
    except Exception:
        pass


@router.get("/models")
async def list_models(user: User = Depends(get_current_user)):
    """返回当前配置的模型信息（兼容 OpenAI /v1/models 格式）"""
    return {
        "object": "list",
        "data": [{
            "id": settings.LLM_MODEL,
            "object": "model",
            "created": int(time.time()),
            "owned_by": settings.LLM_PROVIDER,
        }],
    }
