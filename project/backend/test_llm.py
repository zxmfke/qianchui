"""LLM Provider self-test — verifies the configured provider works end-to-end.

Usage:
  python test_llm.py                   # Test current .env config
  python test_llm.py --provider deepseek --api-key sk-xxx --model deepseek-chat
  python test_llm.py --check-network   # Only check network connectivity
"""
import argparse
import asyncio
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")


async def check_network():
    """Check connectivity to all known LLM API endpoints."""
    import httpx

    endpoints = {
        "openai": "https://api.openai.com/v1/models",
        "moonshot": "https://api.moonshot.ai/v1/models",
        "deepseek": "https://api.deepseek.com/v1/models",
        "zhipu": "https://open.bigmodel.cn/api/paas/v4/models",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
        "siliconflow": "https://api.siliconflow.cn/v1/models",
        "groq": "https://api.groq.com/openai/v1/models",
        "together": "https://api.together.xyz/v1/models",
    }

    print("=" * 60)
    print("  网络连通性检查")
    print("=" * 60)

    reachable = []
    async with httpx.AsyncClient(timeout=8) as c:
        for name, url in endpoints.items():
            try:
                t0 = time.time()
                r = await c.get(url)
                ms = int((time.time() - t0) * 1000)
                status = f"HTTP {r.status_code}"
                reachable.append(name)
                print(f"  OK    {name:15s} {status} ({ms}ms)")
            except Exception as e:
                print(f"  FAIL  {name:15s} {type(e).__name__}")

    print("-" * 60)
    if reachable:
        print(f"  可用: {', '.join(reachable)}")
        print(f"  建议将 .env 的 LLM_PROVIDER 设为: {reachable[0]}")
    else:
        print("  所有 API 均不可达。请检查网络/代理/DNS 设置。")
        print("  提示: 系统已内置 fallback，所有功能仍可使用（无AI能力）。")
    print()
    return reachable


async def test_provider(provider_type: str, api_key: str, api_base: str, model: str):
    from app.providers.factory import ModelProviderFactory

    print("=" * 60)
    print("  千锤 · LLM Provider 自测")
    print("=" * 60)
    print(f"  Provider : {provider_type}")
    print(f"  Model    : {model}")
    print(f"  API Base : {api_base}")
    print(f"  API Key  : {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '****'}")
    print("-" * 60)

    provider = ModelProviderFactory.create_provider(
        provider_type=provider_type,
        api_key=api_key,
        api_base=api_base,
        model=model,
    )

    test1_ok = test2_ok = test3_ok = None

    # Test 1: non-streaming
    print("\n[Test 1] chat_completion (non-streaming)...")
    t0 = time.time()
    try:
        result = await provider.chat_completion(
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Reply in Chinese. Be brief."},
                {"role": "user", "content": "用一句话介绍你自己"},
            ],
            temperature=0.7,
        )
        elapsed = time.time() - t0
        print(f"  OK ({elapsed:.1f}s)")
        print(f"  Content: {result['content'][:150]}")
        print(f"  Tokens : {result['usage']}")
        test1_ok = True
    except Exception as e:
        print(f"  FAIL: {e}")
        test1_ok = False

    # Test 2: streaming
    print("\n[Test 2] chat_completion_stream (streaming)...")
    t0 = time.time()
    try:
        chunks = []
        async for chunk in provider.chat_completion_stream(
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Reply in Chinese. Be brief."},
                {"role": "user", "content": "处理价格异议的两个要点？"},
            ],
            temperature=0.7,
        ):
            chunks.append(chunk)
            print(chunk, end="", flush=True)
        elapsed = time.time() - t0
        print(f"\n  OK ({elapsed:.1f}s, {len(chunks)} chunks)")
        test2_ok = True
    except Exception as e:
        print(f"\n  FAIL: {e}")
        test2_ok = False

    # Test 3: JSON response format
    print("\n[Test 3] response_format=json (optional)...")
    try:
        result = await provider.chat_completion(
            messages=[
                {"role": "system", "content": "Output valid JSON only."},
                {"role": "user", "content": '输出: {"status": "ok", "provider": "' + provider_type + '"}'},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        print(f"  OK: {result['content'][:200]}")
        test3_ok = True
    except Exception as e:
        print(f"  SKIP: {type(e).__name__}")
        test3_ok = None

    # Summary
    print("\n" + "=" * 60)
    for name, ok in [("Non-streaming", test1_ok), ("Streaming", test2_ok), ("JSON format", test3_ok)]:
        s = "PASS" if ok is True else "FAIL" if ok is False else "SKIP"
        print(f"  {s:4s}  {name}")
    print("=" * 60)

    if test1_ok and test2_ok:
        print("  All critical tests passed!")
    elif test1_ok is False and test2_ok is False:
        print("  连接失败。请检查:")
        print("  1. 网络是否能访问 API (python test_llm.py --check-network)")
        print("  2. API Key 是否正确")
        print(f"  3. 可用 providers: {ModelProviderFactory.list_providers()}")
    print()


def main():
    parser = argparse.ArgumentParser(description="LLM Provider self-test")
    parser.add_argument("--provider", help="Override LLM_PROVIDER")
    parser.add_argument("--api-key", help="Override LLM_API_KEY")
    parser.add_argument("--api-base", help="Override LLM_API_BASE")
    parser.add_argument("--model", help="Override LLM_MODEL")
    parser.add_argument("--check-network", action="store_true", help="Only check network connectivity")
    args = parser.parse_args()

    if args.check_network:
        asyncio.run(check_network())
        return

    from app.config import get_settings
    from app.providers.factory import ModelProviderFactory

    settings = get_settings()
    provider_type = args.provider or settings.LLM_PROVIDER
    api_key = args.api_key or settings.LLM_API_KEY

    if args.api_base:
        api_base = args.api_base
    elif args.provider and args.provider != settings.LLM_PROVIDER:
        defaults = ModelProviderFactory.get_defaults(args.provider)
        api_base = defaults.get("api_base", settings.LLM_API_BASE)
    else:
        api_base = settings.LLM_API_BASE

    if args.model:
        model = args.model
    elif args.provider and args.provider != settings.LLM_PROVIDER:
        defaults = ModelProviderFactory.get_defaults(args.provider)
        model = defaults.get("model", settings.LLM_MODEL)
    else:
        model = settings.LLM_MODEL

    asyncio.run(test_provider(provider_type, api_key, api_base, model))


if __name__ == "__main__":
    main()
