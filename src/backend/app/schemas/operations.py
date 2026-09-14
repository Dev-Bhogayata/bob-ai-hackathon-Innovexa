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
