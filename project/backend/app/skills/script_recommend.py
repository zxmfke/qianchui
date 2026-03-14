import json
import logging

from app.providers.base import ModelProvider
from app.skills.base import Skill

logger = logging.getLogger(__name__)

RECOMMEND_SYSTEM_PROMPT = """你是千锤·营销话术AI操作系统的话术推荐专家。

你的职责是根据用户描述的场景、客户心理状态和业务上下文，推荐最合适的营销话术。

## 核心能力
你必须按照「话术三层结构」来组织推荐：

### 第一层：心理层（WHY — 为什么这么说）
分析客户当前的心理状态：
- 信任阶段：陌生→好奇→信任→依赖
- 情绪状态：焦虑/犹豫/抗拒/期待/急迫
- 决策阶段：认知→兴趣→评估→决定→行动

### 第二层：策略层（HOW — 怎么说的框架）
选择最合适的沟通策略：
- 破冰策略：访问式提问 → 痛点共鸣 → 建立信任
- 挖需策略：反问痛点 → 认同感受 → 解答疑虑
- 逼单策略：稀缺性 → 社会证明 → 占便宜心理
- 异议处理：认同 → 转化 → 引导

### 第三层：话术层（WHAT — 具体说什么）
提供可以直接使用的话术文本，包括：
- 开场话术、引导话术、成交话术
- 每条话术标注适用场景

## 企业记忆上下文
{enterprise_memory}

## 话术库中的相关话术
{existing_scripts}

## 输出要求
请以JSON格式输出，结构如下：
{{
  "text": "总结性的推荐说明文字",
  "recommendations": [
    {{
      "title": "话术标题",
      "psychology": {{
        "trust_stage": "信任阶段判断",
        "emotion": "情绪状态",
        "decision_stage": "决策阶段",
        "analysis": "心理层分析说明"
      }},
      "strategy": {{
        "name": "策略名称",
        "framework": "策略框架描述",
        "key_principle": "核心原则"
      }},
      "scripts": [
        {{
          "text": "具体话术文本",
          "scenario": "适用场景",
          "tone": "语气风格"
        }}
      ]
    }}
  ],
  "suggested_actions": [
    {{"label": "操作标签", "action": "操作类型"}}
  ]
}}

请推荐2-3条话术，每条都要包含完整的三层结构。话术要自然、有温度、不生硬。"""


class ScriptRecommendSkill(Skill):
    """根据场景描述，从话术库中检索并AI生成推荐话术。"""

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    @property
    def name(self) -> str:
        return "script-recommend"

    @property
    def description(self) -> str:
        return "根据场景/客户类型推荐合适的营销话术，输出包含心理层、策略层、话术层的完整推荐"

    @property
    def trigger_phrases(self) -> list[str]:
        return ["推荐话术", "推荐一个话术", "这种客户怎么说", "有什么好的话术", "话术推荐", "应对话术"]

    async def execute(self, user_input: str, context: dict) -> dict:
        enterprise_memory = context.get("enterprise_memory", "暂无企业记忆数据")
        existing_scripts = context.get("relevant_scripts", "暂无相关话术")

        if isinstance(enterprise_memory, dict):
            enterprise_memory = json.dumps(enterprise_memory, ensure_ascii=False, indent=2)
        if isinstance(existing_scripts, (list, dict)):
            existing_scripts = json.dumps(existing_scripts, ensure_ascii=False, indent=2)

        system_prompt = RECOMMEND_SYSTEM_PROMPT.format(
            enterprise_memory=enterprise_memory,
            existing_scripts=existing_scripts,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        try:
            result = await self.provider.chat_completion(
                messages,
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(result["content"])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("ScriptRecommend parse error: %s", e)
            return {
                "text": "抱歉，话术推荐时遇到了问题，请稍后重试。",
                "cards": [],
                "suggested_actions": [],
            }

        cards = [
            {
                "type": "script-card",
                "data": rec,
            }
            for rec in parsed.get("recommendations", [])
        ]

        suggested_actions = parsed.get("suggested_actions", [
            {"label": "加入我的话术库", "action": "save_script"},
            {"label": "用这个话术演练", "action": "start_simulation"},
            {"label": "换一批推荐", "action": "refresh_recommend"},
        ])

        return {
            "text": parsed.get("text", "为您推荐了以下话术："),
            "cards": cards,
            "suggested_actions": suggested_actions,
        }
