export interface TimelineItem {
  vessel_id: string;
  berth_id: string;
  priority: string;
  scheduled_start: string;
  scheduled_end: string;
  eta: string;
  etd: string;
  wait_hours: number;
  teu_capacity: number;
  status: string;
  crane_ids: string[];
  yard_zone_id: string | null;
  yard_allocated_teu: number | null;
  yard_capacity_shortfall_teu: number;
}

export interface TimelineResponse {
  api_version: string;
  window_start: string;
  window_end: string;
  duration_hours: number;
  berths: string[];
  items: TimelineItem[];
}

export interface HotspotFactor {
  name: string;
  value: number;
  unit: string;
}

export interface HotspotItem {
  resource_id: string;
  resource_type: "berth" | "yard";
  label: string;
  score: number;
  risk_level: "high" | "medium" | "low";
  factors: HotspotFactor[];
  recommended_action: string;
}

export interface HotspotResponse {
  api_version: string;
  as_of: string;
  horizon_hours: number;
  items: HotspotItem[];
}
