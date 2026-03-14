"""渠道物料分析 Skill

分析渠道物料内容，提取品牌调性、核心卖点、风格关键词、目标受众等结构化信息。
"""

import json
import logging

from app.providers.base import ModelProvider
from app.skills.base import Skill

logger = logging.getLogger(__name__)

CHANNEL_MATERIAL_SYSTEM_PROMPT = """你是千锤·营销话术AI操作系统的渠道物料分析专家。

你的任务是从给定的渠道营销物料（视频脚本、图文、广告文案等）中，提取结构化信息，用于话术资产沉淀和复用。

## 分析维度

1. **品牌调性 (brand_tone)**：专业/温暖/活泼/高端/亲民/科技感/文艺/幽默 等，可多选
2. **核心卖点 (selling_points)**：产品特色、技术优势、差异化价值，3-5 条
3. **关键词 (keywords)**：高频表达、核心词汇、行业术语，5-10 个
4. **内容风格 (style)**：口语化/正式/种草风/测评向/故事型/干货型 等
5. **目标受众 (target_audience)**：年龄、性别、消费能力、兴趣、痛点等特征

## 输出格式

严格输出 JSON：
{{
  "brand_tone": ["调性1", "调性2"],
  "selling_points": ["卖点1", "卖点2", "卖点3"],
  "keywords": ["关键词1", "关键词2", ...],
  "style": "风格描述",
  "target_audience": "目标受众特征描述"
}}"""


class ChannelMaterialSkill(Skill):
    """分析渠道物料，提取品牌调性、核心卖点和风格关键词。"""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    @property
    def name(self) -> str:
        return "channel-material"

    @property
    def description(self) -> str:
        return "分析渠道物料，提取品牌调性、核心卖点和风格关键词"

    @property
    def trigger_phrases(self) -> list[str]:
        return ["分析物料", "提取物料信息", "渠道物料分析", "/物料"]

    async def execute(self, user_input: str, context: dict) -> dict:
        material_content = context.get("material_content", "")
        material_title = context.get("material_title", "")
        channel = context.get("channel", "")
        material_type = context.get("material_type", "")

        user_prompt = f"""【物料信息】
渠道：{channel}
类型：{material_type}
标题：{material_title}

【物料内容】
{material_content}

【用户需求】
{user_input}

请分析上述物料，按要求的 JSON 格式输出提取结果。"""

        messages = [
            {"role": "system", "content": CHANNEL_MATERIAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        extracted_info: dict = {}
        try:
            result = await self.provider.chat_completion(
                messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            content = result.get("content", "{}")
            parsed = json.loads(content)
            extracted_info = {
                "brand_tone": parsed.get("brand_tone", []),
                "selling_points": parsed.get("selling_points", []),
                "keywords": parsed.get("keywords", []),
                "style": parsed.get("style", ""),
                "target_audience": parsed.get("target_audience", ""),
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Channel material extraction failed: %s", e)

        cards = [
            {
                "type": "channel-material-extract",
                "data": extracted_info,
            }
        ]

        summary_parts = ["已完成渠道物料分析，提取结果如下："]
        if extracted_info.get("brand_tone"):
            summary_parts.append(f"\n**品牌调性**：{', '.join(extracted_info['brand_tone'])}")
        if extracted_info.get("selling_points"):
            summary_parts.append(
                f"\n**核心卖点**：\n" + "\n".join(f"- {s}" for s in extracted_info["selling_points"])
            )
        if extracted_info.get("keywords"):
            summary_parts.append(f"\n**关键词**：{', '.join(extracted_info['keywords'])}")
        if extracted_info.get("style"):
            summary_parts.append(f"\n**内容风格**：{extracted_info['style']}")
        if extracted_info.get("target_audience"):
            summary_parts.append(f"\n**目标受众**：{extracted_info['target_audience']}")

        return {
            "text": "\n".join(summary_parts),
            "cards": cards,
            "extracted_info": extracted_info,
            "suggested_actions": [
                {"label": "保存到话术库", "action": "save_to_script"},
                {"label": "创建相似话术", "action": "create_similar_script"},
                {"label": "继续分析其他物料", "action": "analyze_more"},
            ],
        }
