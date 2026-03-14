"""飞轮感知 Skill [v1.4 重构]

从对话诊断数据中提取痛点标签，与企业记忆·痛点库匹配：
- 匹配到的痛点 → 更新 pain_points 表的 mention_count 和趋势字段
- 未匹配的高频词 → 提示为"疑似新痛点"

不再使用独立的 pain_point_trends 表，所有趋势数据直接写入 pain_points 表。
"""

import json
import logging

from app.providers.base import ModelProvider
from app.skills.base import Skill

logger = logging.getLogger(__name__)

FLYWHEEL_SENSE_PROMPT = """你是千锤·营销话术AI操作系统的痛点趋势感知引擎。

你的任务：分析对话诊断数据，识别客户痛点的变化趋势。

具体步骤：
1. 统计每个已知痛点在本期对话中的提及次数
2. 与上期数据对比，计算变化率
3. 标记趋势标签（rising/falling/stable/new）
4. 发现未收录的高频关键词，提示为疑似新痛点
5. 判断是否需要触发策略联动（变化率>20%或出现新痛点）

输出JSON格式：
{{
  "pain_point_updates": [
    {{
      "pain_point_name": "面部松弛",
      "mention_count": 342,
      "change_rate": 0.82,
      "trend_label": "rising",
      "evidence_keywords": ["脸松了", "法令纹"]
    }}
  ],
  "unrecognized_keywords": [
    {{
      "keyword": "产后修复",
      "mention_count": 28,
      "suggested_pain_point_name": "产后修复需求"
    }}
  ],
  "should_trigger_cascade": true,
  "trigger_reasons": ["面部松弛提及率上升82%", "发现新痛点:产后修复"],
  "summary": "本周期核心变化总结"
}}"""


class FlywheelSenseSkill(Skill):
    """分析对话数据，更新痛点库趋势字段，发现新兴痛点。"""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    @property
    def name(self) -> str:
        return "flywheel-sense"

    @property
    def description(self) -> str:
        return "从对话诊断数据中感知痛点趋势变化，更新企业记忆·痛点库的趋势字段"

    @property
    def trigger_phrases(self) -> list[str]:
        return ["飞轮感知", "痛点趋势", "痛点变化", "趋势分析", "感知扫描", "趋势"]

    async def execute(self, user_input: str, context: dict) -> dict:
        diagnosis_data = context.get("diagnosis_data", {})
        pain_points_current = context.get("pain_points_current", [])
        enterprise_memory = context.get("enterprise_memory", "")
        time_window = context.get("time_window", "30天")

        user_prompt = f"""【分析时间窗口】{time_window}
【诊断数据汇总】
{json.dumps(diagnosis_data, ensure_ascii=False, indent=2)}

【当前痛点库】
{json.dumps(pain_points_current, ensure_ascii=False, indent=2)}

【企业背景】
{enterprise_memory}

【用户需求】
{user_input}

请分析痛点趋势变化，输出JSON。"""

        messages = [
            {"role": "system", "content": FLYWHEEL_SENSE_PROMPT},
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
            logger.error("Flywheel sense failed: %s", e)
            parsed = {"pain_point_updates": [], "should_trigger_cascade": False, "summary": "分析失败"}

        cards = [
            {
                "type": "flywheel-trend-card",
                "data": {
                    "updates": parsed.get("pain_point_updates", []),
                    "new_keywords": parsed.get("unrecognized_keywords", []),
                    "should_cascade": parsed.get("should_trigger_cascade", False),
                },
            }
        ]

        actions = [{"label": "查看痛点库详情", "action": "view_pain_points"}]
        if parsed.get("should_trigger_cascade"):
            actions.insert(0, {"label": "触发策略联动", "action": "trigger_cascade"})
        if parsed.get("unrecognized_keywords"):
            actions.append({"label": "确认新痛点", "action": "confirm_new_pain_points"})

        return {
            "text": parsed.get("summary", "痛点趋势分析完成"),
            "cards": cards,
            "suggested_actions": actions,
        }
