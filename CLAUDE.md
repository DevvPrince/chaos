# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**chaos** is a single-owner personal profile system: it stores the owner's data across life domains (body/health, education, finance, other) and exposes it as a knowledge base that AI agents can query. The owner communicates in Thai; code, specs, and commit messages are in English.

The repository is at the **pre-scaffold stage** — no code exists yet. Everything under "Target architecture" and "Commands" below is the agreed direction, not existing files. When you scaffold a part, replace the matching "target" text here with what actually exists, and correct anything that turned out differently.

- Remote: https://github.com/DevvPrince/chaos.git

## Workflow: spec-driven development (mandatory)

All features and behavior changes follow the project skill at `.claude/skills/spec-driven-development/` (invoke it via the Skill tool). Read its `SKILL.md` before starting any feature. Key points that apply here:

- `specs/` at the repo root is the catalog: one spec per feature (`<id>-<feature>`) and one per shared component (`<id>-component-<capability>`); `specs/README.md` holds the generated index. A change edits the owning spec, never a new "fix" spec.
- New spec IDs are random 7-char `[a-z0-9]`.
- Two human gates: Gate 1 (spec + plan + batches approved) before any code; Gate 2 (spec diff + code diff) at the end. Never write approvals into `SPEC.md` that the owner did not give.
- The orchestrator never writes tests or source itself; test writer, builder, and auditor are separate fresh-context runs. Builders never edit tests.
- Tests are tagged with `<specid>:REQ-NN` (pytest: `@pytest.mark.spec("<id>:REQ-01")` — register the `spec` marker in pytest config; Vitest/Playwright: `[<id>:REQ-01]` in the test title).

Traceability checker (the skill docs say `.agents/skills/...`; in this repo it lives under `.claude/skills/`):

```bash
python .claude/skills/spec-driven-development/scripts/check_spec_traceability.py
python .claude/skills/spec-driven-development/scripts/check_spec_traceability.py --write-index
```

## Target architecture

Monorepo of FastAPI microservices plus one web frontend:

| Path | Role |
| --- | --- |
| `apps/web` | Frontend: Next.js (App Router) + TypeScript, Tailwind + shadcn/ui, TanStack Query |
| `services/gateway` | Single public entrypoint: auth check, routing to domain services, aggregation for the web app |
| `services/identity` | Owner account, sessions/tokens, API keys for agents, consent/sharing scopes |
| `services/health` | Body: measurements, vitals, lab results, medical history, medications, sleep/exercise |
| `services/education` | Degrees, courses, certificates, skills, learning log |
| `services/finance` | Accounts, transactions, assets/liabilities, insurance, tax, budgets |
| `services/life` | "Other": goals, documents, contacts, preferences, timeline |
| `services/knowledge` | Agent-facing layer: consumes domain events, builds embeddings/summaries, semantic search, MCP server for agents |
| `packages/py-common` | Shared Python: settings, DB session, auth dependency, event schemas, logging |
| `packages/api-client` | TypeScript client generated from the services' OpenAPI specs |
| `infra/docker` | Dockerfiles + `compose.yaml` for local dev |
| `infra/terraform` | Modules and per-environment stacks |

Cross-cutting rules (intended — confirm in the first specs):

- **Each service owns its data** (own Postgres schema/DB, own Alembic migrations). No service reads another service's tables; it calls the API or consumes events.
- **Domain services emit change events**; `knowledge` is the only consumer that indexes them. Agents read through `knowledge` (search/MCP), never directly from domain DBs.
- **Agent access is scoped**: every agent API key carries per-domain read scopes enforced by `gateway`/`identity`; sensitive domains (health, finance) are off by default.
- Postgres with `pgvector` for embeddings; Python tooling is `uv` workspaces; JS tooling is `pnpm` workspaces.
- Each service follows the same internal layout (`app/api`, `app/domain`, `app/db`, `tests/`) so they can be built the same way.

## Commands (target — update once scaffolded)

```bash
docker compose -f infra/docker/compose.yaml up -d      # full local stack
uv sync                                                # install all Python workspaces
uv run --package <service> pytest                      # one service's tests
uv run --package <service> pytest path/to/test_x.py::test_name   # single test
uv run ruff check . && uv run ruff format --check . && uv run mypy .
pnpm install && pnpm --filter web dev                  # frontend dev server
pnpm --filter web test                                 # Vitest
terraform -chdir=infra/terraform/envs/<env> plan
```
