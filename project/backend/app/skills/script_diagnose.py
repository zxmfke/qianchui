import json
import logging

from app.providers.base import ModelProvider
from app.skills.base import Skill

logger = logging.getLogger(__name__)

DIAGNOSE_SYSTEM_PROMPT = """你是千锤·营销话术AI操作系统的话术诊断专家。

你的职责是分析真实的客户对话记录，按照「话术三层结构」进行全面诊断，输出详细的诊断报告。

## 诊断框架

### 第一层：心理层诊断（WHY）
检查咨询师是否准确判断了客户的心理状态：
- 是否正确识别客户的信任阶段（陌生→好奇→信任→依赖）？
- 是否准确判断客户的情绪状态（焦虑/犹豫/抗拒/期待/急迫）？
- 是否理解客户的决策阶段？
- 常见错误：在客户已经信任时仍在做破冰、误判客户情绪导致策略失误

### 第二层：策略层诊断（HOW）
检查咨询师选择的沟通策略是否合适：
- 是否选择了正确的策略（破冰/挖需/方案/逼单/异议处理）？
- 策略切换的时机是否恰当？
- 常见错误：客户还在犹豫就开始逼单、过早报价、未做充分挖需

### 第三层：话术层诊断（WHAT）
检查具体话术文本是否得当：
- 话术是否自然、有温度？
- 是否过于模板化？
- 是否有情绪价值？
- 常见错误：过于生硬的模板话术、缺乏共情

## 评分标准
- 每一层0-100分
- 总分为三层的加权平均（心理层30%、策略层40%、话术层30%）

## 输出要求
请以JSON格式输出：
{{
  "overall_score": 72,
  "diagnosis": {{
    "psychology_layer": {{
      "score": 65,
      "issues": [
        {{
          "turn": 3,
          "issue": "问题描述",
          "original": "原始话术",
          "suggested": "建议话术"
        }}
      ]
    }},
    "strategy_layer": {{
      "score": 70,
      "issues": [
        {{
          "turn": 5,
          "issue": "问题描述",
          "current_strategy": "当前策略",
          "suggested_strategy": "建议策略"
        }}
      ]
    }},
    "script_layer": {{
      "score": 80,
      "issues": [
        {{
          "turn": 7,
          "issue": "问题描述",
          "original": "原始话术",
          "suggested": "建议话术"
        }}
      ]
    }}
  }},
  "improvement_plan": [
    "改进建议1",
    "改进建议2"
  ],
  "summary": "总结性诊断说明"
}}

请逐轮分析对话，找出所有问题点。每个问题都要给出具体的改进建议。"""


class ScriptDiagnoseSkill(Skill):
    """分析对话记录，输出基于三层结构的诊断报告。"""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    @property
    def name(self) -> str:
        return "script-diagnose"

    @property
    def description(self) -> str:
        return "分析客户对话记录，按心理层/策略层/话术层输出诊断报告和改进建议"

    @property
    def trigger_phrases(self) -> list[str]:
        return ["分析对话", "诊断话术", "对话诊断", "帮我诊断", "看看这段对话", "话术分析"]

    async def execute(self, user_input: str, context: dict) -> dict:
        conversation_text = context.get("conversation_text", user_input)

        messages = [
            {"role": "system", "content": DIAGNOSE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"请诊断以下对话记录：\n\n{conversation_text}",
            },
        ]

        try:
            result = await self.provider.chat_completion(
                messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(result["content"])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("ScriptDiagnose parse error: %s", e)
            return {
                "text": "抱歉，诊断分析时遇到了问题，请确保提供了完整的对话记录后重试。",
                "cards": [],
                "suggested_actions": [],
            }

        diagnosis = parsed.get("diagnosis", {})
        overall_score = parsed.get("overall_score", 0)

        card = {
            "type": "diagnosis-report",
            "data": {
                "overall_score": overall_score,
                "psychology_layer": diagnosis.get("psychology_layer", {}),
                "strategy_layer": diagnosis.get("strategy_layer", {}),
                "script_layer": diagnosis.get("script_layer", {}),
                "improvement_plan": parsed.get("improvement_plan", []),
            },
        }

        return {
            "text": parsed.get("summary", f"诊断完成，总评分：{overall_score}/100"),
            "cards": [card],
            "suggested_actions": [
                {"label": "查看推荐话术", "action": "recommend_for_issues"},
                {"label": "开始针对性演练", "action": "start_simulation"},
                {"label": "保存诊断报告", "action": "save_report"},
            ],
        }
