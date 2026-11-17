# Mate — Your AI Co-Founder

Mate is an open-source team of AI agents that takes a founder from a rough idea toward a validated, sellable
digital product — and is willing to say "don't launch this" when the evidence is weak. A skeptical co-founder
agent challenges the idea, proposes a better-scoped direction the founder can approve or reject, and turns the
approved plan into an interactive business map. Specialised agents then work through six gated phases
(Discover, Validate, Build, Commercial setup, Launch, Operate). Gates are deterministic code; the founder approves
everything that matters; payments, publishing and delivery are MOCKED.

## Quickstart

```bash
docker compose up
```

Open **http://localhost:8080**. The API runs on http://localhost:8000 (interactive docs at `/docs`).

- **Live agents (default: Gemini API free tier).** Create a free key at https://aistudio.google.com/apikey, then
  `cp .env.example .env` and set `GEMINI_API_KEY=...` before `docker compose up`. Without a key, live ventures say
  the model is not configured — nothing is invented in its place.
- **Local open-weight model instead** (no key; nothing leaves your machine):
  `MODEL_PROVIDER=ollama docker compose --profile ollama up` starts Ollama and pulls `qwen3.5:9b`.
- **Look around immediately:** choose **Scripted demo** on the last onboarding step (or "Fill in the demo founder").
  Demo ventures use pre-written agent replies, are labelled *Scripted demo* everywhere, and still run the real
  gates, approvals, MVP build, MOCKED commerce and decision log.
- Needs Docker with the Compose v2 plugin; if `docker compose` is unknown, see `docs/troubleshooting.md`.
  All settings are documented in `.env.example`.

Regenerate the committed demo outputs and log: `python scripts/run_demo.py` (scripted) or
`python scripts/run_demo.py --mode live` (live model). Run the tests: `pytest` and `cd frontend && npm test`.

## What works and what is mocked

| Step | Status | Notes |
|---|---|---|
| Founder onboarding and saved profile | Working | Three short steps with progressive disclosure; stored in SQLite |
| Skeptical co-founder debate | Working | Live via the Gemini API free tier (default) or Ollama; scripted replies in demo mode (labelled) |
| Readiness checklist and opportunity comparison | Working | Model scores 12 criteria; the weighted index is computed in code and labelled heuristic |
| Proposal approve / reject | Working | Backend state machine; plans cannot be created without founder approval |
| Interactive business mind map | Working | React Flow; built from the stored plan; hover preview, detail panel, collapsible discussion |
| AI-negotiated node edits with versioning | Working | Founder approves each revision; optimistic version check; full history |
| Adaptive palette from the plan | Working | Palette follows the type of product; every token checked against WCAG AA in code |
| Phase 1 research (World Bank, Wikipedia) | Working | Free keyless sources; degrades to labelled UNKNOWN when offline (the committed run was offline) |
| Mom Test interview plan, Lean Canvas, experiments | Working | Targets locked before results; Mate never simulates interview answers |
| Landing page for the waitlist test | STUBBED | Draft page generated and previewed; never published, sign-up form disabled |
| Experiment results | Working | Entered by the founder; in demo mode entered as MOCKED and labelled |
| MVP build and tests | Working | Template-driven "offline records tool"; generated Node tests run under a fixed command |
| Pricing, break-even, draft policies | Working | Costs are labelled assumptions; break-even computed in code; policies marked DRAFT, not legal advice |
| Store page and launch posts | STUBBED | Drafts only; external publishing connectors do not exist; founder posts manually |
| Checkout, payment, payout | MOCKED | Synthetic orders and ledger; no provider, sandbox, card data or money |
| Delivery and refund with access revocation | MOCKED | Idempotent by event id; reconciliation report |
| Support triage | Working | Draft replies for the founder to send; in demo mode the ticket is MOCKED |
| Operating metrics | MOCKED | Demo metrics are synthetic and labelled as such |
| Persevere-or-pivot memo and Phase 6 gate | Working | Gate decides from recorded data; memo is advisory |
| Decision log and audit trail | Working | `decision_log.json` + in-app decision log |
| Model providers | Working | Gemini API and Ollama gateways, both tested against fake servers; switch with `MODEL_PROVIDER` |
| Streaming responses | STUBBED | Implemented and tested in the Ollama gateway only; the UI uses non-streamed structured calls |

