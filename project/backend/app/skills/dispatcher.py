import json
import logging

from app.providers.base import ModelProvider
from app.skills.base import Skill
from app.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)

INTENT_SYSTEM_PROMPT = """你是千锤·营销话术AI操作系统的意图识别引擎。

根据用户输入，判断应该调用哪个Skill。如果没有合适的Skill则返回"general_chat"。

可用的Skills：
{skill_list}

请以JSON格式返回结果，仅包含以下字段：
{{"skill": "skill名称", "confidence": 0.0-1.0, "extracted_params": {{}}}}

extracted_params中应包含从用户输入中提取的关键参数，如：
- scenario: 场景描述
- customer_type: 客户类型
- difficulty: 难度等级
- category: 话术分类
- time_range: 时间范围
- query: 查询内容"""


class SkillDispatcher:
    """Uses LLM to identify user intent and dispatch to the appropriate Skill."""

    def __init__(self, provider: ModelProvider):
        self.provider = provider
        self.registry = SkillRegistry()

    async def dispatch(self, user_input: str, context: dict) -> tuple[Skill | None, dict]:
        """Identify intent and return the matched Skill with extracted params.

        Returns:
            (skill_or_none, {"skill_name": str, "confidence": float, "params": dict})
        """
        skills = self.registry.list_skills()
        if not skills:
            return None, {"skill_name": "general_chat", "confidence": 1.0, "params": {}}

        skill_list = "\n".join(
            f"- {s.name}: {s.description} (触发词: {', '.join(s.trigger_phrases)})"
            for s in skills
        )

        messages = [
            {
                "role": "system",
                "content": INTENT_SYSTEM_PROMPT.format(skill_list=skill_list),
            },
            {"role": "user", "content": user_input},
        ]

        try:
            result = await self.provider.chat_completion(
                messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(result["content"])
            skill_name = parsed.get("skill", "general_chat")
            confidence = parsed.get("confidence", 0.0)
            extracted_params = parsed.get("extracted_params", {})
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Intent recognition parse error: %s", e)
            skill_name = "general_chat"
            confidence = 0.5
            extracted_params = {}

        skill = self.registry.get_skill(skill_name)
        dispatch_result = {
            "skill_name": skill_name,
            "confidence": confidence,
            "params": extracted_params,
        }

        if skill is None and skill_name != "general_chat":
            logger.warning("Skill '%s' not found in registry, falling back", skill_name)

        return skill, dispatch_result
