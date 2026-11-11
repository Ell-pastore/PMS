# Project Management System (PMS)

University project management system built with FastAPI, SQLAlchemy, and PostgreSQL.

PMS manages the full lifecycle of university research activities — student research proposals, projects, grants, publications, progress monitoring, and approval workflows — with multi-tenant (per-university) isolation, role-based access control, and comprehensive audit logging.

## Main Features

| Category | Features |
|----------|----------|
| Users & Authentication | Registration, login, profile management, password hashing, token auth |
| Roles & Permissions | Role/permission CRUD, role-permission assignment, tenant-scoped role assignment |
| Universities | University CRUD, memberships, system/department settings |
| Organization | Faculties, departments, leadership, staff/student profiles |
| Research Topics | Topic management, duplicate detection |
| Research Proposals | Full lifecycle (draft → submit → review → approve/reject), revisions, supervisors, reviews |
| Research Projects | Project creation from proposals, milestones, participants, supervisors, status tracking |
| Progress Reports | Report submission, comments, student activity tracking |
| Grants | Opportunities, applications, awards, allocations, expenditures, reports |
| Publications | Submission, verification workflow, authors, project links |
| Approvals | Versioned workflows, steps, instances, actions |
| Notifications & Alerts | Notifications, preferences, alert rules, alert events |
| Files, Audit & Retention | File metadata, document attachments, audit logs, retention policies |

See [`docs/product/FEATURES.md`](docs/product/FEATURES.md) for the complete feature reference.

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Web framework | FastAPI | `>=0.115,<1` |
| ASGI server | uvicorn | `>=0.30,<1` |
| ORM | SQLAlchemy | `>=2.0,<3` |
| Database driver | psycopg | `>=3.2,<4` |
| Migrations | Alembic | `>=1.13,<2` |
| Settings | pydantic-settings | `>=2.0,<3` |
| Validation | Pydantic v2 | — |

See `backend/requirements.txt` for the complete dependency list.

## Project Structure

```
PMS/
├── PRD.md                          # Product requirements document
├── AGENTS.md                       # AI development instructions (primary reference for agents)
├── CLAUDE.md                       # Claude Code entry point (delegates to AGENTS.md)
├── COMPLETION_REPORT.md            # Prior implementation completion report
├── README.md                       # This file
├── .env                            # DATABASE_URL
├── alembic.ini                     # Alembic configuration
├── alembic/
│   ├── env.py                      # Migration environment
│   ├── script.py.mako              # Migration template
│   └── versions/                   # 6 migration revisions (head: b1c2d3e4f5a6)
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── core/                   # config, dependencies, exceptions, pagination, security
│   │   ├── database/               # SQLAlchemy engine and session
│   │   ├── models/                 # ORM models and metadata registry
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── services/               # Application service logic (DB + business rules)
│   │   ├── controller/             # Controllers (delegation only, no DB queries)
│   │   ├── routes/                 # HTTP routers (aggregated in routes/api.py)
│   │   └── __init__.py
│   ├── tests/                      # Pytest test suite
│   └── requirements.txt
└── docs/
    ├── architecture/
    │   ├── ARCHITECTURE.md         # Full system architecture
    │   ├── ARCHITECTURE_ESSENTIALS.md  # Concise architectural reference
    │   ├── DATABASE.md             # Database schema and conventions
    │   ├── API.md                  # API endpoint reference
    │   └── SECURITY.md             # Security model and practices
    ├── product/
    │   ├── USER_ROLES.md           # Roles and permissions reference
    │   ├── FEATURES.md             # Feature reference
    │   └── WORKFLOWS.md            # Business workflows
    ├── prompts/
    │   └── PROMPT.md               # Prompt library index for AI agents
    └── pms_schema.dbml             # DBML schema diagram source
```

## Architecture Conventions

PMS follows a strict layered architecture:

```
Routes (HTTP, no DB) → Controllers (delegation, no DB queries) → Services (DB + business logic) → Models (ORM)
```

Key conventions:
- **Controllers contain no DB queries** — they delegate to services and serialize responses.
- **Services own transactions** — use `db.flush()` for IDs, then a single `db.commit()` per operation.
- **Tenant isolation** — every domain resource is scoped to `university_id`; cross-tenant access returns 404.
- **Composite foreign keys** — `(column, university_id)` references prevent cross-tenant orphan references.
- **Paginated envelope** — all list endpoints return `{ items, total, page, page_size, total_pages }`.
- **Structured errors** — `{ detail, error_code, error }` with no internals leaked.

See [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) and [`docs/architecture/ARCHITECTURE_ESSENTIALS.md`](docs/architecture/ARCHITECTURE_ESSENTIALS.md) for full details.

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 14+ database
- A virtual environment (`.venv` is used in this project)

### Setup

1. Clone the repository and navigate to the project root.

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. Configure the database URL. Create a `.env` file at the project root:
   ```bash
   DATABASE_URL=postgresql+psycopg://apple@127.0.0.1:5433/pms_db
   ```

   Or set the `DATABASE_URL` environment variable directly.

