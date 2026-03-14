"""3层7维话术诊断引擎 [v1.1 新增]

实现前置分类 + 规则评分 + LLM语义评分 + 根因归类。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS = {"A1": 20, "A2": 15, "B1": 15, "B2": 15, "B3": 10, "C1": 15, "C2": 10}

CONTACT_KEYWORDS = [
    "电话", "手机", "联系方式", "微信", "加我", "留个", "号码", "回电",
    "预约", "到院", "方便联系", "留下您的",
]
URGE_KEYWORDS = ["还在吗", "能收到消息吗", "请问还在吗", "亲还在吗"]
EMPATHY_KEYWORDS = ["理解", "放心", "不用担心", "很多人都", "正常的"]
POLITE_KEYWORDS = ["您好", "请问", "感谢", "谢谢"]
SELF_REF_KEYWORDS = ["我院", "我们医院", "本院", "我们的医生", "我们拥有"]


@dataclass
class DialogTurn:
    index: int
    role: str  # "service" or "user"
    content: str
    char_count: int = 0

    def __post_init__(self):
        self.char_count = len(self.content)


@dataclass
class Classification:
    traffic_quality: str = "valid"  # valid / invalid / gray
    dialog_depth: str = "normal"   # ultra_short / short / normal
    service_mode: str = "robot"    # robot / human / hybrid
    skip_scoring: bool = False


@dataclass
class DimensionScore:
    score: int = 100
    weight: int = 0
    details: list[str] = field(default_factory=list)

    def deduct(self, points: int, reason: str):
        self.score = max(0, self.score - points)
        self.details.append(f"-{points}: {reason}")

    def bonus(self, points: int, reason: str):
        self.score = min(100, self.score + points)
        self.details.append(f"+{points}: {reason}")


@dataclass
class RootCause:
    type: str          # config / script / traffic / product
    description: str
    affected_turns: list[int] = field(default_factory=list)


class DiagnosisEngine:
    """3层7维话术诊断引擎。"""

    def __init__(self, industry_weights: dict | None = None):
        self.weights = industry_weights or DEFAULT_WEIGHTS

    def diagnose(self, conversation_text: str, search_term: str = "",
                 service_mode: str = "robot") -> dict:
        turns = self._parse_turns(conversation_text)
        if not turns:
            return {"error": "无法解析对话内容"}

        classification = self._classify(turns, search_term, service_mode)
        if classification.skip_scoring:
            return {
                "classification": self._classification_dict(classification),
                "skip_reason": "无效流量或极短对话（无用户回复）",
                "score_result": None,
                "root_causes": [],
            }

        service_turns = [t for t in turns if t.role == "service"]
        user_turns = [t for t in turns if t.role == "user"]

        a1 = self._score_a1_rhythm(turns, service_turns)
        a2 = self._score_a2_value_progression(turns, service_turns, search_term)
        b1 = self._score_b1_first_reply(service_turns, search_term, user_turns)
        c1 = self._score_c1_engagement(user_turns)
        c2 = self._score_c2_warmth(service_turns, classification.service_mode)

        # B2/B3 needs LLM; set placeholder scores for rule-only mode
        b2 = DimensionScore(score=50, weight=self.weights["B2"], details=["[规则降级] 需LLM获取精确评分"])
        b3 = DimensionScore(score=50, weight=self.weights["B3"], details=["[规则降级] 需LLM获取精确评分"])

        for dim, key in [(a1, "A1"), (a2, "A2"), (b1, "B1"), (b2, "B2"),
                         (b3, "B3"), (c1, "C1"), (c2, "C2")]:
            dim.weight = self.weights[key]

        total_weight = sum(self.weights.values())
        overall = round(sum(
            d.score * d.weight for d in [a1, a2, b1, b2, b3, c1, c2]
        ) / total_weight)

        root_causes = self._identify_root_causes(a1, a2, b1, b2, b3, c1, c2)

        return {
            "classification": self._classification_dict(classification),
            "score_result": {
                "overall": overall,
                "grade": self._grade(overall),
                "dimensions": {
                    "A1_rhythm": {"score": a1.score, "weight": a1.weight, "details": a1.details},
                    "A2_value_progression": {"score": a2.score, "weight": a2.weight, "details": a2.details},
                    "B1_first_reply": {"score": b1.score, "weight": b1.weight, "details": b1.details},
                    "B2_relevance": {"score": b2.score, "weight": b2.weight, "details": b2.details},
                    "B3_depth": {"score": b3.score, "weight": b3.weight, "details": b3.details},
                    "C1_engagement": {"score": c1.score, "weight": c1.weight, "details": c1.details},
                    "C2_warmth": {"score": c2.score, "weight": c2.weight, "details": c2.details},
                },
            },
            "root_causes": [{"type": rc.type, "description": rc.description,
                             "affected_turns": rc.affected_turns} for rc in root_causes],
        }

    def _parse_turns(self, text: str) -> list[DialogTurn]:
        turns: list[DialogTurn] = []
        lines = text.strip().split("\n")
        idx = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if re.match(r"^(客户|用户|访客|客服|咨询师|机器人|服务|客户端)[：:]", line):
                parts = line.split("：", 1) if "：" in line else line.split(":", 1)
                role_text = parts[0].strip()
                content = parts[1].strip() if len(parts) > 1 else ""
                role = "user" if role_text in ("客户", "用户", "访客", "客户端") else "service"
                turns.append(DialogTurn(index=idx, role=role, content=content))
                idx += 1
        return turns

    def _classify(self, turns: list[DialogTurn], search_term: str, service_mode: str) -> Classification:
        user_turns = [t for t in turns if t.role == "user"]
        total_rounds = len(user_turns)

        depth = "normal"
        if total_rounds <= 0:
            depth = "ultra_short"
        elif total_rounds <= 2:
            depth = "short"

        skip = depth == "ultra_short" and not user_turns

        return Classification(
            traffic_quality="valid",
            dialog_depth=depth,
            service_mode=service_mode,
            skip_scoring=skip,
        )

    def _score_a1_rhythm(self, turns: list[DialogTurn], service_turns: list[DialogTurn]) -> DimensionScore:
        dim = DimensionScore()

        first_contact_idx = None
        for t in turns:
            if t.role == "service" and any(kw in t.content for kw in CONTACT_KEYWORDS):
                first_contact_idx = t.index
                break

        if first_contact_idx is not None and len(turns) > 0:
            position = first_contact_idx / max(len(turns), 1)
            if position < 0.10:
                dim.deduct(25, f"留联过急（位置{position:.0%}）")
            elif position < 0.25:
                dim.deduct(10, f"留联偏早（位置{position:.0%}）")

        max_consecutive = 0
        current_consecutive = 0
        for t in turns:
            if t.role == "service":
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        if max_consecutive >= 8:
            dim.deduct(30, f"严重刷屏（连续{max_consecutive}条）")
        elif max_consecutive >= 5:
            dim.deduct(12, f"刷屏偏急（连续{max_consecutive}条）")

        urge_count = sum(
            1 for t in service_turns
            if any(kw in t.content for kw in URGE_KEYWORDS)
        )
        if urge_count >= 3:
            dim.deduct(25, f"多次催促（{urge_count}次）")
        elif urge_count >= 2:
            dim.deduct(10, f"催促（{urge_count}次）")

        return dim

    def _score_a2_value_progression(self, turns: list[DialogTurn],
                                     service_turns: list[DialogTurn],
                                     search_term: str) -> DimensionScore:
        dim = DimensionScore()

        first_contact_idx = None
        for t in turns:
            if t.role == "service" and any(kw in t.content for kw in CONTACT_KEYWORDS):
                first_contact_idx = t.index
                break

        if first_contact_idx is not None:
            pre_contact_service = [t for t in service_turns if t.index < first_contact_idx]
            substantive = [t for t in pre_contact_service if t.char_count > 30]
            if not substantive:
                dim.deduct(35, "留联前无任何实质性回复")
            elif len(substantive) == 1:
                dim.deduct(10, "留联前仅有1条实质回复")

            contact_turn = next((t for t in turns if t.index == first_contact_idx), None)
            if contact_turn:
                has_value_exchange = any(
                    kw in contact_turn.content
                    for kw in ["方案", "报价", "对比", "为您", "帮您", "发您"]
                )
                if not has_value_exchange:
                    dim.deduct(20, "留联话术缺乏价值交换")

        return dim

    def _score_b1_first_reply(self, service_turns: list[DialogTurn],
                               search_term: str,
                               user_turns: list[DialogTurn]) -> DimensionScore:
        dim = DimensionScore()
        if not service_turns:
            dim.deduct(30, "无客服回复")
            return dim

        first = service_turns[0]

        if search_term and search_term in first.content:
            dim.bonus(10, "首条直接回应搜索词")
        elif search_term:
            found_in_top3 = any(
                search_term in t.content for t in service_turns[:3]
            )
            if not found_in_top3:
                dim.deduct(20, "前3条均未回应搜索词")

        is_contact = any(kw in first.content for kw in CONTACT_KEYWORDS)
        has_subsequent_value = any(t.char_count > 30 for t in service_turns[1:4])

        if is_contact and not has_subsequent_value:
            dim.deduct(25, "首条留联且无后续价值输出")
        elif is_contact and has_subsequent_value:
            dim.deduct(10, "首条留联但后续有价值输出（轻微扣分）")

        if any(kw in first.content for kw in SELF_REF_KEYWORDS):
            dim.deduct(22, "首条品牌自吹")

        return dim

    def _score_c1_engagement(self, user_turns: list[DialogTurn]) -> DimensionScore:
        dim = DimensionScore()

        if not user_turns:
            dim.score = 40
            dim.details.append("无用户回复，基准分40")
            return dim

        dim.score = 75
        dim.details.append("有用户回复，基准分75")

        substantive = [t for t in user_turns if t.char_count > 5]
        if substantive:
            dim.bonus(10, f"有{len(substantive)}条实质性回复")

        if len(user_turns) >= 3:
            dim.bonus(10, f"{len(user_turns)}轮有效互动")

        questions = [t for t in user_turns if "?" in t.content or "？" in t.content]
        if questions:
            dim.bonus(5, "用户主动提问")

        return dim

    def _score_c2_warmth(self, service_turns: list[DialogTurn], service_mode: str) -> DimensionScore:
        dim = DimensionScore()
        reduction = 0.5 if service_mode == "robot" else 1.0

        has_empathy = any(
            any(kw in t.content for kw in EMPATHY_KEYWORDS)
            for t in service_turns
        )
        if not has_empathy:
            dim.deduct(int(20 * reduction), "缺乏共情表达")

        has_polite = any(
            any(kw in t.content for kw in POLITE_KEYWORDS)
            for t in service_turns
        )
        if not has_polite:
            dim.deduct(8, "缺乏基础礼貌用语")

        short_ratio = sum(1 for t in service_turns if t.char_count < 10) / max(len(service_turns), 1)
        if short_ratio > 0.4:
            dim.deduct(10, f"短消息占比过高（{short_ratio:.0%}）")

        return dim

    def _identify_root_causes(self, a1, a2, b1, b2, b3, c1, c2) -> list[RootCause]:
        causes: list[RootCause] = []

        if a1.score < 60:
            causes.append(RootCause(type="config", description="对话节奏设计不佳（留联时机/消息密度/催促）"))
        if a2.score < 60:
            causes.append(RootCause(type="config", description="价值递进策略不足（留联前缺乏价值输出）"))
        if b1.score < 60:
            causes.append(RootCause(type="config", description="首条回复效力不足（未回应搜索词/品牌自吹）"))
        if b2.score < 60:
            causes.append(RootCause(type="script", description="应答相关性低（回复与用户问题不相关）"))
        if b3.score < 60:
            causes.append(RootCause(type="script", description="专业内容深度不足"))
        if c1.score < 50:
            causes.append(RootCause(type="traffic", description="用户参与度极低（可能是流量质量问题）"))
        if c2.score < 60:
            causes.append(RootCause(type="script", description="服务温度感知不足（缺乏共情/礼貌）"))

        return causes

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 85:
            return "A"
        if score >= 70:
            return "B"
        if score >= 55:
            return "C"
        return "D"

    @staticmethod
    def _classification_dict(c: Classification) -> dict:
        return {
            "traffic_quality": c.traffic_quality,
            "dialog_depth": c.dialog_depth,
            "service_mode": c.service_mode,
        }
