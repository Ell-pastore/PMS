# PMS Prompt Library Index

Reusable prompts for working with the PMS codebase using OpenCode, Claude Code, and Codex. This document explains how to use prompts with each agent and links to the shared instruction sources.

---

## How to use prompts with each agent

### OpenCode

OpenCode reads `AGENTS.md` at the repository root as its universal AI development instruction source. When starting a session, reference the repository and ask the agent to read `AGENTS.md`:

> "You are working on the PMS repository at /Users/apple/Desktop/PMS. First read AGENTS.md, then follow its conventions for all code changes."

OpenCode also supports skills (e.g., the `opencode` skill) for questions about OpenCode itself.

### Claude Code

Claude Code reads `CLAUDE.md` at the repository root, which is a lightweight entry point that references `AGENTS.md`:

> "Read CLAUDE.md and AGENTS.md in the repository root, then operate under those instructions for the PMS backend."

No Claude-specific instructions are duplicated in `CLAUDE.md`; all shared rules live in `AGENTS.md`.

### Codex

Codex does not auto-discover `AGENTS.md`. Pass the instructions explicitly in the system prompt or as context:

> System: You are working on the PMS (Project Management System) repository. Follow these instructions: [paste key sections of AGENTS.md: layered architecture routes→controllers→services, tenant isolation by university_id, PMSException error handling, never modify models/migrations without justification, never bypass authorization, never commit without permission].

Then reference the repository path:
> Workspace: /Users/apple/Desktop/PMS

---

## Prompt-writing guidelines (PMS-specific)

When writing prompts for PMS tasks, include these elements:

1. **Repository context** — "PMS backend, FastAPI + SQLAlchemy 2 + PostgreSQL, entry point `backend/app/main:app`, API prefix `/api/v1`."
2. **Instruction source** — "Follow `AGENTS.md` and `docs/architecture/ARCHITECTURE_ESSENTIALS.md`."
3. **Constraint reminders** — e.g., "Never modify database models or migrations without justification," "Never bypass `get_tenant_context` or tenant isolation," "Never commit or push without permission."
4. **Verification** — "Run the test suite: `PMS_TEST_DATABASE_URL='...' .venv/bin/python -m pytest backend/tests -q`. All 62 tests must pass."
5. **Scope** — Clearly state whether the task is documentation-only, a targeted bug fix, or a new endpoint; PMS is documentation-focused for this task.

### Example prompt (new endpoint)

> "Add a `GET /api/v1/research-proposals/{id}/summary` endpoint to PMS. Follow AGENTS.md: route → controller → service, service uses `db.flush()` + single `commit()`, all queries filter by `tenant.university_id`, errors use `PMSException` subclasses, static routes before dynamic. Add a test in `backend/tests/`. Run `PMS_TEST_DATABASE_URL='...' .venv/bin/python -m pytest backend/tests -q` and confirm 0 regressions. Do not modify models or migrations."

---

## Related documents

- `AGENTS.md` — universal AI development instructions (OpenCode / Claude Code / Codex source of truth)
- `CLAUDE.md` — Claude Code lightweight entry point (references AGENTS.md)
- `docs/architecture/ARCHITECTURE_ESSENTIALS.md` — concise architectural reference
- `docs/architecture/ARCHITECTURE.md` — full architecture
- `docs/architecture/DATABASE.md` — schema and relationships
- `docs/architecture/API.md` — endpoint conventions
- `docs/architecture/SECURITY.md` — auth/authz/tenant isolation
- `PRD.md` — product requirements
- `README.md` — project overview and setup
