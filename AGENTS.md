# PMS — AI Development Instructions

This file provides instructions for AI coding agents working on the PMS (Project Management System) repository. It preserves existing architectural decisions and conventions.

## 1. Project Overview

PMS is a **backend-only** university project management system built with FastAPI, SQLAlchemy, and PostgreSQL. It manages student research proposals, projects, grants, publications, progress monitoring, and approval workflows with multi-tenant (per-university) isolation.

- **Entry point**: `backend/app/main.py` — creates the FastAPI app, registers exception handlers, includes the v1 API router, exposes `/health`.
- **API root**: `/api/v1` (37 routers, ~120 OpenAPI paths across 12 domains).
- **Test command**: `PMS_TEST_DATABASE_URL='postgresql+psycopg://apple@127.0.0.1:5433/pms_test_db' .venv/bin/python -m pytest backend/tests -q`
- **Run command**: `uvicorn backend.app.main:app --reload` (requires `DATABASE_URL` in `.env` or environment).

## 2. Technology Stack

| Layer | Technology | Version Constraint |
|-------|-----------|-------------------|
| Web framework | FastAPI | `>=0.115,<1` |
| ASGI server | uvicorn | `[standard]>=0.30,<1` |
| ORM | SQLAlchemy | `>=2.0,<3` |
| Database driver | psycopg | `>=3.2,<4` |
| Migrations | Alembic | `>=1.13,<2` |
| Settings | pydantic-settings | `>=2.0,<3` |
| Password hashing | PBKDF2-HMAC-SHA256 (stdlib `hashlib`, `secrets`) | — |
| Tokens | Custom HMAC-SHA256 JWT-compatible (stdlib `hmac`, `base64`, `json`) | — |
| Validation | Pydantic v2 | — |
| Testing | pytest + FastAPI TestClient | — |

See `backend/requirements.txt` for the complete dependency list. **Do not install unnecessary packages.**

## 3. Project Structure

```
PMS/
├── PRD.md                          # Product requirements
├── AGENTS.md                       # AI development instructions (this file)
├── CLAUDE.md                       # Claude Code entry point
├── COMPLETION_REPORT.md            # Prior implementation completion report
├── README.md                       # Project overview and setup
├── .env                            # DATABASE_URL
├── alembic.ini                     # Alembic configuration
├── alembic/
│   ├── env.py                      # Migration environment
│   ├── script.py.mako              # Migration template
│   └── versions/                   # 6 migration revisions (head: b1c2d3e4f5a6)
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── core/
│   │   │   ├── config.py           # Settings (DATABASE_URL, app_name)
│   │   │   ├── dependencies.py     # get_db, get_current_user, get_tenant_context, require_roles
│   │   │   ├── exceptions.py       # PMSException hierarchy + FastAPI exception handlers
│   │   │   ├── pagination.py       # PaginationParams, PaginatedResponse, paginate()
│   │   │   └── security.py         # Password hashing, token create/decode
│   │   ├── database/
│   │   │   └── session.py          # SQLAlchemy engine, SessionLocal, get_db()
│   │   ├── models/
│   │   │   ├── __init__.py         # Model registry + seed helpers
│   │   │   ├── base.py             # Base, TimestampMixin
│   │   │   ├── seed.py             # INITIAL_ROLE_CODES, seed_initial_roles()
│   │   │   ├── User.py             # User, AccountStatus, AccountVerification
│   │   │   ├── role.py             # Role, UserRole, Permission, RolePermission
│   │   │   ├── university.py       # University, UniversityMembership
│   │   │   ├── (one file per domain table)
│   │   │   └── backup/             # Historical model backups (do not edit)
│   │   ├── schemas/
│   │   │   └── (one file per domain)
│   │   ├── services/
│   │   │   └── (one file per domain)
│   │   ├── controller/
│   │   │   └── (one file per domain)
│   │   ├── routes/
│   │   │   ├── api.py              # Router aggregation (prefix /api/v1)
│   │   │   └── (one file per domain)
│   │   └── __init__.py
│   ├── tests/
│   │   ├── conftest.py             # DB fixtures, test helpers
│   │   ├── test_api_auth_and_security.py
│   │   ├── test_api_tenant_isolation.py
│   │   ├── test_models.py
│   │   ├── test_postgres_integrity.py
│   │   ├── test_schema_integrity.py
│   │   └── test_services_controllers_routes.py
│   └── requirements.txt
└── docs/
    ├── architecture/
    │   ├── ARCHITECTURE.md
    │   ├── ARCHITECTURE_ESSENTIALS.md
    │   ├── DATABASE.md
    │   ├── API.md
    │   └── SECURITY.md
    ├── product/
    │   ├── USER_ROLES.md
    │   ├── FEATURES.md
    │   └── WORKFLOWS.md
    ├── prompts/
    │   └── PROMPT.md
    └── pms_schema.dbml             # DBML schema diagram source
```