## Architecture

A React + TypeScript frontend (Vite, React Flow, Tailwind) talks only to a FastAPI backend; the browser never
reaches the model provider. The backend's orchestrator sequences eleven agents — each with its own prompt file in `prompts/`,
a typed Pydantic output schema and an explicit tool list — through a 14-state venture state machine. All model
calls pass through one gateway that requests JSON-schema output, validates it, retries malformed answers and
reports failures instead of hiding them. Approvals, gates, evidence classification, MOCKED commerce and policy
checks are deterministic code, so no model answer can approve, validate or publish anything. Full design, phase
by phase, in [ARCHITECTURE.md](ARCHITECTURE.md).

## Models and free resources

- **Default live model: `gemini-2.5-flash` via the Gemini API free tier** (Google AI Studio key, no billing needed).
  Configure with `GEMINI_MODEL`. The key lives only in your untracked `.env`; it is sent in a request header and never
  logged or returned by the API. Free-tier limits apply (requests per minute and per day): Mate waits and retries on
  HTTP 429, then reports the limit instead of failing silently. Google's terms for the unpaid tier allow it to use
  prompts and responses to improve its products, so do not enter confidential information in live ventures.
- **Open-weight model: `qwen3.5:9b` via [Ollama](https://ollama.com)**, run locally with
  `MODEL_PROVIDER=ollama docker compose --profile ollama up`. Any Ollama model with structured output works
  (for example `qwen3:8b`). This path needs no key and sends nothing off your machine.
- `GET /api/system/status` shows the active provider and whether the key or model is ready.
- **No paid service is needed.** No API keys are committed.
- **Research sources (free, keyless):** World Bank Indicators API and the Wikipedia REST API. For Egypt-focused
  ventures Mate also lists CAPMAS, Central Bank of Egypt, GAFI, ITIDA, MCIT, World Bank and IMF pages for manual
  review; these are suggestions, never cited as retrieved evidence.
- **Everything else:** FastAPI, SQLAlchemy/SQLite, React, React Flow, Tailwind CSS, Lucide icons, Node's built-in test runner.

## Cost per run

**About $0.00 per run**: the Gemini API free tier and local Ollama inference have no per-call fee. The full demo (main
six-phase run plus the weak-idea run) makes 33 model calls with roughly 61k prompt tokens and 11k output tokens — an
estimate from prompt and output sizes at 4 characters per token, not a measured count. On the free tier the cost is
rate limits rather than money; with Ollama it is electricity and hardware, which are not metered per call. The scripted
demo mode uses no model tokens. Live runs log real token counts per agent call (Decision log → Agent runs).

## Demo video

Not recorded yet — a link (3 minutes at most) will be added here when the video exists.

## What our system will NOT do

- Promise income or success; income claims in model output are removed by a policy guard.
- Write reviews, testimonials, sign-ups or countdown timers, or inflate experiment results.
- Pose as the founder, a customer or another brand.
- Publish, send, spend or sign anything: external actions need founder approval *and* still are not executed,
  because no connectors exist in this build.
- Process payments of any kind — not even sandbox payments — or store passwords, card or bank details.
- Fall back silently: if the live model is unavailable or rate-limited, the step fails visibly and nothing advances.
- Treat an assumption as a fact: only sources Mate retrieved itself can be VERIFIED or ESTIMATE.
- Let a model change a gate result, approve a proposal or edit the plan without the founder.
- Help build excluded products: physical goods, financial, investment or crypto products, health or legal advice.
- Paywall any core feature.

## How the project stays alive after the hackathon

- **Maintainers:** the hackathon team keeps maintaining `main`; contributions go through pull requests with the test suite
  (`pytest`, `npm test`) and the adversarial evals (`python evals/run_adversarial.py`) required to pass.
- **Roadmap:** live research connectors beyond World Bank and Wikipedia, more MVP product classes, Alembic
  migrations, multi-user workspaces, Arabic interface, and real (founder-connected) publishing behind the existing
  approval gates — see the roadmap in ARCHITECTURE.md.
- **Community:** prompts, gate thresholds and palettes are plain files so that contributors can propose changes
  with evidence; templates and translations are the planned starting points for new contributors.
- **Funding:** MIT-licensed and free to self-host. Any future hosted version would charge only for hosting, never
  for core features.
# 3enab-CoFounder
