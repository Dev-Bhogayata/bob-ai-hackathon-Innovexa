"""Typed response contracts for PortFlow operational visualizations."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TimelineItem(BaseModel):
    vessel_id: str
    berth_id: str
    priority: str
    scheduled_start: datetime
    scheduled_end: datetime
    eta: datetime
    etd: datetime
    wait_hours: float = Field(ge=0)
    teu_capacity: int = Field(gt=0)
    status: str
    crane_ids: list[str] = Field(default_factory=list)
    yard_zone_id: str | None = None
    yard_allocated_teu: float | None = Field(default=None, ge=0)
    yard_capacity_shortfall_teu: float = Field(default=0, ge=0)


class TimelineResponse(BaseModel):
    api_version: str = "v1"
    window_start: datetime
    window_end: datetime
    duration_hours: int = Field(default=72, ge=1, le=72)
    berths: list[str]
    items: list[TimelineItem]


class HotspotFactor(BaseModel):
    name: str
    value: float
    unit: str


class HotspotItem(BaseModel):
    resource_id: str
    resource_type: str
    label: str
    score: float = Field(ge=0, le=100)
    risk_level: str
    factors: list[HotspotFactor]
    recommended_action: str


class HotspotResponse(BaseModel):
    api_version: str = "v1"
    as_of: datetime
    horizon_hours: int = Field(default=24, ge=1, le=72)
    items: list[HotspotItem]


class SupervisorSummaryRequest(BaseModel):
    assignments: list[dict[str, object]]
    predictions: list[dict[str, object]] = Field(default_factory=list)
    route_recommendations: dict[str, list[dict[str, object]]] = Field(default_factory=dict)
    live: bool = False


class SupervisorSummaryResponse(BaseModel):
    mode: str
    messages: list[dict[str, str]]
    summary: str | None = None
