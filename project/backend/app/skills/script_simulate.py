import json
import logging

from app.providers.base import ModelProvider
from app.skills.base import Skill

logger = logging.getLogger(__name__)

SIMULATE_CUSTOMER_PROMPT = """你是千锤·营销话术AI操作系统中的客户模拟器。

你正在扮演一位真实的客户，与营销/客服人员进行对话演练。

## 你的角色设定
- 客户类型：{customer_type}
- 演练场景：{scenario}
- 难度等级：{difficulty}（1=入门，2=进阶，3=高手）

## 客户人格特征

### 友好型（难度1）
- 配合度高，主动表达需求
- 会主动问问题，语气友善
- 比较容易被说服

### 犹豫型（难度2）
- 反复比较，"我再想想"
- 需要大量的信任建立
- 关注口碑和案例
- 经常问"别人做得怎么样"

### 价格敏感型（难度2）
- 始终关注价格，讨价还价
- "太贵了""有没有优惠"
- 喜欢比较不同机构
- 但如果觉得值就会果断

### 高冷型（难度3）
- 回复简短，"嗯""哦""再说"
- 不主动表达需求
- 需要耐心引导才会打开话题
- 不喜欢太热情的推销

### 投诉型（难度3）
- 带负面情绪，之前有不好的体验
- 需要先做情绪管理
- 语气可能比较冲
- 需要被倾听和认同

## 行为规则
1. 严格按照角色特征回复，不要跳出角色
2. 回复要自然、口语化，像真人聊天
3. 根据难度调整挑战性
4. 适当制造难题和异议
5. 如果对方话术很好，可以逐渐被打动
6. 回复长度控制在1-3句话

## 企业上下文
{enterprise_context}

## 对话历史
{conversation_history}

请以该客户的身份回复。只输出客户说的话，不要加任何角色标签或解释。"""

SIMULATE_HINT_PROMPT = """基于当前的客户模拟对话，分析客户当前的心理状态并给出策略建议。

客户类型：{customer_type}
场景：{scenario}
对话历史：{conversation_history}

请以JSON格式输出：
{{"customer_psychology": "客户当前心理状态分析", "suggested_strategy": "建议的应对策略"}}"""

SIMULATE_SCORE_PROMPT = """你是话术演练评分专家。请对以下演练对话进行评分。

## 评分维度
1. 心理判断（0-100）：是否准确识别客户心理变化
2. 策略选择（0-100）：沟通策略选择是否恰当
3. 话术质量（0-100）：具体话术是否自然有温度
4. 节奏把控（0-100）：对话节奏是否循序渐进

## 演练信息
客户类型：{customer_type}
场景：{scenario}
难度：{difficulty}

## 对话记录
{conversation_history}

请以JSON格式输出：
{{
  "overall_score": 82,
  "dimensions": [
    {{"dimension": "心理判断", "score": 85, "comment": "评价..."}},
    {{"dimension": "策略选择", "score": 80, "comment": "评价..."}},
    {{"dimension": "话术质量", "score": 78, "comment": "评价..."}},
    {{"dimension": "节奏把控", "score": 85, "comment": "评价..."}}
  ],
  "improvement_suggestions": ["建议1", "建议2"],
  "summary": "总评..."
}}"""


