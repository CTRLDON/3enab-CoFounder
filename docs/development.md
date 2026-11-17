# Development

## Run without Docker

```bash
# Backend (Python 3.12+)
python -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements-dev.txt
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend (Node 20+)
cd frontend && npm install && npm run dev      # http://localhost:5173, proxies /api to :8000

# Model: Gemini (default) — export GEMINI_API_KEY=... before starting the backend
# or local Ollama:           export MODEL_PROVIDER=ollama && ollama pull qwen3.5:9b
```

Local data (SQLite database, runtime decision log, generated MVPs) goes to `data/`, which is git-ignored.

## Tests and checks

```bash
pytest                                   # backend: smoke, approval, gates, safety, commerce, research, theme, MVP
python evals/run_adversarial.py          # trick prompts through the real API
cd frontend && npm run typecheck && npm test && npm run build
```

`tests/fake_ollama.py` and `tests/test_gemini_gateway.py` replace only the network: the real gateways (structured output, retries, timeouts,
token accounting) runs against scripted HTTP responses.

## Repository map

| Path | What it holds |
|---|---|
| `backend/app/agents/` | One module per agent; `base.py` handles prompts, model calls, redaction and logging |
| `backend/app/workflows/` | `orchestrator.py`, `phases.py`, `gates.py`, `approval.py`, `state_machine.py` |
| `backend/app/services/` | Model gateway, research, policy guard, plan builder/versioning, MVP template, MOCKED commerce, palettes, audit log |
| `backend/app/demo/` | Scripted fixtures for the offline demo mode |
| `backend/app/api/` | HTTP routes (founders, ventures, debate, plan, phases, commerce, artifacts, audit, system) |
| `prompts/` | One system prompt per agent plus `shared_rules.md` |
| `frontend/src/` | `pages/`, `components/{chat,mindmap,business,phases,research,ui,layout}`, `hooks/`, `services/`, `types/` |
| `scripts/run_demo.py` | Produces `outputs/` and `decision_log.json` by driving the API |
| `evals/` | Adversarial prompt set and runner |

## Adding an agent

1. Add `prompts/<role>.md`.
2. Add an output schema to `backend/app/schemas/agent_io.py` (no fields that approve, pass gates or mark evidence VERIFIED).
3. Add `backend/app/agents/<role>.py` subclassing `BaseAgent`, with `name`, `prompt_file`, `tools`, `responsibility`.
4. Call it from a phase runner; persist its output as an artifact; add scripted fixtures for demo mode.
