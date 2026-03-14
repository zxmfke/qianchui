"""
千锤·营销话术AI操作系统 Skill Eval 运行器

用法:
    python evals/run_all.py                # 运行全部 Eval
    python evals/run_all.py --skill script_recommend  # 运行指定 Skill
    python evals/run_all.py --verbose       # 详细输出
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EvalCase:
    id: str
    input: dict[str, Any]
    expected: dict[str, Any]
    description: str = ""


@dataclass
class EvalResult:
    case_id: str
    passed: bool
    actual: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    latency_ms: float = 0.0


@dataclass
class SkillEvalReport:
    skill_name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    results: list[EvalResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total > 0 else 0.0


def load_cases(cases_path: Path) -> list[EvalCase]:
    with open(cases_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [EvalCase(**case) for case in raw]


def check_result(actual: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, str]:
    """检查实际结果是否满足期望条件"""
    errors = []

    for key, expect_val in expected.items():
        if key not in actual:
            errors.append(f"缺少字段: {key}")
            continue

        actual_val = actual[key]

        if isinstance(expect_val, dict) and "_check" in expect_val:
            check_type = expect_val["_check"]

            if check_type == "exists":
                if actual_val is None:
                    errors.append(f"{key}: 期望非空")

            elif check_type == "min_length":
                if len(actual_val) < expect_val["value"]:
                    errors.append(f"{key}: 长度 {len(actual_val)} < 期望最小 {expect_val['value']}")

            elif check_type == "range":
                lo, hi = expect_val["min"], expect_val["max"]
                if not (lo <= actual_val <= hi):
                    errors.append(f"{key}: 值 {actual_val} 不在 [{lo}, {hi}] 范围")

            elif check_type == "contains":
                if expect_val["value"] not in str(actual_val):
                    errors.append(f"{key}: 不包含 '{expect_val['value']}'")

        elif actual_val != expect_val:
            errors.append(f"{key}: 期望 {expect_val}, 实际 {actual_val}")

    if errors:
        return False, "; ".join(errors)
    return True, ""


async def execute_skill(skill_name: str, skill_input: dict[str, Any]) -> dict[str, Any]:
    """
    调用 Skill 并返回结果。

    实际运行时需要启动后端服务，或直接导入 Skill 模块执行。
    此处提供两种模式：
    - HTTP 模式：通过 API 调用
    - 直接模式：导入 Skill 类执行
    """
    import httpx

    base_url = "http://localhost:8000"
    skill_endpoints = {
        "script_recommend": "/api/skills/script-recommend",
        "script_diagnose": "/api/skills/script-diagnose",
        "script_train": "/api/skills/script-train",
    }

    endpoint = skill_endpoints.get(skill_name)
    if not endpoint:
        raise ValueError(f"未知 Skill: {skill_name}")

    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        # 使用 eval 专用 Token（需在环境变量中配置）
        import os
        token = os.getenv("EVAL_API_TOKEN", "eval-token")
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(endpoint, json=skill_input, headers=headers)
        response.raise_for_status()
        return response.json()


async def run_skill_eval(skill_name: str, cases_dir: Path, verbose: bool = False) -> SkillEvalReport:
    cases_path = cases_dir / "cases.json"
    if not cases_path.exists():
        print(f"  ⚠ 未找到用例文件: {cases_path}")
        return SkillEvalReport(skill_name=skill_name)

    cases = load_cases(cases_path)
    report = SkillEvalReport(skill_name=skill_name, total=len(cases))

    for case in cases:
        if verbose:
            print(f"  运行: [{case.id}] {case.description}")

        start = time.time()
        try:
            actual = await execute_skill(skill_name, case.input)
            latency_ms = (time.time() - start) * 1000
            passed, error = check_result(actual, case.expected)

            result = EvalResult(
                case_id=case.id,
                passed=passed,
                actual=actual,
                error=error,
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            result = EvalResult(
                case_id=case.id,
                passed=False,
                error=str(e),
                latency_ms=latency_ms,
            )

        if result.passed:
            report.passed += 1
            if verbose:
                print(f"    ✓ 通过 ({result.latency_ms:.0f}ms)")
        else:
            report.failed += 1
            if verbose:
                print(f"    ✗ 失败: {result.error} ({result.latency_ms:.0f}ms)")

        report.results.append(result)

    return report


def print_summary(reports: list[SkillEvalReport]) -> None:
    print("\n" + "=" * 60)
    print("千锤·营销话术AI操作系统 Skill Eval 报告")
    print("=" * 60)

    total_cases = sum(r.total for r in reports)
    total_passed = sum(r.passed for r in reports)

    for report in reports:
        status = "✓" if report.failed == 0 else "✗"
        print(f"\n  {status} {report.skill_name}")
        print(f"    通过: {report.passed}/{report.total} ({report.pass_rate:.1f}%)")
        if report.failed > 0:
            for result in report.results:
                if not result.passed:
                    print(f"    - [{result.case_id}] {result.error}")

    overall_rate = (total_passed / total_cases * 100) if total_cases > 0 else 0
    print(f"\n{'=' * 60}")
    print(f"总计: {total_passed}/{total_cases} 通过 ({overall_rate:.1f}%)")
    print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="千锤·营销话术AI操作系统 Skill Eval 运行器")
    parser.add_argument("--skill", type=str, help="指定运行某个 Skill 的 Eval")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    args = parser.parse_args()

    evals_dir = Path(__file__).parent

    skill_dirs = {
        "script_recommend": evals_dir / "script_recommend",
        "script_diagnose": evals_dir / "script_diagnose",
    }

    if args.skill:
        if args.skill not in skill_dirs:
            print(f"未知 Skill: {args.skill}")
            print(f"可用: {', '.join(skill_dirs.keys())}")
            sys.exit(1)
        skill_dirs = {args.skill: skill_dirs[args.skill]}

    reports = []
    for skill_name, skill_dir in skill_dirs.items():
        print(f"\n▶ 评估 Skill: {skill_name}")
        report = await run_skill_eval(skill_name, skill_dir, verbose=args.verbose)
        reports.append(report)

    print_summary(reports)

    total_failed = sum(r.failed for r in reports)
    sys.exit(1 if total_failed > 0 else 0)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
