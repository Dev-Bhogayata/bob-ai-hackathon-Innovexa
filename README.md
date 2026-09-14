# PortFlow

**AI-assisted congestion prediction and port operations optimization**

## Team

Innovexa | AI track

## Problem Statement

Port shift supervisors must coordinate vessel arrivals, berth capacity, yard
space, and disruption events at the same time. Manual planning makes it hard
to see which berth will become a bottleneck and which intervention should
happen first.

## Solution

PortFlow combines a reproducible operational simulator, XGBoost delay
prediction, CP-SAT berth scheduling, explainable rerouting rules, and an LLM
briefing prompt. Its FastAPI contracts feed a React operations console with a
72-hour Gantt timeline and berth/yard hotspot heatmap.

## Key Features

- Seeded synthetic vessels, berths, yard zones, Poisson arrivals, and shock events
- XGBoost vessel-delay model with metrics and feature-importance artifact
- Constraint-safe OR-Tools berth assignment with a toy-case regression suite
- Rule-based alternate-port ranking using distance and available capacity
- React dashboard with the two judge-facing operational views
- Structured JSONL reasoning trace and Bob-assisted development log

## Tech Stack

Python, FastAPI, Pydantic, SQLite, OR-Tools CP-SAT, XGBoost, pandas,
scikit-learn, React, TypeScript, Vite, and IBM Bob-assisted development.

## How to Run

Follow the complete reproducible instructions in
[`docs/setup-guide.md`](docs/setup-guide.md).

## Demo

- Video: see `demo/demo-video-link.txt`
- Live deployment: see `demo/live-demo-url.txt`
- Screenshots: see `demo/screenshots/`

## Known Limitations

The training outcomes are synthetic placeholders and must be replaced with
observed port delay history before production use. The LLM integration creates
provider-neutral messages; a deployment still needs an approved model
provider and credentials. The demo currently runs locally rather than from a
deployed public URL.

## What We Are Most Proud Of

The optimization module was proven against a hand-checkable 3-vessel/2-berth
case before scaling to 50 vessels. The resulting assignments preserve vessel
compatibility and no-overlap constraints, while the API and UI make the
reasoning visible instead of hiding it behind a black box.

## Repository Layout

```text
.
├── submission.yaml
├── src/
│   ├── backend/       # FastAPI application, schemas, and tests
│   ├── frontend/      # React/Vite dashboard
│   ├── agent/         # Predict/optimize/route/summarize orchestration
│   ├── data/          # Synthetic data generator
│   ├── ml/            # XGBoost training
│   ├── optimization/  # CP-SAT berth assignment
│   ├── rerouting/     # Rule-based alternate ports
│   └── llm/           # Supervisor briefing prompt
├── docs/
├── demo/
└── presentation/
```
