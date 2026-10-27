# Project Management System

University project management system built with FastAPI, SQLAlchemy, and PostgreSQL.

## Backend layout

The application lives under `backend/app`:

- `core`: application configuration
- `database`: SQLAlchemy engine and session dependency
- `models`: ORM models and metadata registry
- `schemas`: Pydantic request and response schemas
- `api`: HTTP routers
- `services`: application service logic

## Run the API

Set `DATABASE_URL` in the environment or a local `.env` file, then run:

```bash
uvicorn backend.app.main:app --reload
```

The health endpoint is available at `/health`.
