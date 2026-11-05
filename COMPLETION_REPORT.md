# PMS Backend — Services, Controllers, and Routes Completion Report

## 1. What Antigravity Completed (prior session, baseline)

Antigravity audited and implemented the full PMS backend surface before this session:

- **12 domains wired** into `backend/app/routes/api.py` (37 included routers; 120 OpenAPI paths): users/auth, roles/permissions, user-roles (tenant), universities, memberships, settings, faculties, departments, leadership, staff, students, research topics, duplicates, research proposals, research projects, milestones/templates, progress reports, grant opportunities/applications/awards/expenditures/reports, publications, approvals, notifications/alerts, files/audit/retention.
- **All services, controllers, routes, schemas, and core infra** created (untracked): `backend/app/services/*`, `backend/app/controller/*`, `backend/app/routes/*`, `backend/app/schemas/*`, `backend/app/core/{dependencies,exceptions,pagination,security}.py`.
- Confirmed app boots successfully; baseline suite **43 passed, 0 failed**.
- Confirmed controllers contain no DB queries (pure delegation); services own transactions, FK/tenant validation, duplicate prevention.
- Identified the `roles_router` route-shadowing bug: `GET /{role_id}` declared before `/permissions`, causing `GET /api/v1/roles/permissions` to return 422.
- Identified missing delete guards on `ResearchTopic`, `Faculty`, `Department`, `GrantOpportunity`; multi-commit creation flows in proposals/projects/applications/approvals; missing field filters (`proposal_id`, `submitting_user_id`, `application_id`); missing RBAC on administrative global routes.

## 2. What Was Completed / Corrected (this session)

### 2.1 Route-ordering fix (bug correction)
`backend/app/routes/users.py`: Moved the permission endpoints (`POST/GET /permissions`, `POST /permissions/assign`, `DELETE /permissions/assignments/{id}`) to be declared **before** `/{role_id}` so the static `/permissions` path is no longer shadowed by the dynamic `/{role_id}` route. `GET /roles/permissions` now returns 200; `GET /roles/{id}` still returns 404 for unknown roles.

### 2.2 Targeted service delete guards
- `services/research_topics.py` — `delete_topic`: raises `SpecializedOperationError` (400) when proposals reference the topic.
- `services/organization.py` — `delete_faculty`: blocked when departments exist; `delete_department`: blocked when referenced by research proposals, research projects, staff profiles, student profiles, or department leadership assignments.
- `services/grants.py` — `delete_opportunity`: blocked when grant applications reference it.

### 2.3 Transaction consolidation (multi-commit → single `flush()` + one `commit()`)
- `services/research_proposals.py` `create_proposal`: proposal + initial status history in one transaction.
- `services/research_projects.py` `create_project`: project + initial status history in one transaction.
- `services/grants.py` `create_application`: application + initial status history in one transaction.
- `services/approvals.py` `create_workflow`: workflow + initial draft version in one transaction.
- (`create_award` already used a single commit; left as-is.)

### 2.4 Missing field filters & status validation
- `routes/research_projects.py` + `controller/research_projects.py` + `services/research_projects.py`: added `proposal_id` filter to `list_projects`.
- `routes/research_proposals.py` + `controller/research_proposals.py` + `services/research_proposals.py`: added `submitting_user_id` filter to `list_proposals`.
- `routes/grants.py` + `controller/grants.py` + `services/grants.py`: added `application_id` filter to `list_awards`.
- `schemas/research_projects.py` `ProjectStatusTransition.new_status`: pydantic pattern `^(active|on_hold|completed|cancelled|archived)$`.
- `schemas/research_proposals.py` `ProposalStatusTransition.new_status`: pydantic pattern `^(draft|submitted|under_review|revision_requested|approved|rejected|withdrawn)$`.

### 2.5 RBAC enforcement on administrative global routes
Added `require_roles("university_admin")` (superadmin bypasses via existing `has_role`) to:
- `routes/universities.py`: create/list/get/update/delete university.
- `routes/users.py` roles & permissions: create/list/get/update/delete role; create/list permission; assign/remove role-permission.
- `routes/users.py` users: `list_users` (admin-only); `get_user`/`update_user` allow self-access OR university-admin; `delete_user` admin-only.

Self-access is preserved (a user may read/update their own profile via `/users/{id}`); `/auth/me` remains open.

### 2.6 Test infrastructure updates
- `tests/conftest.py`: added `create_university_admin_helper()` (user + university + membership + `university_admin` role assignment) returning headers with `X-University-ID`; imported `Role`, `UserRole`.
- `tests/test_api_auth_and_security.py`: updated `test_users_crud_and_pagination` and `test_roles_and_permissions` to use the admin helper (required by new RBAC).

