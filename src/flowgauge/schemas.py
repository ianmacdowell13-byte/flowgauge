"""Typed output models. Every tool returns one of these plus a `summary` line."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Row(BaseModel):
    """A single result row: dimension values + metric values."""
    dimensions: dict[str, str] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)


class ReportResult(BaseModel):
    summary: str
    date_range: str
    compare_range: str | None = None
    rows: list[Row] = Field(default_factory=list)
    sampled: bool = False
    notes: list[str] = Field(default_factory=list)