## Environment Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://user@host:port/db` |
| `PMS_TEST_DATABASE_URL` | Test database URL (must not be `pms_db`) | `postgresql+psycopg://apple@127.0.0.1:5433/pms_test_db` |
| `SECRET_KEY` | Token signing key (override the insecure default) | Set in production via environment |

The `.env` file is loaded by `pydantic-settings` via `backend/app/core/config.py`.

## Running the Application

```bash
# From the project root (preferred)
uvicorn backend.app.main:app --reload

# Alternative: run the app module directly (also from the project root)
python -m backend.app.main
```

> Note: `python backend/app/main.py` does not work because the application uses package-relative imports; run it as a module (`python -m backend.app.main`) or via uvicorn from the project root. If `python` is not the virtualenv interpreter, use `.venv/bin/python -m backend.app.main` or `.venv/bin/uvicorn backend.app.main:app --reload`.

The API will be available at `http://localhost:8000`. All API routes are mounted under `/api/v1`.

Health check:
```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

OpenAPI documentation (auto-generated):
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Database Setup and Migrations

PMS uses Alembic for schema management. The current migration head is `b1c2d3e4f5a6`.

```bash
# From the project root
alembic upgrade head      # Apply all migrations to the configured database
alembic current           # Show the current revision
alembic history           # Show migration history
alembic revision -m "msg" # Create a new migration
```

The migration environment (`alembic/env.py`) reads `DATABASE_URL` from the application settings (`backend/app.core.config.settings`).

### Test Database

Tests require a separate PostgreSQL test database at Alembic head. Configure `PMS_TEST_DATABASE_URL` (must not be `pms_db`):

```bash
export PMS_TEST_DATABASE_URL='postgresql+psycopg://apple@127.0.0.1:5433/pms_test_db'
```

Ensure the test database is at migration head:
```bash
PMS_TEST_DATABASE_URL='postgresql+psycopg://apple@127.0.0.1:5433/pms_test_db' alembic upgrade head
```

## Testing

PMS uses pytest with FastAPI's TestClient. Tests run against a live PostgreSQL test database with transactional rollback after each test.

```bash
# Run the full test suite
PMS_TEST_DATABASE_URL='postgresql+psycopg://apple@127.0.0.1:5433/pms_test_db' \
  .venv/bin/python -m pytest backend/tests -q

# Run a single test file
PMS_TEST_DATABASE_URL='postgresql+psycopg://apple@127.0.0.1:5433/pms_test_db' \
  .venv/bin/python -m pytest backend/tests/test_services_controllers_routes.py -q
```

Important:
- Always use `.venv/bin/python` (the system Python lacks dependencies).
- The test database must not be `pms_db` (conftest refuses the development database).
- The test database must be at Alembic head `b1c2d3e4f5a6` (conftest verifies this).

## Documentation

| Document | Path | Purpose |
|----------|------|---------|
| Product Requirements | `PRD.md` | Product overview, requirements, user roles, workflows |
| AI Development Instructions | `AGENTS.md` | Primary reference for AI coding agents |
| Claude Code Entry Point | `CLAUDE.md` | Delegates to AGENTS.md |
| System Architecture | `docs/architecture/ARCHITECTURE.md` | Full architecture reference |
| Architecture Essentials | `docs/architecture/ARCHITECTURE_ESSENTIALS.md` | Concise architectural reference |
| Database Reference | `docs/architecture/DATABASE.md` | Schema, constraints, migrations |
| API Reference | `docs/architecture/API.md` | Endpoint reference |
| Security Reference | `docs/architecture/SECURITY.md` | Auth, authorization, multi-tenancy |
| User Roles | `docs/product/USER_ROLES.md` | Roles, permissions, access matrix |
| Features | `docs/product/FEATURES.md` | Feature inventory by domain |
| Workflows | `docs/product/WORKFLOWS.md` | Business workflows and state transitions |
| Prompt Library | `docs/prompts/PROMPT.md` | Prompt-writing guidelines for AI agents |
| Schema Diagram | `docs/pms_schema.dbml` | DBML source for all 60 tables |

## Development Commands

```bash
# Run the API (development)
uvicorn backend.app.main:app --reload

# Run the API as a module
python -m backend.app.main

# Run the full test suite
PMS_TEST_DATABASE_URL='postgresql+psycopg://apple@127.0.0.1:5433/pms_test_db' \
  .venv/bin/python -m pytest backend/tests -q

# Run migrations
alembic upgrade head
alembic current
alembic history
```

## Contributing

AI coding agents should read [`AGENTS.md`](AGENTS.md) before making changes. Key rules:

- Never modify production semantics simply to satisfy tests.
- Never modify database models or migrations without justification.
- Never introduce unnecessary dependencies.
- Never duplicate existing functionality.
- Never bypass authorization or tenant isolation.
- Never commit or push without explicit permission.

## License

University project. See repository for licensing information.
