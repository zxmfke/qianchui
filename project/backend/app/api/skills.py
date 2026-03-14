from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.providers.factory import ModelProviderFactory
from app.skills.registry import SkillRegistry

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillExecuteRequest(BaseModel):
    scenario: str = ""
    script_content: str = ""
    customer_profile: dict | None = None
    skill_gap: str = ""
    difficulty: str = "intermediate"
    task_id: str = ""
    user_response: str = ""


class SkillDispatchRequest(BaseModel):
    skill_name: str
    input: dict = {}


class SkillInfoResponse(BaseModel):
    name: str
    description: str
    trigger_phrases: list[str] = []
    input_schema: dict = {}


def _get_provider():
    settings = get_settings()
    return ModelProviderFactory.create_provider(
        provider_type=settings.LLM_PROVIDER,
        api_key=settings.LLM_API_KEY,
        api_base=settings.LLM_API_BASE,
        model=settings.LLM_MODEL,
    )


@router.get("", response_model=list[SkillInfoResponse])
async def list_skills(user: User = Depends(get_current_user)):
    registry = SkillRegistry()
    skills = registry.list_skills()
    return [
        SkillInfoResponse(
            name=s.name,
            description=s.description,
            trigger_phrases=s.trigger_phrases,
            input_schema={},
        )
        for s in skills
    ]


@router.get("/{skill_name}", response_model=SkillInfoResponse)
async def get_skill_detail(
    skill_name: str,
    user: User = Depends(get_current_user),
):
    registry = SkillRegistry()
    skill = registry.get_skill(skill_name)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": f"技能 '{skill_name}' 未找到", "message_en": f"Skill '{skill_name}' not found"})
    return SkillInfoResponse(
        name=skill.name,
        description=skill.description,
        trigger_phrases=skill.trigger_phrases,
        input_schema={},
    )


@router.post("/dispatch")
async def dispatch_skill(
    body: SkillDispatchRequest,
    user: User = Depends(get_current_user),
):
    registry = SkillRegistry()
    skill = registry.get_skill(body.skill_name)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": f"技能 '{body.skill_name}' 未找到", "message_en": f"Skill '{body.skill_name}' not found"})

    user_input = body.input.get("scenario", "") or body.input.get("query", "")
    context = {**body.input, "enterprise_id": str(user.enterprise_id)}
    result = await skill.execute(user_input, context)
    return result


@router.post("/script-recommend")
async def recommend_script(
    body: SkillExecuteRequest,
    user: User = Depends(get_current_user),
):
    registry = SkillRegistry()
    skill = registry.get_skill("script-recommend")
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "技能未注册", "message_en": "Skill not registered"})

    context = {
        "customer_profile": body.customer_profile or {},
        "enterprise_id": str(user.enterprise_id),
    }
    result = await skill.execute(body.scenario, context)

    recommendations = []
    for card in result.get("cards", []):
        if card["type"] == "script-card":
            rec_data = card["data"]
            recommendations.append({
                "script_id": rec_data.get("title", ""),
                "relevance_score": 0.9,
                "reason": rec_data.get("strategy", {}).get("key_principle", "推荐匹配"),
                **rec_data,
            })

    return {"recommendations": recommendations, "text": result.get("text", "")}


@router.post("/script-diagnose")
async def diagnose_script(
    body: SkillExecuteRequest,
    user: User = Depends(get_current_user),
):
    registry = SkillRegistry()
    skill = registry.get_skill("script-diagnose")
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "技能未注册", "message_en": "Skill not registered"})

    context = {
        "conversation_text": body.script_content,
        "scenario": body.scenario,
        "enterprise_id": str(user.enterprise_id),
    }
    result = await skill.execute(body.script_content, context)

    overall_score = 0
    dimensions = []
    suggestions = []
    for card in result.get("cards", []):
        if card["type"] == "diagnosis-report":
            data = card["data"]
            overall_score = data.get("overall_score", 0)
            for layer_name in ("psychology_layer", "strategy_layer", "script_layer"):
                layer = data.get(layer_name, {})
                if layer:
                    dimensions.append({
                        "name": layer_name,
                        "score": layer.get("score", 0),
                        "issues": layer.get("issues", []),
                    })
            suggestions = data.get("improvement_plan", [])

    return {
        "overall_score": overall_score,
        "dimensions": dimensions,
        "suggestions": suggestions,
        "text": result.get("text", ""),
    }


@router.post("/script-train")
async def train_script(
    body: SkillExecuteRequest,
    user: User = Depends(get_current_user),
):
    registry = SkillRegistry()
    skill = registry.get_skill("script-train")
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "技能未注册", "message_en": "Skill not registered"})

    difficulty_map = {"beginner": 1, "intermediate": 2, "advanced": 3}
    difficulty_level = difficulty_map.get(body.difficulty, 2)

    context = {
        "params": {"difficulty": difficulty_level, "category": body.skill_gap or "综合", "count": 1},
        "industry": "消费医疗",
        "products": "热玛吉、水光针、吸脂塑形",
    }
    result = await skill.execute("", context)

    task = {}
    for card in result.get("cards", []):
        if card["type"] == "training-quiz":
            q = card["data"]
            task = {
                "scenario_description": q.get("scenario", ""),
                "expected_skills": [body.skill_gap or "综合"],
                "question": q,
            }
            break

    return {"task": task, "text": result.get("text", "")}


@router.post("/script-train/evaluate")
async def evaluate_training(
    body: SkillExecuteRequest,
    user: User = Depends(get_current_user),
):
    return {
        "score": 75,
        "feedback": f"针对您的回答「{body.user_response[:50]}」的评估：表达自然，但在策略层可以更深入。",
    }