## 4. Architecture Conventions

### Layered Architecture (strict)

```
Routes (HTTP) → Controllers (delegation only) → Services (DB + business logic) → Models (ORM)
```

- **Routes**: Parse HTTP request, call controller, return response. No DB queries.
- **Controllers**: Validate input, delegate to services, serialize ORM models to Pydantic schemas. **No DB queries.**
- **Services**: Own all database access, transactions, FK/relationship validation, duplicate prevention, tenant isolation, soft/hard deletion rules.
- **Models**: SQLAlchemy ORM definitions, table constraints, relationships.

### Request Flow

1. FastAPI route receives request.
2. `get_db` provides a SQLAlchemy session.
3. `get_current_user` resolves the user from Bearer token or `X-User-Id` header.
4. `get_tenant_context` resolves the university from `X-University-ID` header, loads roles, verifies membership.
5. `require_roles(...)` (optional) enforces role-based access on admin routes.
6. Controller → Service → DB.

### Transaction Rule

Services should use `db.flush()` to obtain generated IDs, then a single `db.commit()` at the end of a logical operation. Avoid multiple `db.commit()` calls within one business operation (prevents orphaned rows on partial failure).

### Naming Conventions

- Service classes: `<Domain>Service` (e.g., `ResearchProposalService`, `GrantAwardService`).
- Controller classes: `<Domain>Controller` (e.g., `ResearchProposalController`).
- Route routers: `<domain>_router` (e.g., `proposals_router`, `awards_router`).
- Schemas: `<Entity>Create`, `<Entity>Update`, `<Entity>Read`, `<Entity>Base`.
- Exception classes: `<Specific>Error` extending `PMSException`.

## 5. Coding Standards

- **Python**: Type hints required on all function signatures. Use `from __future__ import annotations`.
- **Imports**: Relative imports within `backend.app` (e.g., `from ..core.dependencies import ...`).
- **Docstrings**: All public modules, classes, and methods must have docstrings.
- **Pydantic**: Use `BaseModel` with `ConfigDict(from_attributes=True)` for read schemas.
- **No application code should be modified to make tests pass** — fix the code, not the test expectations.
- **Never duplicate existing functionality**: Check `services/`, `controller/`, `routes/`, `schemas/` before creating new files.
- **No unnecessary refactoring**: Make targeted, minimal changes.

## 6. Database Conventions

### Primary Keys

- **Integer PKs**: `users`, `roles`, `user_roles`, `faculties`, `departments`, `student_profiles`, `staff_profiles`.
- **UUID PKs**: All other 53 tables (default `uuid.uuid4`).

### Tenant Isolation (Critical)

- Every domain table has a `university_id` column.
- Cross-table foreign keys are **composite**: `(column, university_id)` references `(referenced_column, university_id)`.
- Every service query filters by `university_id` from `TenantContext`.
- Cross-tenant lookups return 404 (not 403) to avoid leaking resource existence.

### Timestamps

- `TimestampMixin` provides `created_at` (server default `now()`) and `updated_at` (server default `now()`, `onupdate=now()`).
- All timestamps are timezone-aware (`DateTime(timezone=True)`).

### Constraints

- PostgreSQL check constraints enforce status enums, amount non-negativity, date ordering, etc.
- Unique constraints include `university_id` where applicable (e.g., `uq_<table>_id_university`).
- Partial indexes enforce active-only uniqueness (e.g., one active lead per proposal).

### Migration Management

- Alembic is the single source of truth for schema changes.
- Current head: `b1c2d3e4f5a6`.
- Test database must be at alembic head (conftest verifies this).
- **Do not modify models or migrations unless genuinely necessary.**

## 7. API Development Conventions

### Router Registration

All routers are aggregated in `backend/app/routes/api.py` with prefix `/api/v1`.

### Endpoint Patterns

- `POST /` → create (201 Created)
- `GET /` → list (200, paginated envelope)
- `GET /{id}` → get (200, or 404)
- `PATCH/PUT /{id}` → update (200)
- `DELETE /{id}` → delete (200)
- `POST /{id}/action` → domain action (e.g., `/submit`, `/status`)

### Response Shapes

