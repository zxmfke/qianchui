import json
import logging

from app.providers.base import ModelProvider
from app.skills.base import Skill

logger = logging.getLogger(__name__)

DATA_INSIGHT_PROMPT = """你是千锤·营销话术AI操作系统的数据分析专家。

你的职责是根据话术使用数据，生成有洞察力的数据分析和可视化建议。

## 可用数据
{data_summary}

## 分析要求
根据用户的查询需求，从以下维度进行分析：
1. 话术复用率趋势
2. 高转化话术特征
3. 团队使用情况对比
4. 培训效果与实战关联
5. 客户类型分布

## 输出要求
请以JSON格式输出：
{{
  "text": "数据洞察的文字说明",
  "insights": [
    {{
      "title": "洞察标题",
      "description": "洞察描述",
      "metric_value": "关键指标值",
      "trend": "up/down/stable",
      "recommendation": "基于数据的建议"
    }}
  ],
  "charts": [
    {{
      "chart_type": "line/bar/pie/ranking",
      "title": "图表标题",
      "data": [
        {{"label": "标签", "value": 100}}
      ]
    }}
  ],
  "suggested_actions": [
    {{"label": "操作标签", "action": "操作类型"}}
  ]
}}"""


class DataInsightSkill(Skill):
    """查询话术使用数据，生成数据洞察和图表。"""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    @property
    def name(self) -> str:
        return "data-insight"

    @property
    def description(self) -> str:
        return "查询话术使用数据，生成数据洞察和图表卡片"

    @property
    def trigger_phrases(self) -> list[str]:
        return ["看数据", "数据分析", "复用率", "转化率", "看板", "统计", "趋势"]

    async def execute(self, user_input: str, context: dict) -> dict:
        data_summary = context.get("data_summary", {})
        if isinstance(data_summary, dict):
            data_summary = json.dumps(data_summary, ensure_ascii=False, indent=2)

        if not data_summary or data_summary == "{}":
            data_summary = self._generate_mock_summary()

        system_prompt = DATA_INSIGHT_PROMPT.format(data_summary=data_summary)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        try:
            result = await self.provider.chat_completion(
                messages,
                temperature=0.4,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(result["content"])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("DataInsight parse error: %s", e)
            return {
                "text": "抱歉，数据分析时遇到了问题，请稍后重试。",
                "cards": [],
                "suggested_actions": [],
            }

        cards = []
        for chart in parsed.get("charts", []):
            cards.append({"type": "data-chart", "data": chart})

        for insight in parsed.get("insights", []):
            cards.append({"type": "knowledge-card", "data": insight})

        return {
            "text": parsed.get("text", "以下是数据分析结果："),
            "cards": cards,
            "suggested_actions": parsed.get("suggested_actions", [
                {"label": "查看详细报告", "action": "detailed_report"},
                {"label": "导出数据", "action": "export_data"},
            ]),
        }

    @staticmethod
    def _generate_mock_summary() -> str:
        return json.dumps({
            "period": "最近7天",
            "total_scripts": 156,
            "published_scripts": 120,
            "total_usages": 892,
            "avg_daily_usages": 127.4,
            "top_categories": [
                {"name": "破冰话术", "count": 245},
                {"name": "挖需话术", "count": 198},
                {"name": "逼单话术", "count": 167},
                {"name": "异议处理", "count": 152},
                {"name": "回访话术", "count": 130},
            ],
            "team_usage": [
                {"user": "张三", "usage_count": 89, "avg_rating": 4.2},
                {"user": "李四", "usage_count": 76, "avg_rating": 3.8},
                {"user": "王五", "usage_count": 65, "avg_rating": 4.5},
            ],
            "conversion_rate_avg": 0.23,
            "training_completion": 0.78,
        }, ensure_ascii=False, indent=2)
