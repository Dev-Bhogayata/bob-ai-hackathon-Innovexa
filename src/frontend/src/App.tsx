import { useCallback, useEffect, useState } from "react";
import { HotspotHeatmap } from "./components/HotspotHeatmap";
import { Timeline } from "./components/Timeline";
import { ScenarioForm } from "./components/ScenarioForm";
import { fetchHotspots, fetchTimeline, postHotspots, postTimeline } from "./services/api";
import type { HotspotResponse, TimelineResponse } from "./types/api";
import "./styles.css";

const DEMO_START = "2026-01-01T00:00:00+00:00";

export default function App() {
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [hotspots, setHotspots] = useState<HotspotResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [scenarioName, setScenarioName] = useState("Seeded demo scenario");

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [timelineData, hotspotData] = await Promise.all([
        fetchTimeline(DEMO_START),
        fetchHotspots(DEMO_START),
      ]);
      setTimeline(timelineData);
      setHotspots(hotspotData);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load PortFlow data");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadScenario = async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const scenario = JSON.parse(await file.text());
      const windowStart = scenario.window_start ?? DEMO_START;
      const request = {
        scenario: scenario.scenario ?? scenario,
        window_start: windowStart,
        window_end: scenario.window_end ?? new Date(new Date(windowStart).getTime() + 72 * 3600000).toISOString(),
      };

      const timelineData = await postTimeline(request);
      const hotspotData = await postHotspots({
        scenario: request.scenario,
        as_of: windowStart,
        horizon_hours: 24,
      });
      setTimeline(timelineData);
      setHotspots(hotspotData);
      setScenarioName(file.name);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load scenario");
    } finally {
      setLoading(false);
    }
  };

  const runScenario = async (payload: unknown, label: string) => {
    setLoading(true);
    setError(null);
    try {
      const request = payload as { scenario: unknown; window_start: string };
      const [timelineData, hotspotData] = await Promise.all([
        postTimeline(payload),
        postHotspots({ scenario: request.scenario, as_of: request.window_start, horizon_hours: 24 }),
      ]);
      setTimeline(timelineData);
      setHotspots(hotspotData);
      setScenarioName(label);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to plan scenario");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const highRiskCount = hotspots?.items.filter((item) => item.risk_level === "high").length ?? 0;
  const delayedCount = timeline?.items.filter((item) => item.status === "delayed").length ?? 0;

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">PF</span><span>PortFlow</span></div>
        <div className="topbar-meta"><span className="live-dot" /> Operations console <label className="upload-button">Load scenario JSON<input type="file" accept="application/json,.json" onChange={(event) => { const file = event.target.files?.[0]; if (file) void loadScenario(file); }} /></label><button onClick={() => void loadDashboard()}>Demo</button></div>
      </header>
      <section className="hero">
        <div>
          <p className="eyebrow">SHIFT SUPERVISOR VIEW / {scenarioName}</p>
          <h1>Make the next move <em>before</em> congestion does.</h1>
          <p className="hero-copy">AI-assisted berth planning, delay prediction, and routing recommendations in one operational picture.</p>
        </div>
        <div className="hero-stats">
          <div><strong>{timeline?.items.length ?? "--"}</strong><span>planned movements</span></div>
          <div><strong>{highRiskCount}</strong><span>high-risk hotspots</span></div>
          <div><strong>{delayedCount}</strong><span>waiting vessels</span></div>
        </div>
      </section>
      <ScenarioForm onSubmit={runScenario} disabled={loading} />
      {loading && <div className="state-card">Loading live operations data...</div>}
      {error && <div className="state-card error">{error}. Start the API with <code>uvicorn src.backend.app.main:app --reload</code>.</div>}
      {!loading && !error && timeline && hotspots && (
        <div className="dashboard-grid">
          <Timeline data={timeline} />
          <HotspotHeatmap items={hotspots.items} />
        </div>
      )}
      <footer>PortFlow AI operations layer <span>·</span> API v1 <span>·</span> Explainable by design</footer>
    </main>
  );
}
