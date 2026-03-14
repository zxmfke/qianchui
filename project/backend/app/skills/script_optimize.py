"""话术优化策略生成 Skill [v1.1 新增]

根据3层7维诊断结果和根因归类，生成可执行的话术优化策略方案。
"""

import json
import logging

from app.providers.base import ModelProvider
from app.skills.base import Skill

logger = logging.getLogger(__name__)

OPTIMIZE_SYSTEM_PROMPT = """你是千锤·营销话术AI操作系统的话术优化策略专家。

根据诊断结果，生成可执行的话术优化方案。每个方案必须包含「当前话术」和「建议话术」的对比。

## 根因类型与优化方向

| 根因类型 | 优化方向 |
|---------|---------|
| 配置问题(config) | 调整话术触发配置、节奏、时机 |
| 话术问题(script) | 改写话术内容、增加价值交换、共情 |
| 流量问题(traffic) | 标记为流量问题，不做话术调整 |
| 产品问题(product) | 标记为产品反馈 |

## 优化原则

1. **结果导向**：优化方案应以提升用户回复率和留联率为目标
2. **先给价值再要信息**：留联前必须有价值输出
3. **具体可执行**：给出完整的话术文本，不要泛泛建议
4. **渐进式改进**：每次只改1-3个点，避免大改

## 输出格式

输出JSON：
{{
  "strategies": [
    {{
      "priority": "P0/P1/P2",
      "problem": "问题描述",
      "root_cause_type": "config/script/traffic/product",
      "solution": "解决方案说明",
      "current_script": "当前话术原文",
      "suggested_script": "建议修改后的话术",
      "expected_impact": "预期效果",
      "risk_level": "low/medium/high"
    }}
  ]
}}"""


class ScriptOptimizeSkill(Skill):
    """根据诊断结果生成话术优化策略。"""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    @property
    def name(self) -> str:
        return "script-optimize"

    @property
    def description(self) -> str:
        return "根据话术诊断结果生成可执行的优化策略方案，包含当前话术vs建议话术的对比"

    @property
    def trigger_phrases(self) -> list[str]:
        return ["优化话术", "生成优化方案", "话术改进", "怎么优化", "帮我优化"]

    async def execute(self, user_input: str, context: dict) -> dict:
        diagnosis_result = context.get("diagnosis_result", {})
        enterprise_memory = context.get("enterprise_memory", "")
        industry = context.get("industry", "oral")
        conversation_text = context.get("conversation_text", "")

        user_prompt = f"""【诊断结果】
前置分类：{json.dumps(diagnosis_result.get('classification', {}), ensure_ascii=False)}
3层7维评分：{json.dumps(diagnosis_result.get('score_result', {}), ensure_ascii=False)}
根因列表：{json.dumps(diagnosis_result.get('root_causes', []), ensure_ascii=False)}

【对话原文】
{conversation_text}

【企业背景】
行业：{industry}
企业记忆：{enterprise_memory}

【用户需求】
{user_input}

请针对诊断发现的问题，生成优化策略。"""

        messages = [
            {"role": "system", "content": OPTIMIZE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            result = await self.provider.chat_completion(
                messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(result["content"])
            strategies = parsed.get("strategies", [])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Optimize strategy generation failed: %s", e)
            strategies = []

        cards = [
            {
                "type": "optimize-strategy",
                "data": {
                    "priority": s.get("priority", "P1"),
                    "problem": s.get("problem", ""),
                    "root_cause_type": s.get("root_cause_type", "script"),
                    "current_script": s.get("current_script", ""),
                    "suggested_script": s.get("suggested_script", ""),
                    "expected_impact": s.get("expected_impact", ""),
                    "risk_level": s.get("risk_level", "low"),
                },
            }
            for s in strategies
        ]

        summary_parts = [f"基于诊断结果，为您生成了 {len(strategies)} 条优化策略："]
        for i, s in enumerate(strategies, 1):
            summary_parts.append(
                f"\n{i}. [{s.get('priority', 'P1')}] {s.get('problem', '')} → {s.get('solution', '')}"
            )

        return {
            "text": "\n".join(summary_parts),
            "cards": cards,
            "suggested_actions": [
                {"label": "采纳全部方案", "action": "adopt_all_strategies"},
                {"label": "创建AB测试验证", "action": "create_ab_test"},
                {"label": "查看详细诊断报告", "action": "view_diagnosis"},
            ],
        }
