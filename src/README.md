# PortFlow source

The monorepo source lives under this directory to keep the submission
template's top-level structure intact.

- `backend/` contains the FastAPI application, Pydantic contracts, and backend tests.
- `frontend/` contains the React/Vite dashboard.
- `data/` generates seeded synthetic vessel and port data.
- `ml/`, `optimization/`, `rerouting/`, and `llm/` contain the decision modules.
- `agent/` wires the modules into the conditional agent pipeline.

Copy `.env.example` to `.env` only when local environment overrides are needed.
Never commit real credentials.
