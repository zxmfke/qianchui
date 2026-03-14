"""话术标注 Skill [v1.1 新增]

对对话进行AI预标注：质量标注、策略标注、话术提取、知识挖掘。
"""

import json
import logging

from app.providers.base import ModelProvider
from app.skills.base import Skill

logger = logging.getLogger(__name__)

ANNOTATE_SYSTEM_PROMPT = """你是千锤·营销话术AI操作系统的话术标注专家。

分析对话记录，对每一轮客服/机器人回复进行质量标注和策略分类。

## 标注规则

1. **质量标注**：good(好) / bad(差) / neutral(中性)
   - good: 有效回应客户、推进对话、有价值输出
   - bad: 忽略客户问题、过度推销、生硬模板
   - neutral: 常规性回复，无明显好坏

2. **策略分类**：
   - ice_breaking: 破冰/开场
   - need_digging: 挖需/反问
   - solution: 方案介绍/专业解答
   - closing: 逼单/留联
   - objection_handling: 异议处理
   - empathy: 共情/安抚
   - other: 其他

3. **可提取性**：标记为good且有通用价值的回复设置extractable=true

4. **知识挖掘**：发现以下情况时添加到mining_suggestions:
   - 客户提到新的痛点/需求
   - 高频出现的用户问题
   - 值得沉淀的应对模式

## 输出格式

输出JSON：
{{
  "annotations": [
    {{
      "turn_index": 轮次序号(从0开始),
      "speaker": "service/user",
      "label": "good/bad/neutral",
      "strategy_type": "策略类型",
      "note": "标注理由",
      "confidence": 0.0-1.0,
      "extractable": true/false
    }}
  ],
  "mining_suggestions": [
    {{
      "type": "new_pain_point/new_faq/failure_pattern/good_practice",
      "description": "发现描述",
      "source_turns": [涉及的轮次]
    }}
  ]
}}"""


class ScriptAnnotateSkill(Skill):
    """对对话进行AI预标注和知识挖掘。"""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    @property
    def name(self) -> str:
        return "script-annotate"

    @property
    def description(self) -> str:
        return "对对话进行质量标注、策略分类和知识挖掘，支持AI预标注和话术提取"

    @property
    def trigger_phrases(self) -> list[str]:
        return ["标注对话", "标记话术", "标注", "话术标注", "分析标注"]

    async def execute(self, user_input: str, context: dict) -> dict:
        conversation_text = context.get("conversation_text", user_input)
        diagnosis_summary = context.get("diagnosis_summary", "")

        user_prompt = f"""【对话原文】
{conversation_text}

【诊断参考】
{diagnosis_summary if diagnosis_summary else '(无诊断参考)'}

请对以上对话进行逐轮标注和知识挖掘。"""

        messages = [
            {"role": "system", "content": ANNOTATE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            result = await self.provider.chat_completion(
                messages,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(result["content"])
            annotations = parsed.get("annotations", [])
            mining_suggestions = parsed.get("mining_suggestions", [])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Annotation generation failed: %s", e)
            annotations = []
            mining_suggestions = []

        good_count = sum(1 for a in annotations if a.get("label") == "good")
        bad_count = sum(1 for a in annotations if a.get("label") == "bad")
        extractable_count = sum(1 for a in annotations if a.get("extractable"))

        cards = [
            {
                "type": "annotation-card",
                "data": {
                    "annotations": annotations,
                    "mining_suggestions": mining_suggestions,
                    "summary": {
                        "total": len(annotations),
                        "good": good_count,
                        "bad": bad_count,
                        "extractable": extractable_count,
                        "mining_count": len(mining_suggestions),
                    },
                },
            }
        ]

        text_parts = [
            f"已完成对话标注，共 {len(annotations)} 轮：",
            f"- 优秀话术：{good_count} 条（{extractable_count} 条可提取入库）",
            f"- 问题话术：{bad_count} 条",
        ]
        if mining_suggestions:
            text_parts.append(f"- 知识挖掘发现 {len(mining_suggestions)} 条建议")

        actions = []
        if extractable_count > 0:
            actions.append({"label": f"提取 {extractable_count} 条优秀话术入库", "action": "extract_scripts"})
        if mining_suggestions:
            actions.append({"label": "查看知识挖掘建议", "action": "view_mining"})
        actions.append({"label": "进入标注工作台审核", "action": "open_annotation_workbench"})

        return {
            "text": "\n".join(text_parts),
            "cards": cards,
            "suggested_actions": actions,
        }
