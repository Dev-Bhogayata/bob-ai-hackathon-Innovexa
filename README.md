# PortFlow

AI-assisted congestion prediction and port operations optimization.

## Repository structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI route modules
│   │   ├── core/            # Settings and shared backend concerns
│   │   ├── db/              # SQLite connection and persistence layer
│   │   ├── ml/              # XGBoost prediction pipeline
│   │   ├── optimization/    # OR-Tools optimization models
│   │   ├── schemas/          # API request and response schemas
│   │   └── main.py           # FastAPI application entry point
│   └── tests/
│       ├── api/
│       ├── ml/
│       └── optimization/
├── src/
│   ├── data/
│       └── generate_data.py  # Synthetic CSV/SQLite dataset generator
│   └── scoring/
│       └── berth_scoring.py  # Explainable 0–100 berth baseline scorer
├── data/
│   ├── raw/                 # Source datasets
│   └── processed/           # Cleaned and feature-ready datasets
├── docs/
│   └── .gitkeep
├── frontend/
│   ├── public/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── services/
│       ├── types/
│       └── .gitkeep
├── scripts/
│   └── .gitkeep
├── .env.example
├── .gitignore
└── README.md
```

This repository is currently scaffolded for phased development. The directories
contain placeholders only; implementation will be added module by module.

## Generate synthetic data

```bash
python src/data/generate_data.py
```

The command writes `vessels.csv`, `berths.csv`, `yard_zones.csv`,
`shocks.csv`, `arrival_stream.csv`, and `portflow.db` to `data/generated/`.
Use `--seed` for reproducible data or `--output-dir` to choose another output
directory.

## Score berth pressure

After generating data, the baseline scorer can be imported with
`score_berths(berths, vessels, yard_zones, as_of=...)`. It returns one
explainable result per berth, sorted from highest to lowest score. Scores
combine 24-hour incoming TEU pressure (40%), active berth occupancy (30%), and
capacity-weighted yard fill (30%).

## Train the delay model

Install the ML dependencies and train the explainable baseline model:

```bash
pip install -r requirements.txt
python src/ml/train_delay_model.py
```

The command writes a native XGBoost model, synthetic historical outcomes,
validation metrics, and `data/models/feature_importance.png`. The training
outcomes are synthetic placeholders generated from the operational features;
replace them with observed vessel delay records before using the model for
real decisions.

## Optimize berth assignments

The CP-SAT optimizer in `src/optimization/berth_assignment.py` assigns each
vessel to a compatible berth, prevents schedule overlap, and minimizes
priority-weighted waiting time:

```python
from src.optimization.berth_assignment import optimize_berth_assignments

assignments = optimize_berth_assignments(vessels, berths)
```

It enforces vessel length, draft, and required-crane compatibility. The
hand-checkable 3-vessel/2-berth fixture is covered by
`backend/tests/optimization/test_berth_assignment.py`; the same model was
validated against all 50 generated vessels.

## Rank alternate ports

For a vessel whose predicted delay exceeds a threshold, use
`src/rerouting/alternate_ports.py` to rank up to three feasible alternate
ports. The rule-based score weights inverse distance at 60% and capacity
adequacy at 40%; ports with insufficient estimated TEU capacity are excluded.
Each result includes both component scores and a plain-language reason.

## Run the agent loop

`src/agent/portflow_loop.py` exposes callable `predict`, `optimize`, `route`,
and `summarize` tools and runs them in that order. `run_portflow_loop(...)`
returns every intermediate artifact plus a provider-neutral LLM prompt. Pass
`trace_path=Path("data/agent_trace.jsonl")` to write one JSON reasoning event
per step for demos and judge review.

For the API-facing conditional pipeline, use
`src/agent/orchestrator.py`. `orchestrate(...)` runs
`predict_congestion -> optimize_berths -> recommend_routing -> generate_plan`
for a supplied time window. Berth optimization runs only when a hotspot score
is above 70; alternate-port routing runs only when a vessel's predicted delay
is above 12 hours. Each step logs duration and JSON output size.

## Bob-assisted development log

Key prompts, design decisions, and validation milestones are recorded in
[`docs/dev-log.md`](docs/dev-log.md) for judging and project handoff.

```python
from src.agent.portflow_loop import run_portflow_loop

result = run_portflow_loop(
    vessels,
    berths,
    alternate_ports,
    predictor=my_delay_predictor,
    trace_path=Path("data/agent_trace.jsonl"),
)
```

## Generate a shift-supervisor briefing

`src/llm/shift_summary.py` converts the optimizer's structured assignment
output into provider-neutral system and user messages. Send those messages to
the LLM provider used by the application:

```python
from src.llm.shift_summary import build_shift_supervisor_prompt

messages = build_shift_supervisor_prompt(assignments)
```

The prompt requires strict JSON with a headline, current operating facts,
ranked berth risks, evidence-based reasons, recommended actions, and handoff
watch items. The helper performs no network calls and requires no API key.