import { useState, type FormEvent } from "react";

export interface ScenarioFormProps {
  onSubmit: (payload: unknown, label: string) => Promise<void>;
  disabled?: boolean;
}

type VesselDraft = {
  vessel_id: string;
  vessel_name: string;
  eta: string;
  etd: string;
  teu_capacity: string;
  vessel_length_m: string;
  draft_m: string;
  required_cranes: string;
  cargo_type: string;
  priority: string;
};

const initialVessel: VesselDraft = {
  vessel_id: "LIVE-001",
  vessel_name: "",
  eta: "2026-01-01T04:00",
  etd: "2026-01-02T04:00",
  teu_capacity: "4200",
  vessel_length_m: "280",
  draft_m: "11.5",
  required_cranes: "3",
  cargo_type: "containers",
  priority: "priority",
};

function iso(value: string): string {
  return new Date(value).toISOString();
}

export function ScenarioForm({ onSubmit, disabled }: ScenarioFormProps) {
  const [vessels, setVessels] = useState<VesselDraft[]>([initialVessel]);
  const [windowStart, setWindowStart] = useState("2026-01-01T00:00");
  const [berthId, setBerthId] = useState("LIVE-B01");
  const [berthLength, setBerthLength] = useState("320");
  const [berthDepth, setBerthDepth] = useState("13");
  const [cranes, setCranes] = useState("4");
  const [yardCapacity, setYardCapacity] = useState("20000");
  const [yardFill, setYardFill] = useState("20");
  const [yardCargo, setYardCargo] = useState("containers");
  const [storm, setStorm] = useState(false);

  const updateVessel = (index: number, key: keyof VesselDraft, value: string) => {
    setVessels((current) => current.map((vessel, position) => (
      position === index ? { ...vessel, [key]: value } : vessel
    )));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const start = iso(windowStart);
    const payload = {
      scenario: {
        vessels: vessels.map((vessel) => ({
          ...vessel,
          vessel_name: vessel.vessel_name || undefined,
          eta: iso(vessel.eta),
          etd: iso(vessel.etd),
          teu_capacity: Number(vessel.teu_capacity),
          vessel_length_m: Number(vessel.vessel_length_m),
          draft_m: Number(vessel.draft_m),
          required_cranes: Number(vessel.required_cranes),
        })),
        berths: [{
          berth_id: berthId,
          berth_name: berthId,
          max_vessel_length_m: Number(berthLength),
          min_depth_m: Number(berthDepth),
          assigned_crane_count: Number(cranes),
        }],
        yard_zones: [{
          zone_id: "LIVE-Y01",
          zone_name: "Operational yard",
          cargo_type: yardCargo,
          capacity_teu: Number(yardCapacity),
          current_fill_pct: Number(yardFill),
          reefer_plug_count: 50,
        }],
        shocks: storm ? [{
          shock_id: "LIVE-STORM-01",
          shock_type: "storm",
          severity: "severe",
          start_time: start,
          end_time: new Date(new Date(start).getTime() + 9 * 3600000).toISOString(),
          arrival_rate_multiplier: 2,
          capacity_reduction_pct: 40,
          description: "Storm reduces berth handling capacity",
        }] : [],
      },
      window_start: start,
      window_end: new Date(new Date(start).getTime() + 72 * 3600000).toISOString(),
    };
    await onSubmit(payload, `User scenario (${vessels.length} vessel${vessels.length === 1 ? "" : "s"})`);
  };

  return (
    <section className="panel scenario-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">LIVE SCENARIO PLANNER</p>
          <h2>Describe your port situation</h2>
        </div>
        <span className="badge">Required inputs</span>
      </div>
      <form onSubmit={(event) => void submit(event)}>
        <div className="form-section">
          <h3>Planning window</h3>
          <label>Window start<input type="datetime-local" value={windowStart} onChange={(event) => setWindowStart(event.target.value)} required /></label>
        </div>
        {vessels.map((vessel, index) => (
          <div className="form-section" key={vessel.vessel_id}>
            <h3>Vessel {index + 1}</h3>
            <div className="form-grid">
              {([
                ["vessel_id", "Vessel ID", "text"],
                ["vessel_name", "Vessel name", "text"],
                ["eta", "ETA", "datetime-local"],
                ["etd", "ETD", "datetime-local"],
                ["teu_capacity", "TEU capacity", "number"],
                ["vessel_length_m", "Length (m)", "number"],
                ["draft_m", "Draft (m)", "number"],
                ["required_cranes", "Required cranes", "number"],
              ] as const).map(([key, label, type]) => (
                <label key={key}>{label}<input type={type} value={vessel[key]} onChange={(event) => updateVessel(index, key, event.target.value)} required={key !== "vessel_name"} min={type === "number" ? "0" : undefined} /></label>
              ))}
              <label>Cargo type<select value={vessel.cargo_type} onChange={(event) => updateVessel(index, "cargo_type", event.target.value)}><option>containers</option><option>reefer</option><option>bulk</option><option>vehicles</option><option>project_cargo</option></select></label>
              <label>Priority<select value={vessel.priority} onChange={(event) => updateVessel(index, "priority", event.target.value)}><option>standard</option><option>priority</option><option>critical</option></select></label>
            </div>
            {vessels.length > 1 && <button type="button" onClick={() => setVessels((current) => current.filter((_, position) => position !== index))}>Remove vessel</button>}
          </div>
        ))}
        <button type="button" onClick={() => setVessels((current) => [...current, { ...initialVessel, vessel_id: `LIVE-${String(current.length + 1).padStart(3, "0")}` }])}>+ Add vessel</button>
        <div className="form-section">
          <h3>Port capacity</h3>
          <div className="form-grid">
            <label>Berth ID<input value={berthId} onChange={(event) => setBerthId(event.target.value)} required /></label>
            <label>Berth max length (m)<input type="number" value={berthLength} onChange={(event) => setBerthLength(event.target.value)} min="1" required /></label>
            <label>Berth depth (m)<input type="number" value={berthDepth} onChange={(event) => setBerthDepth(event.target.value)} min="1" required /></label>
            <label>Available cranes<input type="number" value={cranes} onChange={(event) => setCranes(event.target.value)} min="1" required /></label>
            <label>Yard capacity (TEU)<input type="number" value={yardCapacity} onChange={(event) => setYardCapacity(event.target.value)} min="1" required /></label>
            <label>Current yard fill (%)<input type="number" value={yardFill} onChange={(event) => setYardFill(event.target.value)} min="0" max="100" required /></label>
            <label>Yard cargo type<select value={yardCargo} onChange={(event) => setYardCargo(event.target.value)}><option>containers</option><option>reefer</option><option>bulk</option><option>vehicles</option></select></label>
          </div>
          <label className="checkbox"><input type="checkbox" checked={storm} onChange={(event) => setStorm(event.target.checked)} /> Include a severe storm shock in the first 9 hours</label>
        </div>
        <button className="primary-action" type="submit" disabled={disabled}>{disabled ? "Planning..." : "Generate predicted Gantt chart"}</button>
      </form>
    </section>
  );
}
