import json
import logging

from app.providers.base import ModelProvider
from app.skills.base import Skill

logger = logging.getLogger(__name__)

TRAIN_SYSTEM_PROMPT = """你是千锤·营销话术AI操作系统的培训出题专家。

你的职责是生成高质量的话术培训选择题，帮助一线营销/客服人员通过刷题学习话术技巧。

## 出题规则

### 题目结构
每道题包含：
1. 一个真实的客户对话场景
2. 客户当前的心理/情绪状态描述
3. 四个选项（A/B/C/D），只有一个最佳答案
4. 详细的三层结构解析

### 题目质量要求
- 场景必须真实、有代入感（使用具体的行业术语和场景）
- 选项必须都像是合理的回答，不能有明显的"送分"选项
- 错误选项应该是常见的真实错误（如过早报价、忽略情绪等）
- 解析必须包含心理层、策略层、话术层的完整分析

### 难度等级
- 难度1（入门）：场景简单，正确答案较明显
- 难度2（进阶）：需要综合判断客户心理
- 难度3（高手）：复杂场景，多种策略都有道理但需要选最优

## 企业上下文
行业：{industry}
产品：{products}

## 输出要求
请以JSON格式输出：
{{
  "questions": [
    {{
      "id": "Q001",
      "scenario": "客户说的话/场景描述",
      "customer_state": "客户当前心理状态描述",
      "options": [
        {{"key": "A", "text": "选项A的话术"}},
        {{"key": "B", "text": "选项B的话术"}},
        {{"key": "C", "text": "选项C的话术"}},
        {{"key": "D", "text": "选项D的话术"}}
      ],
      "correct_answer": "B",
      "category": "破冰/挖需/逼单/异议处理/回访",
      "difficulty": 1,
      "explanation": {{
        "psychology": "心理层解析：分析客户当前心理状态...",
        "strategy": "策略层解析：为什么选择这个策略...",
        "script": "话术层解析：这条话术为什么好..."
      }},
      "wrong_explanations": {{
        "A": "为什么A是不合适的...",
        "C": "为什么C是不合适的...",
        "D": "为什么D是不合适的..."
      }}
    }}
  ]
}}

根据指定的难度和分类，生成{count}道题目。"""


class ScriptTrainSkill(Skill):
    """生成培训选择题，含三层结构解析。"""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    @property
    def name(self) -> str:
        return "script-train"

    @property
    def description(self) -> str:
        return "生成话术培训选择题，支持指定难度和分类，包含心理层/策略层/话术层解析"

    @property
    def trigger_phrases(self) -> list[str]:
        return ["出题", "练习", "刷题", "培训", "考考我", "学习话术", "每日刷题"]

    async def execute(self, user_input: str, context: dict) -> dict:
        params = context.get("params", {})
        difficulty = params.get("difficulty", 2)
        category = params.get("category", "综合")
        count = params.get("count", 3)
        industry = context.get("industry", "消费医疗")
        products = context.get("products", "热玛吉、水光针、吸脂塑形等医美项目")

        if isinstance(products, list):
            products = "、".join(products)

        system_prompt = TRAIN_SYSTEM_PROMPT.format(
            industry=industry,
            products=products,
            count=count,
        )

        user_msg = f"请生成{count}道{category}类型的话术培训题，难度等级：{difficulty}。"
        if user_input and user_input.strip():
            user_msg += f"\n用户补充要求：{user_input}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]

        try:
            result = await self.provider.chat_completion(
                messages,
                temperature=0.8,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(result["content"])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("ScriptTrain parse error: %s", e)
            return {
                "text": "抱歉，生成题目时遇到了问题，请稍后重试。",
                "cards": [],
                "suggested_actions": [],
            }

        questions = parsed.get("questions", [])
        cards = [
            {
                "type": "training-quiz",
                "data": q,
            }
            for q in questions
        ]

        return {
            "text": f"为您生成了{len(questions)}道{category}话术培训题（难度{difficulty}）：",
            "cards": cards,
            "suggested_actions": [
                {"label": "再来一组题", "action": "more_quiz"},
                {"label": "查看答题统计", "action": "view_progress"},
                {"label": "练习薄弱环节", "action": "practice_weak"},
            ],
        }
