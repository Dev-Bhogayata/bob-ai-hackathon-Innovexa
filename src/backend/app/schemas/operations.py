"""Typed response contracts for PortFlow operational visualizations."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    duration_hours: int = Field(default=72, ge=1, le=720)
    berths: list[str]
    items: list[TimelineItem]


class VesselInput(BaseModel):
    """Validated vessel input accepted by the live planning endpoint."""

    model_config = ConfigDict(extra="forbid")

    vessel_id: str = Field(min_length=1)
    vessel_name: str | None = None
    eta: datetime
    etd: datetime
    teu_capacity: int = Field(gt=0)
    vessel_length_m: float = Field(gt=0)
    draft_m: float = Field(gt=0)
    required_cranes: int = Field(ge=1)
    cargo_type: str = Field(min_length=1)
    priority: str = Field(default="standard", pattern="^(standard|priority|critical)$")
    assigned_berth_id: str | None = None

    @field_validator("eta", "etd")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def valid_service_window(self) -> "VesselInput":
        if self.etd <= self.eta:
            raise ValueError("etd must be after eta")
        return self


class BerthInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    berth_id: str = Field(min_length=1)
    berth_name: str | None = None
    max_vessel_length_m: float = Field(gt=0)
    min_depth_m: float = Field(gt=0)
    assigned_crane_count: int = Field(ge=1)


class YardZoneInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: str = Field(min_length=1)
    zone_name: str | None = None
    cargo_type: str | None = None
    capacity_teu: int = Field(gt=0)
    current_fill_pct: float = Field(ge=0, le=100)
    reefer_plug_count: int = Field(default=0, ge=0)


class ShockInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shock_id: str = Field(min_length=1)
    shock_type: str = Field(min_length=1)
    severity: str = Field(default="moderate", pattern="^(moderate|severe)$")
    start_time: datetime
    end_time: datetime
    arrival_rate_multiplier: float = Field(default=1, ge=1)
    capacity_reduction_pct: float = Field(default=0, ge=0, le=100)
    description: str | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def shock_timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def valid_shock_window(self) -> "ShockInput":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class ScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vessels: list[VesselInput] = Field(min_length=1)
    berths: list[BerthInput] = Field(min_length=1)
    yard_zones: list[YardZoneInput] = Field(min_length=1)
    shocks: list[ShockInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_ids_and_references(self) -> "ScenarioInput":
        for label, values, key in (
            ("vessels", self.vessels, "vessel_id"),
            ("berths", self.berths, "berth_id"),
            ("yard_zones", self.yard_zones, "zone_id"),
            ("shocks", self.shocks, "shock_id"),
        ):
            ids = [getattr(value, key) for value in values]
            if len(ids) != len(set(ids)):
                raise ValueError(f"{label} IDs must be unique")
        berth_ids = {berth.berth_id for berth in self.berths}
        unknown = {
            vessel.assigned_berth_id
            for vessel in self.vessels
            if vessel.assigned_berth_id and vessel.assigned_berth_id not in berth_ids
        }
        if unknown:
            raise ValueError(f"assigned_berth_id references unknown berth(s): {sorted(unknown)}")
        return self


class TimelineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: ScenarioInput
    window_start: datetime
    window_end: datetime

    @field_validator("window_start", "window_end")
    @classmethod
    def window_timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("window timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def valid_window(self) -> "TimelineRequest":
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        if (self.window_end - self.window_start).total_seconds() > 720 * 3600:
            raise ValueError("time window must not exceed 720 hours")
        return self


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


class HotspotRequest(BaseModel):
    scenario: ScenarioInput
    as_of: datetime
    horizon_hours: int = Field(default=24, ge=1, le=72)

    @field_validator("as_of")
    @classmethod
    def hotspot_timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of must include a timezone")
        return value


class SupervisorSummaryRequest(BaseModel):
    assignments: list[dict[str, object]]
    predictions: list[dict[str, object]] = Field(default_factory=list)
    route_recommendations: dict[str, list[dict[str, object]]] = Field(default_factory=dict)
    live: bool = False


class SupervisorSummaryResponse(BaseModel):
    mode: str
    messages: list[dict[str, str]]
    summary: str | None = None
