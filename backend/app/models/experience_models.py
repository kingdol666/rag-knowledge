"""Pydantic models for Experience API."""
from __future__ import annotations
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class ExperienceCategory(str, Enum):
    BEST_PRACTICE = "best_practice"
    TROUBLESHOOTING = "troubleshooting"
    LESSON_LEARNED = "lesson_learned"
    OPTIMIZATION = "optimization"
    TIP = "tip"
    WORKFLOW = "workflow"
    DECISION = "decision"


class ExperienceResult(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class ExperienceSeverity(str, Enum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    NORMAL = "normal"
    TIP = "tip"


class ExperienceStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ExperienceCreate(BaseModel):
    title: str
    scenario: str = ""
    category: ExperienceCategory = ExperienceCategory.TIP
    problem: str = ""
    solution: str = ""
    result: ExperienceResult = ExperienceResult.SUCCESS
    key_lessons: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    severity: ExperienceSeverity = ExperienceSeverity.NORMAL
    related_docs: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class ExperienceUpdate(BaseModel):
    title: Optional[str] = None
    scenario: Optional[str] = None
    category: Optional[ExperienceCategory] = None
    problem: Optional[str] = None
    solution: Optional[str] = None
    result: Optional[ExperienceResult] = None
    key_lessons: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    severity: Optional[ExperienceSeverity] = None
    status: Optional[ExperienceStatus] = None
    related_docs: Optional[list[str]] = None
    prerequisites: Optional[list[str]] = None
    metrics: Optional[dict[str, Any]] = None


class ExperienceApplyRequest(BaseModel):
    user: str = ""
    context: str = ""
    result: str = ""
    notes: str = ""


class ExperienceReviewRequest(BaseModel):
    reviewer: str = ""
    rating: float = Field(default=5.0, ge=0, le=5)
    comment: str = ""
