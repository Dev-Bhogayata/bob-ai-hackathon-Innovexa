# Setup guide

## Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer and npm
- Git
- A terminal and a browser

No external account or API key is required for the local demo.

For live watsonx.ai supervisor summaries, set `WATSONX_URL`,
`WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, and optionally `WATSONX_MODEL_ID` in
`.env`. Never commit the API key.

## Install

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp src/.env.example .env
cd src/frontend
npm install
cd ../..
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.

## Run

Open two terminals from the repository root.

Terminal 1:

```bash
source .venv/bin/activate
uvicorn src.backend.app.main:app --reload
```

Terminal 2:

```bash
cd src/frontend
npm run dev
```

Open the Vite URL shown in the terminal, normally
`http://localhost:5173`. The API docs are at
`http://127.0.0.1:8000/docs`.

## Verify

```bash
curl http://127.0.0.1:8000/health
curl 'http://127.0.0.1:8000/api/v1/timeline?start=2026-01-01T00:00:00%2B00:00&seed=42'
curl 'http://127.0.0.1:8000/api/v1/hotspots?as_of=2026-01-01T00:00:00%2B00:00&seed=42'
python -m unittest discover -s src/backend/tests -p 'test_*.py' -v
cd src/frontend && npm run build
```

## Optional data/model commands

```bash
python src/data/generate_data.py --seed 42
python src/ml/train_delay_model.py --seed 42
```

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `uvicorn: command not found` | Activate `.venv` and rerun `pip install -r requirements.txt`. |
| Frontend shows API error | Start the backend on port 8000 before `npm run dev`. |
| Port 8000 is busy | Stop the existing process or run `uvicorn ... --port 8001` and update the Vite proxy. |
| Native ML package install fails | Use Python 3.11+ on a supported 64-bit platform and recreate `.venv`. |
| No model artifact appears | Run `python src/ml/train_delay_model.py` explicitly; training artifacts are gitignored. |
