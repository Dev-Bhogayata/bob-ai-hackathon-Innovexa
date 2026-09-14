import type { TimelineResponse } from "../types/api";

interface TimelineProps {
  data: TimelineResponse;
}

const HOUR_WIDTH = 48;

function hourOffset(value: string, start: string): number {
  return (
    (new Date(value).getTime() - new Date(start).getTime()) / 3_600_000
  );
}

export function Timeline({ data }: TimelineProps) {
  const ticks = Array.from({ length: 13 }, (_, index) => index * 6);
  return (
    <section className="panel timeline-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">72-hour berth plan</p>
          <h2>Vessel movement timeline</h2>
        </div>
        <span className="badge">{data.items.length} movements</span>
      </div>
      <div className="timeline-scroll">
        <div className="timeline-canvas" style={{ width: `${data.duration_hours * HOUR_WIDTH + 160}px` }}>
          <div className="timeline-axis">
            <span className="axis-label">BERTH</span>
            {ticks.map((tick) => (
              <span key={tick} style={{ left: `${160 + tick * HOUR_WIDTH}px` }}>
                +{tick}h
              </span>
            ))}
          </div>
          {data.berths.map((berth) => (
            <div className="timeline-row" key={berth}>
              <strong>{berth}</strong>
              <div className="lane">
                {data.items
                  .filter((item) => item.berth_id === berth)
                  .map((item) => {
                    const left = hourOffset(item.scheduled_start, data.window_start) * HOUR_WIDTH;
                    const width = Math.max(
                      64,
                      hourOffset(item.scheduled_end, item.scheduled_start) * HOUR_WIDTH,
                    );
                    return (
                      <div
                        className={`vessel-bar ${item.status}`}
                        key={item.vessel_id}
                        style={{ left: `${left}px`, width: `${width}px` }}
                        title={`${item.vessel_id} | ${item.priority} | ${item.wait_hours}h wait | cranes: ${item.crane_ids.join(", ")} | yard: ${item.yard_zone_id ?? "unassigned"} | shortfall: ${item.yard_capacity_shortfall_teu} TEU`}
                      >
                        <b>{item.vessel_id}</b>
                        <small>{item.wait_hours > 0 ? `${item.wait_hours}h wait` : "on time"}</small>
                      </div>
                    );
                  })}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="legend">
        <span><i className="legend-dot scheduled" /> Scheduled</span>
        <span><i className="legend-dot delayed" /> Waiting</span>
      </div>
    </section>
  );
}
