# Solution overview

PortFlow is a layered decision-support system. A seeded simulator creates
vessel, berth, yard, arrival, and shock data. A baseline pressure scorer and
XGBoost model identify congestion and delay risk. OR-Tools CP-SAT then assigns
compatible vessels to berths without overlap while minimizing
priority-weighted wait. A simple alternate-port rule ranks feasible diversion
options by distance and available TEU capacity.

The final structured output is passed to a provider-neutral LLM prompt that
asks for a concise shift-supervisor briefing: what is happening, which
resources are at risk, the evidence, and the recommended action. The React
dashboard consumes stable FastAPI contracts to display the 72-hour Gantt and
hotspot heatmap.

The design favors explainability: every score exposes its factors, every
optimization result is constraint-checked, and every agent step can be logged
as JSONL for review.

For live operations, the API explicitly allocates crane IDs per berth and
checks vessel TEU against compatible yard-zone headroom. Supervisor summaries
can be sent through the IBM watsonx.ai adapter using environment-based
credentials; missing credentials fail clearly instead of silently returning a
mock response.
