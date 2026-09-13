import type { HotspotResponse, TimelineResponse } from "../types/api";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`);
  if (!response.ok) {
    throw new Error(`PortFlow API returned ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function fetchTimeline(start: string): Promise<TimelineResponse> {
  return getJson(`/api/v1/timeline?start=${encodeURIComponent(start)}&seed=42`);
}

export function fetchHotspots(asOf: string): Promise<HotspotResponse> {
  return getJson(
    `/api/v1/hotspots?as_of=${encodeURIComponent(asOf)}&horizon_hours=24&seed=42`,
  );
}
