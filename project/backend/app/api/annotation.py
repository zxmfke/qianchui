"""话术标注 API [v1.1 新增]"""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/annotations", tags=["annotations"])


@router.post("")
async def create_annotation(
    conversation_text: str,
    turn_index: int,
    label: str,
    strategy_type: str | None = None,
    note: str | None = None,
    diagnosis_report_id: str | None = None,
):
    if label not in ("good", "bad", "neutral"):
        raise HTTPException(status_code=400, detail={"message": "label 必须为 good/bad/neutral", "message_en": "label must be good/bad/neutral"})
    return {
        "id": "placeholder-uuid",
        "turn_index": turn_index,
        "label": label,
        "strategy_type": strategy_type,
        "note": note,
        "is_ai_generated": False,
    }


@router.get("")
async def list_annotations(
    enterprise_id: str | None = None,
    diagnosis_report_id: str | None = None,
    label: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    return {"items": [], "total": 0}


@router.put("/{annotation_id}")
async def update_annotation(annotation_id: str, label: str | None = None, note: str | None = None):
    return {"id": annotation_id, "updated": True}


@router.post("/ai-pre-annotate")
async def ai_pre_annotate(
    conversation_text: str,
    diagnosis_report_id: str | None = None,
):
    return {
        "annotations": [],
        "message": "AI预标注需要配置LLM Provider",
    }


@router.post("/{annotation_id}/extract-script")
async def extract_script(annotation_id: str):
    return {
        "script": None,
        "message": "话术提取需要标注数据",
    }


@router.get("/mining/suggestions")
async def get_mining_suggestions(enterprise_id: str | None = None):
    return {"suggestions": []}
