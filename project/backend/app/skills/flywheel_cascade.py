"""飞轮联动 Skill [v1.4 重构]

根据痛点库趋势字段的变化，生成四层策略联动方案：
- 痛点层：确认/补充痛点库
- 产品层：调整产品优先级，标记覆盖空白
- 服务层：调整服务场景，标记场景缺口
- 话术层：新增/淘汰/调整话术
"""

import json
import logging

from app.providers.base import ModelProvider
from app.skills.base import Skill

logger = logging.getLogger(__name__)

CASCADE_PROMPT = """你是千锤·营销话术AI操作系统的策略联动引擎。

当客户痛点发生变化时，生成完整的策略级联更新方案：
1. 产品策略适配：推荐产品/项目组合调整
2. 服务策略适配：接待流程和场景调整
3. 话术策略适配：新增/调整/下线话术

企业背景：
{enterprise_memory}

输出JSON格式：
{{
  "cascade_plans": [
    {{
      "pain_point": "痛点名称",
      "trend": "上升/下降/新增",
      "product_strategy": {{
        "adjustments": ["调整1"],
        "new_combinations": ["组合1"],
        "priority_change": "P2→P0"
      }},
      "service_strategy": {{
        "adjustments": ["调整1"],
        "new_scenarios": ["场景1"],
        "training_needs": ["培训1"]
      }},
      "script_strategy": {{
        "new_scripts": [{{"title": "话术标题", "psychology": "...", "strategy": "...", "script": "..."}}],
        "adjust_scripts": ["调整描述"],
        "retire_scripts": []
      }}
    }}
  ],
  "implementation_timeline": "建议N天内完成",
  "estimated_impact": "预计影响描述"
}}"""


class FlywheelCascadeSkill(Skill):
    """根据痛点变化生成策略级联更新方案。"""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    @property
    def name(self) -> str:
        return "flywheel-cascade"

    @property
    def description(self) -> str:
        return "根据痛点趋势变化自动生成产品→服务→话术的三层策略级联更新方案"

    @property
    def trigger_phrases(self) -> list[str]:
        return ["策略联动", "飞轮联动", "联动", "级联更新", "策略更新"]

    async def execute(self, user_input: str, context: dict) -> dict:
        pain_point_signal = context.get("pain_point_signal", {})
        enterprise_memory = context.get("enterprise_memory", "")

        user_prompt = f"""【痛点变化信号】
{json.dumps(pain_point_signal, ensure_ascii=False, indent=2)}

【用户需求】
{user_input}

请生成策略级联更新方案。"""

        messages = [
            {"role": "system", "content": CASCADE_PROMPT.format(enterprise_memory=enterprise_memory)},
            {"role": "user", "content": user_prompt},
        ]

        try:
            result = await self.provider.chat_completion(
                messages,
                temperature=0.5,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(result["content"])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Flywheel cascade failed: %s", e)
            parsed = {"cascade_plans": []}

        plans = parsed.get("cascade_plans", [])
        cards = [
            {
                "type": "flywheel-cascade-card",
                "data": {
                    "pain_point": p.get("pain_point", ""),
                    "trend": p.get("trend", ""),
                    "product_strategy": p.get("product_strategy", {}),
                    "service_strategy": p.get("service_strategy", {}),
                    "script_strategy": p.get("script_strategy", {}),
                },
            }
            for p in plans
        ]

        summary = f"为 {len(plans)} 个痛点变化生成了策略联动方案"
        if parsed.get("implementation_timeline"):
            summary += f"，{parsed['implementation_timeline']}"

        return {
            "text": summary,
            "cards": cards,
            "suggested_actions": [
                {"label": "采纳全部方案", "action": "adopt_all_cascades"},
                {"label": "逐条审核", "action": "review_cascades"},
                {"label": "查看影响范围", "action": "view_impact"},
            ],
        }
