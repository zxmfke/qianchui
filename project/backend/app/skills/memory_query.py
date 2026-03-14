import json
import logging

from app.providers.base import ModelProvider
from app.skills.base import Skill

logger = logging.getLogger(__name__)

MEMORY_QUERY_PROMPT = """你是千锤·营销话术AI操作系统的企业记忆查询助手。

企业记忆系统存储了企业的核心知识链路：痛点 → 产品 → 服务 → 话术。
你的职责是根据用户查询，从企业记忆中检索相关知识并以结构化方式呈现。

## 企业记忆数据
### 痛点库
{pain_points}

### 产品库
{products}

### 服务库
{services}

### 关联话术
{related_scripts}

## 分析要求
1. 理解用户的查询意图
2. 从企业记忆中找到相关的知识节点
3. 展示完整的知识链路（痛点→产品→服务→话术）
4. 给出实用的建议

## 输出要求
请以JSON格式输出：
{{
  "text": "查询结果的文字说明",
  "knowledge_cards": [
    {{
      "title": "知识卡片标题",
      "type": "pain_point/product/service/script_chain",
      "content": "详细内容描述",
      "related_chain": {{
        "pain_points": ["痛点名称"],
        "products": ["产品名称"],
        "services": ["服务名称"],
        "scripts": ["相关话术摘要"]
      }}
    }}
  ],
  "suggestions": ["基于记忆的实操建议"],
  "suggested_actions": [
    {{"label": "操作标签", "action": "操作类型"}}
  ]
}}"""


class MemoryQuerySkill(Skill):
    """查询企业记忆（痛点→产品→服务→话术链路）。"""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    @property
    def name(self) -> str:
        return "memory-query"

    @property
    def description(self) -> str:
        return "查询企业记忆系统中的痛点、产品、服务和话术知识链路"

    @property
    def trigger_phrases(self) -> list[str]:
        return [
            "痛点", "产品", "服务", "知识", "企业记忆",
            "这个客户的痛点", "产品话术", "知识链", "记忆",
        ]

    async def execute(self, user_input: str, context: dict) -> dict:
        pain_points = context.get("pain_points", [])
        products = context.get("products", [])
        services = context.get("services", [])
        related_scripts = context.get("related_scripts", [])

        def _format(items: list) -> str:
            if not items:
                return "暂无数据"
            if isinstance(items[0], dict):
                return json.dumps(items, ensure_ascii=False, indent=2)
            return "\n".join(f"- {item}" for item in items)

        system_prompt = MEMORY_QUERY_PROMPT.format(
            pain_points=_format(pain_points),
            products=_format(products),
            services=_format(services),
            related_scripts=_format(related_scripts),
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        try:
            result = await self.provider.chat_completion(
                messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(result["content"])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("MemoryQuery parse error: %s", e)
            return {
                "text": "抱歉，查询企业记忆时遇到了问题，请稍后重试。",
                "cards": [],
                "suggested_actions": [],
            }

        cards = [
            {"type": "knowledge-card", "data": kc}
            for kc in parsed.get("knowledge_cards", [])
        ]

        return {
            "text": parsed.get("text", "以下是企业记忆查询结果："),
            "cards": cards,
            "suggested_actions": parsed.get("suggested_actions", [
                {"label": "查看相关话术", "action": "view_scripts"},
                {"label": "更新企业记忆", "action": "update_memory"},
            ]),
        }