- Single object: the entity read schema.
- List: `PaginatedResponse[T]` with `items`, `total`, `page`, `page_size`, `total_pages`.
- Delete success: `{"status": "success", "message": "..."}`.

### Error Response Shape

All errors return JSON: `{ "detail": "...", "error_code": "...", "error": "<ExceptionClassName>" }`.

### Status Codes

- 200: Success (GET, PUT, PATCH, DELETE)
- 201: Created (POST)
- 400: Bad request / invalid input / FK violation / check constraint
- 401: Unauthorized (missing/invalid token)
- 403: Forbidden (insufficient role, inactive account, inactive tenant, cross-tenant membership)
- 404: Not found (including cross-tenant — existence not leaked)
- 409: Duplicate resource / unique constraint violation
- 422: Validation error (pydantic/schema)

### Route Ordering

Static routes must be declared **before** dynamic parameterized routes on the same router to avoid path shadowing (e.g., `/permissions` before `/{role_id}`).

## 8. Authentication and Authorization Rules

### Authentication

- `get_current_user`: Resolves user from `Authorization: Bearer <token>` or `X-User-Id` header.
- Tokens are custom HMAC-SHA256 JWT-compatible (not PyJWT). Created by `security.create_access_token()`, verified by `security.decode_access_token()`.
- Passwords: PBKDF2-HMAC-SHA256, 100,000 iterations, random salt.
- User must have `status == active` (otherwise 403).

### Authorization

- `get_tenant_context`: Requires `X-University-ID` header; verifies university exists and is active; loads active user roles for that university; verifies active `UniversityMembership` (superadmin exempt).
- `require_roles(*role_codes)`: FastAPI dependency factory; user must hold at least one of the listed roles, or be `superadmin`.
- **Admin routes** (`universities`, `roles`, `permissions`, `users list`) require `university_admin`.
- **Self-access**: `GET/PATCH /users/{id}` allows the user to access their own profile without admin role; accessing another user's profile requires `university_admin`.
- `superadmin` is referenced in code but **not seeded** — it must be manually assigned if needed.

### Never Do

- Never bypass `get_tenant_context` on university-scoped routes.
- Never return 403 for a resource that exists in another tenant (use 404 to avoid leaking existence).
- Never hardcode role checks in services; role checks belong in routes via `require_roles`.

## 9. Multi-Tenancy Requirements

- Every university-scoped endpoint requires `X-University-ID` header (or `university_id` query param).
- `get_tenant_context` validates the university, loads roles, and checks membership.
- All service-layer queries filter by `tenant.university_id`.
- Composite FKs enforce tenant scoping at the DB level.
- Test helpers: `make_auth_headers(user, university_id)` adds the `X-University-ID` header.

## 10. Exception Handling

### Exception Hierarchy (`core/exceptions.py`)

```
PMSException (base, 400)
├── NotFoundError (404)
├── DuplicateResourceError (409)
├── ForeignKeyViolationError (400)
├── InvalidInputError (400)
├── UnauthorizedError (401)
├── ForbiddenError (403)
├── DatabaseError (500)
└── SpecializedOperationError (400, configurable status_code)
```

### Handlers

- `PMSException` → structured JSON with `detail`, `error_code`, `error` (class name).
- `IntegrityError` → parsed by PostgreSQL SQLSTATE (23505 unique, 23503 FK, 23514 check, 23502 not-null).
- `SQLAlchemyError` → 500 `DATABASE_ERROR`.
- `Exception` → 500 `INTERNAL_SERVER_ERROR` (no internals leaked).

### Rules

- Services raise `PMSException` subclasses; controllers/routes do not catch them (global handlers handle them).
- Never return raw database exceptions to the client.
- Never leak stack traces or SQL internals.

## 11. Testing Requirements

### Test Configuration

- Test DB env var: `PMS_TEST_DATABASE_URL` (must NOT be `pms_db` — conftest refuses the dev database).
- Test DB must be at alembic head `b1c2d3e4f5a6` (conftest verifies).
- Fixtures: `postgres_engine` (session), `db_session` (transactional rollback), `client` (TestClient with `get_db` override).
- All DB changes in tests are rolled back after each test.

### Test Helpers (`conftest.py`)

- `create_user_helper(db, ...)` — creates a user.
- `create_university_helper(db, ...)` — creates a university.
- `create_membership_helper(db, university_id, user_id)` — creates membership.
- `make_auth_headers(user, university_id)` — Bearer token + optional X-University-ID.
- `create_university_admin_helper(db)` — user + university + membership + `university_admin` role.

