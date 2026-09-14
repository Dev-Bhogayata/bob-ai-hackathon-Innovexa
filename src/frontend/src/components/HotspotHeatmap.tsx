import type { HotspotItem } from "../types/api";

interface HotspotHeatmapProps {
  items: HotspotItem[];
}

function scoreClass(score: number): string {
  if (score >= 70) return "heat-high";
  if (score >= 40) return "heat-medium";
  return "heat-low";
}

export function HotspotHeatmap({ items }: HotspotHeatmapProps) {
  return (
    <section className="panel heatmap-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Live pressure map</p>
          <h2>Operational hotspots</h2>
        </div>
        <span className="badge">24h horizon</span>
      </div>
      <div className="heatmap-grid">
        {items.map((item) => (
          <article className={`heat-cell ${scoreClass(item.score)}`} key={item.resource_id}>
            <div className="heat-cell-top">
              <span>{item.resource_type.toUpperCase()}</span>
              <strong>{item.score.toFixed(0)}</strong>
            </div>
            <h3>{item.label}</h3>
            <p>{item.factors.map((factor) => `${factor.name.replace(/_/g, " ")} ${factor.value.toFixed(0)}${factor.unit === "percent" ? "%" : ""}`).join(" · ")}</p>
            <small>{item.recommended_action}</small>
          </article>
        ))}
      </div>
    </section>
  );
}