class ScriptSimulateSkill(Skill):
    """AI扮演客户进行模拟对话演练。"""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    @property
    def name(self) -> str:
        return "script-simulate"

    @property
    def description(self) -> str:
        return "AI扮演客户进行模拟对话演练，支持多种客户人格，结束后输出评分"

    @property
    def trigger_phrases(self) -> list[str]:
        return ["演练", "模拟客户", "模拟对话", "练习对话", "陪我练", "开始演练"]

    async def execute(self, user_input: str, context: dict) -> dict:
        mode = context.get("mode", "chat")

        if mode == "start":
            return await self._start_simulation(context)
        elif mode == "score":
            return await self._score_simulation(context)
        else:
            return await self._chat_turn(user_input, context)

    async def _start_simulation(self, context: dict) -> dict:
        scenario = context.get("scenario", "新客户首次咨询")
        customer_type = context.get("customer_type", "friendly")
        difficulty = context.get("difficulty", 1)

        customer_type_cn = {
            "friendly": "友好型",
            "hesitant": "犹豫型",
            "price_sensitive": "价格敏感型",
            "cold": "高冷型",
            "complaining": "投诉型",
        }.get(customer_type, customer_type)

        opening_prompt = SIMULATE_CUSTOMER_PROMPT.format(
            customer_type=customer_type_cn,
            scenario=scenario,
            difficulty=difficulty,
            enterprise_context=context.get("enterprise_context", "消费医疗行业"),
            conversation_history="（对话刚开始，请作为客户先开口说第一句话）",
        )

        result = await self.provider.chat_completion(
            [{"role": "system", "content": opening_prompt}],
            temperature=0.8,
        )

        return {
            "text": f"演练开始！场景：{scenario}，客户类型：{customer_type_cn}，难度：{'⭐' * difficulty}",
            "cards": [
                {
                    "type": "simulation-start",
                    "data": {
                        "scenario": scenario,
                        "customer_type": customer_type_cn,
                        "difficulty": difficulty,
                        "customer_opening": result["content"],
                    },
                }
            ],
            "suggested_actions": [
                {"label": "查看参考话术", "action": "view_reference"},
                {"label": "结束演练", "action": "end_simulation"},
            ],
        }

    async def _chat_turn(self, user_input: str, context: dict) -> dict:
        scenario = context.get("scenario", "客户咨询")
        customer_type = context.get("customer_type", "友好型")
        difficulty = context.get("difficulty", 1)
        history = context.get("conversation_history", [])

        history_text = "\n".join(
            f"{'客户' if m['role'] == 'customer' else '咨询师'}: {m['content']}"
            for m in history
        )

        customer_prompt = SIMULATE_CUSTOMER_PROMPT.format(
            customer_type=customer_type,
            scenario=scenario,
            difficulty=difficulty,
            enterprise_context=context.get("enterprise_context", "消费医疗行业"),
            conversation_history=history_text + f"\n咨询师: {user_input}",
        )

        customer_result = await self.provider.chat_completion(
            [{"role": "system", "content": customer_prompt}],
            temperature=0.8,
        )

        hint = None
        if context.get("show_hints", True):
            try:
                hint_prompt = SIMULATE_HINT_PROMPT.format(
                    customer_type=customer_type,
                    scenario=scenario,
                    conversation_history=history_text + f"\n咨询师: {user_input}\n客户: {customer_result['content']}",
                )
                hint_result = await self.provider.chat_completion(
                    [{"role": "user", "content": hint_prompt}],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )
                hint = json.loads(hint_result["content"])
            except Exception as e:
                logger.warning("Hint generation failed: %s", e)

        response: dict = {
            "text": customer_result["content"],
            "cards": [],
            "suggested_actions": [
                {"label": "查看参考话术", "action": "view_reference"},
                {"label": "结束演练并评分", "action": "end_simulation"},
            ],
        }

        if hint:
            response["hint"] = hint

        return response

    async def _score_simulation(self, context: dict) -> dict:
        history = context.get("conversation_history", [])
        history_text = "\n".join(
            f"{'客户' if m['role'] == 'customer' else '咨询师'}: {m['content']}"
            for m in history
        )

        score_prompt = SIMULATE_SCORE_PROMPT.format(
            customer_type=context.get("customer_type", "友好型"),
            scenario=context.get("scenario", "客户咨询"),
            difficulty=context.get("difficulty", 1),
            conversation_history=history_text,
        )

        try:
            result = await self.provider.chat_completion(
                [{"role": "user", "content": score_prompt}],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(result["content"])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Simulation scoring error: %s", e)
            parsed = {
                "overall_score": 0,
                "dimensions": [],
                "improvement_suggestions": ["评分过程出现问题，请重试"],
                "summary": "评分失败",
            }

        return {
            "text": parsed.get("summary", f"演练结束，总评分：{parsed.get('overall_score', 0)}/100"),
            "cards": [
                {
                    "type": "simulation-score",
                    "data": parsed,
                }
            ],
            "suggested_actions": [
                {"label": "再练一次", "action": "retry_simulation"},
                {"label": "换个场景", "action": "new_simulation"},
                {"label": "查看改进话术", "action": "recommend_improvement"},
            ],
        }
