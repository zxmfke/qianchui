import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DiagnosisAnalyzeRequest(BaseModel):
    conversation_text: str = Field(min_length=10)


class DiagnosisIssue(BaseModel):
    turn: int
    issue: str
    original: str | None = None
    suggested: str | None = None
    current_strategy: str | None = None
    suggested_strategy: str | None = None


class DiagnosisLayerResult(BaseModel):
    score: int
    issues: list[DiagnosisIssue]


class DiagnosisResult(BaseModel):
    overall_score: int
    psychology_layer: DiagnosisLayerResult
    strategy_layer: DiagnosisLayerResult
    script_layer: DiagnosisLayerResult
    improvement_plan: list[str]


class DiagnosisAnalyzeResponse(BaseModel):
    report_id: uuid.UUID
    result: DiagnosisResult


class DiagnosisReportResponse(BaseModel):
    id: uuid.UUID
    conversation_text: str
    overall_score: int
    result: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class DiagnosisReportListResponse(BaseModel):
    items: list[DiagnosisReportResponse]
    total: int
