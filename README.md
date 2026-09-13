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
│   └── data/
│       └── generate_data.py  # Synthetic CSV/SQLite dataset generator
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