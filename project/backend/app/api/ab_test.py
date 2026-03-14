"""AB测试 API [v1.1 新增]"""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/ab-tests", tags=["ab-tests"])


@router.post("")
async def create_ab_test(
    name: str,
    description: str | None = None,
    task_id: str | None = None,
    duration_days: int = 14,
):
    return {
        "id": "placeholder-uuid",
        "name": name,
        "status": "draft",
        "duration_days": duration_days,
    }


@router.get("")
async def list_ab_tests(
    enterprise_id: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    return {"items": [], "total": 0}


@router.get("/{test_id}")
async def get_ab_test(test_id: str):
    return {"id": test_id, "status": "draft", "variants": []}


@router.put("/{test_id}/start")
async def start_ab_test(test_id: str):
    return {"id": test_id, "status": "running"}


@router.put("/{test_id}/stop")
async def stop_ab_test(test_id: str):
    return {"id": test_id, "status": "paused"}


@router.get("/{test_id}/metrics")
async def get_ab_test_metrics(test_id: str):
    return {
        "test_id": test_id,
        "status": "running",
        "variants": [],
        "significance": {},
        "recommendation": None,
    }


@router.put("/{test_id}/conclude")
async def conclude_ab_test(test_id: str, decision: str):
    if decision not in ("promote", "rollback"):
        raise HTTPException(status_code=400, detail={"message": "decision 必须为 promote 或 rollback", "message_en": "decision must be promote/rollback"})
    return {"id": test_id, "status": "completed", "conclusion": decision}
