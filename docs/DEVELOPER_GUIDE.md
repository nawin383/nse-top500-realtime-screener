# Developer Guide

## Setup

```bash
pip install -r requirements.txt
cd frontend && npm install
copy .env.example .env  # DATA_MODE=mock
uvicorn backend.app.main:app --reload  # terminal 1
npm run dev --prefix frontend           # terminal 2 -> http://localhost:5173
```

## Coding Standards

- Python: ruff + black (line 100), type hints, `loguru` JSON logs, no secrets in logs.
- TS/React: eslint `max-warnings 0`, functional components, hooks, tailwind.
- Commits: conventional `feat:`, `fix:`, `chore:`.
- Tests required for new engines; keep `pytest -v` green.

## Contributing

1. Branch `feat/<name>` from `main`.
2. Add tests in `backend/tests/test_*.py`.
3. Update `config/nse_top500.json` via `scripts/generate_universe.py` if tokens change.
4. PR triggers CI: pytest, npm build, snyk scan, docker ghcr.
5. Review needs 1 approval, CI green, no direct `main` push.

## Project Map

`backend/app/main.py` lifespan -> `services/data_engine.py` -> `providers/*` -> `market_state.py` -> WS `/ws/stream`.

## Adding a Screener

```python
# backend/app/screeners.py
SCREENERS["my_screen"] = lambda states, limit=20: sorted(states, key=lambda s: s.score, reverse=True)[:limit]
```

## Env Secrets

Never commit `.env`. CI uses `GITHUB_TOKEN` for GHCR, `SNYK_TOKEN` for scan.

## Release

Tag `vX.Y.Z` -> CI builds ghcr image, K8s rolling update via `kubectl set image`.
