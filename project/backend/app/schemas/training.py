import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class QuizOption(BaseModel):
    key: str
    text: str


class QuizQuestion(BaseModel):
    id: str = ""
    question: str = ""
    scenario: str = ""
    customer_state: str = ""
    options: list[QuizOption] = []
    correct_answer: str = ""
    category: str = ""
    difficulty: int = 1
    explanation: dict = {}
    script_id: uuid.UUID | None = None


class QuizResponse(BaseModel):
    questions: list[QuizQuestion]
    total: int


class QuizAnswerSubmit(BaseModel):
    question_id: str
    answer: str
    question_data: dict = Field(default_factory=dict)


class AnswerExplanation(BaseModel):
    psychology: str
    strategy: str
    script: str


class QuizAnswerResult(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: AnswerExplanation
    user_accuracy: float
    category_accuracy: float


class WeakPointItem(BaseModel):
    category: str
    accuracy: float
    total_questions: int
    wrong_count: int


class TrainingProgressResponse(BaseModel):
    total_questions: int
    correct_count: int
    accuracy: float
    streak_days: int
    weak_points: list[WeakPointItem]
    recent_categories: list[str]
