# PMS — Claude Code Instructions

This is a lightweight entry point for Claude Code. It delegates to the shared
instructions in [`AGENTS.md`](../AGENTS.md), which is the single source of truth
for AI coding agents working on this repository.

## How to Use

When starting work on the PMS repository, read [`AGENTS.md`](../AGENTS.md) first.
It contains the complete set of instructions:

- Project overview and technology stack
- Project structure and architecture conventions
- Coding standards and database conventions
- API development conventions
- Authentication and authorization rules
- Multi-tenancy requirements
- Exception handling
- Testing requirements
- Security requirements
- Git workflow
- Development commands
- Things agents must never do

## Key Facts at a Glance

| Item | Value |
|------|-------|
| Entry point | `backend/app/main.py` |
| API prefix | `/api/v1` |
| Test command | `PMS_TEST_DATABASE_URL='postgresql+psycopg://apple@127.0.0.1:5433/pms_test_db' .venv/bin/python -m pytest backend/tests -q` |
| Run command | `uvicorn backend.app.main:app --reload` |
| Alembic head | `b1c2d3e4f5a6` |
| Python interpreter | `.venv/bin/python` |

## Never Do (from AGENTS.md)

- Never modify production semantics just to satisfy tests.
- Never modify database models or migrations without justification.
- Never introduce unnecessary dependencies.
- Never duplicate existing functionality.
- Never bypass authorization or tenant isolation.
- Never commit or push without explicit permission.

If a task requires changing the database schema, models, or migrations, treat it as
a justified architectural change and document it before implementing.
