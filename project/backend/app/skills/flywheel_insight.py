"""飞轮洞察 Skill [v1.4 重构]

从 pain_points/products/services/scripts 的飞轮字段
以及 flywheel_events 审计日志中聚合数据，生成飞轮运行报告。
"""

import json
import logging

from app.providers.base import ModelProvider
from app.skills.base import Skill

logger = logging.getLogger(__name__)

INSIGHT_PROMPT = """你是千锤·营销话术AI操作系统的飞轮运营分析师。

基于飞轮运行数据，生成洞察报告，覆盖以下维度：
1. 飞轮转速：从痛点发现到话术落地的平均时间
2. 飞轮健康度：四齿轮（感知→产品→服务→话术）评分
3. 商业价值量化：飞轮转动带来的留联率、转化率变化
4. 优化建议：瓶颈环节和加速建议

输出JSON格式：
{{
  "flywheel_speed": {{
    "avg_cycle_days": 5.2,
    "trend": "加速中/减速/稳定",
    "target": 7,
    "status": "达标/未达标"
  }},
  "gear_health": {{
    "sense": {{"score": 85, "issue": null}},
    "product_adapt": {{"score": 72, "issue": "产品团队响应偏慢"}},
    "service_adapt": {{"score": 80, "issue": null}},
    "script_adapt": {{"score": 90, "issue": null}}
  }},
  "business_impact": {{
    "contact_rate_change": "+3.2%",
    "new_pain_points_captured": 3,
    "scripts_auto_generated": 12,
    "scripts_adopted": 8
  }},
  "bottleneck": "瓶颈描述",
  "recommendations": ["建议1", "建议2"],
  "summary": "飞轮运行总结"
}}"""


class FlywheelInsightSkill(Skill):
    """分析飞轮运行历史，生成健康度报告。"""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    @property
    def name(self) -> str:
        return "flywheel-insight"

    @property
    def description(self) -> str:
        return "分析飞轮运行历史数据，生成健康度分析、商业价值量化和优化建议报告"

    @property
    def trigger_phrases(self) -> list[str]:
        return ["飞轮洞察", "飞轮报告", "飞轮健康", "飞轮状态", "飞轮"]

    async def execute(self, user_input: str, context: dict) -> dict:
        flywheel_data = context.get("flywheel_data", {})
        enterprise_memory = context.get("enterprise_memory", "")

        user_prompt = f"""【飞轮运行数据】
{json.dumps(flywheel_data, ensure_ascii=False, indent=2)}

【企业背景】
{enterprise_memory}

【用户需求】
{user_input}

请生成飞轮健康度分析报告。"""

        messages = [
            {"role": "system", "content": INSIGHT_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            result = await self.provider.chat_completion(
                messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(result["content"])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Flywheel insight failed: %s", e)
            parsed = {"summary": "飞轮洞察分析失败"}

        cards = [
            {
                "type": "flywheel-insight-card",
                "data": {
                    "speed": parsed.get("flywheel_speed", {}),
                    "gear_health": parsed.get("gear_health", {}),
                    "business_impact": parsed.get("business_impact", {}),
                    "bottleneck": parsed.get("bottleneck"),
                    "recommendations": parsed.get("recommendations", []),
                },
            }
        ]

        return {
            "text": parsed.get("summary", "飞轮洞察分析完成"),
            "cards": cards,
            "suggested_actions": [
                {"label": "查看详细报告", "action": "view_flywheel_report"},
                {"label": "导出PDF报告", "action": "export_flywheel_report"},
                {"label": "优化瓶颈环节", "action": "optimize_bottleneck"},
            ],
        }
