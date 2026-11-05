# Architecture Essentials — PMS

A concise architectural reference for developers and AI agents. Read this first to understand the system quickly.

---

## System overview

PMS is a **backend-only** FastAPI API for managing academic research at **one university at a time**. It covers research proposals, projects, grants, publications, progress monitoring, approvals, notifications, files, audit, and retention. All data is partitioned by university (`university_id`). There is **no frontend**.

- Entry point: `backend/app/main:app`
- API prefix: `/api/v1` (37 routers, ~120 paths)
- Database: PostgreSQL, 60 tables, Alembic migrations (head `b1c2d3e4f5a6`)

---

## Technology stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI `>=0.115,<1` |
| ORM | SQLAlchemy `>=2.0,<3` |
| Driver | psycopg `>=3.2,<4` |
| Migrations | Alembic `>=1.13,<2` |
| Settings | pydantic-settings `>=2.0,<3` |
| Hashing | PBKDF2-HMAC-SHA256 (stdlib) |
| Tokens | Custom HMAC-SHA256 JWT-compatible (stdlib) |
| Tests | pytest + FastAPI TestClient |

See `backend/requirements.txt`.

---

## Critical architectural decisions

1. **Layered: routes → controllers → services → models.** Routes parse HTTP, controllers delegate (no DB), services own transactions + validation, models define schema.
2. **Tenant isolation by `university_id`.** Every tenant-scoped table and service query is filtered by `tenant.university_id`. Cross-tenant access returns 404.
3. **Composite foreign keys.** `(child_column, university_id) → (parent_column, parent.university_id)`, `ondelete="RESTRICT"`.
4. **Single transaction per service op.** `db.flush()` then one `db.commit()` — never multiple commits in one business operation.
5. **Role checks only on admin routes.** Domain routes enforce tenant isolation only (intentional).
6. **Custom HMAC tokens, no PyJWT.** Zero extra dependency. 24h expiry.
7. **`superadmin` not seeded.** Bypass exists in code but requires manual role assignment.
8. **Hard deletes + DB RESTRICT.** Structured delete guards on 4 domains only.

---

## Core application layers

```
Routes (backend/app/routes/)       HTTP input, call controllers
Controllers (backend/app/controller/)  Thin, no DB queries, serialize ORM→Pydantic
Services (backend/app/services/)   DB access, transactions, validation, business rules
Models (backend/app/models/)       SQLAlchemy 2.0 ORM, 60 tables
Core (backend/app/core/)           config, dependencies, exceptions, pagination, security
```

---

## Database principles

- 7 baseline tables use Integer PKs (`users`, `roles`, `user_roles`, `faculties`, `departments`, `student_profiles`, `staff_profiles`).
- 53 tenant tables use UUID PKs (`uuid4`) and carry `university_id`.
- All tables have `created_at`/`updated_at` (`TimestampMixin`, timezone-aware).
- Check constraints enforce status enums, amounts ≥ 0, date ordering, exclusive targets.
- Alembic head: `b1c2d3e4f5a6`. Test DB must be at head.
- **Never modify models or migrations without justification.**

---

## Tenant isolation rules

- Every tenant-scoped table has `university_id`.
- Every service query filters by `tenant.university_id`.
- `X-University-ID` header (or `university_id` query) is mandatory on scoped operations.
- Composite FKs enforce tenant consistency at the DB level.
- Cross-tenant lookups return 404 (never leak existence).
- `superadmin` bypasses membership check (global bypass).
- One deployment serves one university instance at a time (operational).

---

## Authentication and authorization principles

- **Auth:** Bearer token (HMAC-SHA256, verified by `security.decode_access_token`) or `X-User-Id` header. User must be `active`.
- **Tenant context:** `get_tenant_context` validates university, loads roles, checks membership (superadmin exempt).
- **Authz:** `require_roles(*codes)` on admin routes only (`universities`, `roles`, `permissions`, `users list`). Self-access to own profile always allowed.
- **Never bypass** `get_tenant_context` or `require_roles`.
- **Never return 403** for cross-tenant resources — use 404.

---

## Important relationships

| Entity | Key relationships |
|--------|-------------------|
| `universities` | Root tenant; `university_id` on all tenant tables |
| `users` | `user_roles`, `student_profiles`, `staff_profiles`, `memberships` |
| `roles` | Assigned to users per university via `user_roles` |
| `research_proposals` | → topics, departments, submitter; → revisions, participants, supervisors, reviews |
| `research_projects` | One-to-one with proposal (`proposal_id` unique); → milestones, supervisors, participants |
| `grant_applications` | → opportunities, applicant, optional project; → awards |
| `grant_awards` | One per application; → expenditures, grant progress reports, project allocations |
| `publications` | → authors (internal XOR external), projects, reviews |
| `approval_workflows` | → versions → steps → instances → actions |

---

## Non-negotiable architectural constraints

1. Do not bypass authorization or tenant isolation.
2. Do not modify database models or migrations without justification.
3. Do not introduce unnecessary dependencies.
4. Do not duplicate existing functionality.
5. Do not modify production semantics to satisfy tests.
6. Use `flush()` + single `commit()` in services (no multi-commit flows).
7. Static routes before dynamic routes on the same router.
8. Errors use `PMSException` hierarchy; never raw stack traces to clients.
9. All service methods are `@staticmethod`.
10. This is a backend-only project — no frontend code exists.

---

## Related documents

- `docs/architecture/ARCHITECTURE.md` — full architecture with diagrams
- `docs/architecture/DATABASE.md` — schema and relationships
- `docs/architecture/API.md` — endpoint conventions
- `docs/architecture/SECURITY.md` — auth/authz/tenant isolation
- `docs/product/USER_ROLES.md` — roles and permissions
- `AGENTS.md` — AI development instructions