### 2.7 New tests (`tests/test_services_controllers_routes.py`, 19 tests)
- Route ordering: `/roles/permissions` returns 200 (not 422); `/roles/{missing}` returns 404.
- RBAC: non-admin denied on list-users, create-role, create-university, read-other-user; admin allowed; self-access allowed.
- Delete guards: topic-with-proposals blocked; topic-without-proposals allowed; faculty-with-departments blocked; department-with-profiles blocked; grant-opportunity-with-applications blocked; tenant isolation respected (cross-tenant delete → 404).
- Field filters: projects by `proposal_id`; proposals by `submitting_user_id`; awards by `application_id`.
- Status validation: invalid project status → 422 (schema pattern); valid transition → 200.
- Pagination envelope: `items`, `total`, `page`, `page_size`, `total_pages` consistent.

## 3. Intentional Exclusions and Why

- **Grant award / publication delete guards** (optional per scope): not added. Awards and publications already cascade via `passive_deletes=True` relationships; adding explicit guards was deemed optional and lower-risk to leave to the DB RESTRICT constraints.
- **RBAC on domain routes (proposals, projects, grants, etc.)**: intentionally not added. These already enforce tenant isolation via `university_id` scoping in every service query; adding role-based checks would invent new authorization rules not present in the seeded role semantics.
- **`superadmin` seeding**: not added. `superadmin` is referenced by `dependencies.py` but intentionally not in `seed.py` (per Antigravity's findings); roles remain reference data assigned by authorized workflow.
- **Model / migration changes**: none made. All fixes live in services/controllers/routes/schemas; no DDL or model edits required.
- **Soft-delete conversion**: not implemented. Existing services use hard `db.delete()` + `commit()`; soft deletion was not part of the accepted scope and would require model/migration changes.

## 4. Remaining Gaps

- Most `delete_*` operations across other domains (projects, proposals, applications, awards, milestones, etc.) still perform unguarded `db.delete()`. They are protected at the DB layer by RESTRICT foreign keys where applicable, but do not return a structured `SpecializedOperationError` message. Could be hardened incrementally.
- Domain-level RBAC (e.g., only `grant_admin` may create grant awards) is not enforced; authorization remains tenant-scoped via `university_id` plus the global admin routes above.
- `superadmin` role is not seeded, so the superadmin bypass in `dependencies.has_role`/`get_tenant_context` can only be exercised by manually assigning a `superadmin` role row.

## 5. Test Results

```
$ PMS_TEST_DATABASE_URL='postgresql+psycopg://apple@127.0.0.1:5433/pms_test_db' \
  .venv/bin/python -m pytest backend/tests -q
62 passed in 2.17s
```

- **Total: 62 passed, 0 failed.**
- Original 43 tests (auth/security, tenant isolation, models, schema integrity, postgres integrity) all still pass — no regressions.
- 19 new tests added in `tests/test_services_controllers_routes.py`.
- App imports and boots cleanly; all 37 routers / 120 OpenAPI paths remain mounted.

## 6. Architectural / Security Issues Found

1. **Route shadowing (fixed)** — `GET /{role_id}` declared before static `/permissions` caused `GET /api/v1/roles/permissions` to return 422 instead of 200. Reordered routes so static paths are registered first.
2. **Global admin routes had no role checks (fixed)** — `users`, `roles`, `permissions`, `universities` CRUD were open to any authenticated user. Added `require_roles("university_admin")` with self-access preservation for user read/update.
3. **Multi-commit creation flows (fixed)** — proposal, project, application, and workflow creation each committed the parent row before creating related history/version rows, risking orphaned rows on later failure. Consolidated into `flush()` + single `commit()`.
4. **Unguarded deletes (fixed for 4 domains)** — topic/faculty/department/grant-opportunity deletes had no reference checks, relying solely on DB RESTRICT constraints (which surface as raw 400s without a structured error code). Added `SpecializedOperationError` guards with clear messages.
5. **Schema status validation absent (fixed)** — `ProposalStatusTransition` and `ProjectStatusTransition` accepted arbitrary strings; DB check constraints would reject invalid statuses only at commit time. Added pydantic `pattern` validation (returns 422 early).
6. **Residual risk** — Many other `delete_*` endpoints remain unguarded; domain-level RBAC (role-scoped permissions per resource) is not implemented; `superadmin` is not seeded. These are intentional exclusions (see Section 3) rather than regressions.
