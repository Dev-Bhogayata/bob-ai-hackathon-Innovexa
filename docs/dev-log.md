# PortFlow development log

This log records the key Bob-assisted decisions behind PortFlow. It is
intended to make the application's technology choices and iteration history
visible during judging.

## 2026-09-13 — Repository scaffold

**Prompt:** Build PortFlow in phases and scaffold the repository first using
FastAPI, OR-Tools, XGBoost, React, and SQLite.

**Decision shaped by Bob:** Keep the concerns separated from the beginning:
`src/data`, `src/scoring`, `src/ml`, `src/optimization`, `src/rerouting`,
`src/llm`, `src/agent`, `src/backend`, and `src/frontend`, with backend tests
organized by capability.
Implementation was intentionally deferred until the structure was approved.

## 2026-09-13 — Synthetic operational data

**Prompt:** Generate 50 vessels, 8 berths, yard zones, a 30-day Poisson
arrival stream, and congestion shocks, saving both CSV and SQLite outputs.

**Decision shaped by Bob:** Make the dataset deterministic with a seed and
include explicit storm/equipment-breakdown events, capacity reduction, and
congestion fields. This gives every later module a reproducible demo dataset.

## 2026-09-13 — Explainable berth scoring

**Prompt:** Score each berth from 0–100 using incoming vessel volume, current
occupancy, and yard fill before adding ML.

**Decision shaped by Bob:** Use a transparent weighted baseline instead of
introducing a model prematurely: incoming TEU pressure 40%, occupancy 30%,
and capacity-weighted yard fill 30%. The output exposes each component so a
supervisor can understand the score.

## 2026-09-13 — Delay prediction

**Prompt:** Train XGBoost to predict vessel delay hours and generate a feature
importance chart for judges.

**Decision shaped by Bob:** Use an XGBoost regressor with synthetic historical
outcomes until real port outcomes are available. Save the native model,
metrics, historical training rows, and a PNG feature-importance chart. The
artifact explicitly marks outcomes as synthetic to avoid overstating validity.

## 2026-09-13 — Constraint optimization

**Prompt:** Build the hardest module against a tiny 3-vessel/2-berth case,
verify constraints by hand, and only then scale to 50 vessels.

**Decision shaped by Bob:** Implement CP-SAT berth assignment with explicit
length, draft, crane, ETA, and no-overlap constraints. The toy fixture became
the regression test before validating the same model against all 50 generated
vessels.

## 2026-09-13 — Rule-based rerouting

**Prompt:** Rank 2–3 alternate ports for vessels whose predicted delay exceeds
a threshold using distance and estimated capacity.

**Decision shaped by Bob:** Keep rerouting rule-based for a demo that is easy
to explain: exclude insufficient-capacity ports, then rank using 60% inverse
distance and 40% capacity adequacy. Each recommendation includes its evidence.

## 2026-09-13 — LLM supervisor briefing

**Prompt:** Feed optimizer JSON to an LLM prompt that explains what is
happening, which berths are at risk, and why.

**Decision shaped by Bob:** Keep the LLM boundary provider-neutral. The
application creates strict system/user messages and requests structured JSON
with a headline, operational facts, ranked risks, evidence, actions, and
handoff watch items. No API key or network call is required by the core logic.

## 2026-09-13 — Single agent loop

**Prompt:** Wire the capabilities as callable tools in one loop:
predict → optimize → route → summarize, with a reasoning trace.

**Decision shaped by Bob:** Expose ordinary Python callables and return all
intermediate artifacts. Each step emits a JSONL event containing timestamp,
inputs, outputs, rationale, and status so judges can see the decision path.

## 2026-09-13 — Conditional API orchestrator

**Prompt:** Create an orchestrator for a time window that predicts
congestion, optimizes only above hotspot score 70, routes only above 12 hours
of predicted delay, and generates a 72-hour supervisor plan.

**Decision shaped by Bob:** Add a backend-facing orchestration contract with
explicit threshold flags and per-step duration/output-size logs. This keeps
the eventual API and the planned 72-hour Gantt/heatmap frontend decoupled from
individual model implementations.

## Current demo story

The resulting flow demonstrates layered technology rather than a single
opaque model:

1. Synthetic port operations data establishes a reproducible scenario.
2. An explainable berth baseline and XGBoost delay model identify pressure.
3. CP-SAT enforces operational constraints.
4. Rules provide actionable alternate-port recommendations.
5. An LLM turns structured decisions into a supervisor briefing.
6. The agent trace makes every step inspectable for judges.
