"""Pydantic models for KB Automation API (自动经验总结)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AutomationToggleRequest(BaseModel):
    """开关自动经验总结。"""
    enabled: bool


class AutomationIngestRequest(BaseModel):
    """文档入库通知（web documents/create 钩子调用）。

    doc_count: 本次入库实际落盘的文档数（大文档拆分时为 part 数，默认 1）。
    """
    doc_path: str = ""
    title: str = ""
    doc_count: int = Field(default=1, ge=1, le=100)