### Running Tests

```bash
PMS_TEST_DATABASE_URL='postgresql+psycopg://apple@127.0.0.1:5433/pms_test_db' \
  .venv/bin/python -m pytest backend/tests -q
```

### Test Rules

- Use `.venv/bin/python` (system python lacks dependencies).
- Do not change production semantics just to pass tests.
- Add tests for new CRUD, search, filtering, pagination, authorization, tenant isolation, and invalid requests.
- Existing suite: 62 passed, 0 failed (do not regress).

## 12. Security Requirements

- Passwords: PBKDF2-HMAC-SHA256, 100k iterations (never plaintext).
- Tokens: HMAC-SHA256 signed, 24-hour expiry (never unsigned or never-expiring).
- `SECRET_KEY` default is insecure ("pms-insecure-development-secret-key-replace-in-prod") — must be changed in production via environment.
- All university-scoped routes require tenant context (authentication + membership).
- Role-based access on global admin routes (`require_roles`).
- Cross-tenant access returns 404 (no existence leakage).
- Structured error responses (no internals leaked).
- `superadmin` bypass exists but role is not seeded.

## 13. Git Workflow

- **Do not commit or push without explicit permission.**
- Work on feature branches off `main`.
- The repo was on `main`, up to date with `origin/main` at the last known state.

## 14. Development Commands

```bash
# Run the API (development)
uvicorn backend.app.main:app --reload

# Run tests
PMS_TEST_DATABASE_URL='postgresql+psycopg://apple@127.0.0.1:5433/pms_test_db' \
  .venv/bin/python -m pytest backend/tests -q

# Run a single test file
PMS_TEST_DATABASE_URL='postgresql+psycopg://apple@127.0.0.1:5433/pms_test_db' \
  .venv/bin/python -m pytest backend/tests/test_services_controllers_routes.py -q

# Alembic migrations (from repo root)
alembic upgrade head
alembic current
alembic history
```

## 15. Things Agents Must Never Do

1. **Never modify production semantics simply to satisfy tests.** Fix the code; if a test contradicts intended behavior, update the test only after confirming the test assumption is wrong.
2. **Never modify database models or migrations without justification.** Schema changes require alembic migrations and test DB updates.
3. **Never introduce unnecessary dependencies.** Use the existing stack; check `requirements.txt` first.
4. **Never duplicate existing functionality.** Check `services/`, `controller/`, `routes/`, `schemas/` before creating new files.
5. **Never bypass authorization or tenant isolation.** All university-scoped routes must use `get_tenant_context` and filter by `university_id`.
6. **Never commit or push without explicit permission.**
7. **Never return raw database exceptions or stack traces to clients.** Use the PMS exception hierarchy.
8. **Never create dynamic routes before static routes on the same router** (path shadowing).
9. **Never use multiple `db.commit()` calls within one business operation** in services; use `flush()` + single `commit()`.
10. **Never modify frontend code that doesn't exist** — this is a backend-only project.

## 16. Verification Checklist

Before considering a task complete:
- [ ] App imports cleanly: `.venv/bin/python -c "from backend.app.main import app; print('ok')"`
- [ ] Test suite passes: `PMS_TEST_DATABASE_URL=... .venv/bin/python -m pytest backend/tests -q`
- [ ] No new dependencies added
- [ ] No models or migrations changed (unless justified)
- [ ] No existing tests regressed
- [ ] Changes are minimal and targeted
- [ ] Authorization and tenant isolation preserved

## Related Documents

- [`PRD.md`](../PRD.md) — Product requirements
- [`docs/architecture/ARCHITECTURE.md`](../docs/architecture/ARCHITECTURE.md) — Full architecture
- [`docs/architecture/ARCHITECTURE_ESSENTIALS.md`](../docs/architecture/ARCHITECTURE_ESSENTIALS.md) — Concise reference
- [`docs/architecture/DATABASE.md`](../docs/architecture/DATABASE.md) — Database reference
- [`docs/architecture/API.md`](../docs/architecture/API.md) — API reference
- [`docs/architecture/SECURITY.md`](../docs/architecture/SECURITY.md) — Security reference
- [`docs/product/USER_ROLES.md`](../docs/product/USER_ROLES.md) — Roles and permissions
- [`docs/product/FEATURES.md`](../docs/product/FEATURES.md) — Feature reference
- [`docs/product/WORKFLOWS.md`](../docs/product/WORKFLOWS.md) — Workflow reference
- [`README.md`](../README.md) — Project overview and setup
