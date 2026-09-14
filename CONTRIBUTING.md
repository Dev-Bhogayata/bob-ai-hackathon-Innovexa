# Contributing

This repository follows the Bobathon submission template. Keep application
source under `src/`, do not commit `.env`, `node_modules/`, `.venv/`, or build
artifacts, and update the relevant documentation when behavior changes.

Before opening a change, run:

```bash
python -m unittest discover -s src/backend/tests -p 'test_*.py' -v
cd src/frontend && npm run build
```
