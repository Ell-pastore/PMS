# PMS Database Reference

## Overview

PMS uses PostgreSQL as its primary database, accessed through SQLAlchemy 2.0 ORM. The schema consists of 60 tables organized into 12 domains. Alembic manages schema migrations (current head: `b1c2d3e4f5a6`).

## Connection

- **URL source**: `DATABASE_URL` environment variable or `.env` file (loaded via `backend/app/core/config.py`).
- **Example `.env`**: `DATABASE_URL=postgresql+psycopg://apple@127.0.0.1:5433/pms_db`
- **Test database**: `PMS_TEST_DATABASE_URL` (must not be `pms_db`; conftest refuses the dev database).
- **Engine**: `create_engine(url, pool_pre_ping=True)` in `backend/app/database/session.py`.
- **Session**: `sessionmaker(autoflush=False, autocommit=False, expire_on_commit=False)`.
- **Dependency**: `get_db()` yields a request-scoped session and closes it after the request.

## Table Inventory (60 tables)

| Domain | Tables | PK Type |
|--------|--------|---------|
| Core / Auth | users, roles, user_roles, permissions, role_permissions, account_verifications | int |
| Tenancy | universities, university_memberships, university_settings | uuid |
| Organization | faculties, departments, department_leadership, department_settings, staff_profiles, student_profiles | mixed |
| Research Topics | research_topics, duplicate_topic_candidates | uuid |
| Research Proposals | research_proposals, proposal_participants, proposal_supervisors, proposal_reviews, proposal_revisions, proposal_status_history | uuid |
| Research Projects | research_projects, project_participants, project_supervisors, project_milestones, milestone_templates, project_status_history, project_comments, student_activity | uuid |
| Progress Reports | progress_reports, progress_report_reviews | uuid |
| Grants | grant_opportunities, grant_applications, grant_application_participants, grant_application_reviews, grant_application_status_history, grant_awards, grant_project_allocations, grant_expenditures, grant_progress_reports | uuid |
| Publications | publications, publication_authors, publication_projects, publication_reviews | uuid |
| Approvals | approval_workflows, approval_workflow_versions, approval_workflow_steps, approval_instances, approval_actions | uuid |
| Notifications & Alerts | notifications, notification_preferences, alert_rules, alert_events | uuid |
| Files, Audit & Retention | stored_files, document_attachments, audit_logs, retention_policies | uuid |

## Primary Key Strategy

| PK Type | Tables |
|---------|--------|
| Integer | `users`, `roles`, `user_roles`, `faculties`, `departments`, `student_profiles`, `staff_profiles` |
| UUID (default `uuid.uuid4`) | All other 53 tables |

## Tenant Isolation (Composite Foreign Keys)

Every domain table has a `university_id` column. Cross-table foreign keys are **composite**: `(column, university_id)` references `(referenced_column, university_id)`, enforced with `ON DELETE RESTRICT`.

### Example: research_proposals → research_topics

```sql
FOREIGN KEY (topic_id, university_id)
  REFERENCES research_topics (id, university_id)
  ON DELETE RESTRICT
```

### Example: research_proposals → departments

```sql
FOREIGN KEY (department_id, university_id)
  REFERENCES departments (id, university_id)
  ON DELETE RESTRICT
```

### Example: research_proposals → university_memberships (submitter)

```sql
FOREIGN KEY (submitting_user_id, university_id)
  REFERENCES university_memberships (user_id, university_id)
  ON DELETE RESTRICT
```

### Unique Constraints with Tenant Scope

Most tables include a `UNIQUE (id, university_id)` constraint (e.g., `uq_research_proposals_id_university`) to prevent duplicate logical IDs across tenants.

## Timestamps

`TimestampMixin` (`backend/app/models/base.py`) is used by most tables:

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| `created_at` | `DateTime(timezone=True)` | `server_default=func.now()` | Set on insert |
| `updated_at` | `DateTime(timezone=True)` | `server_default=func.now()`, `onupdate=func.now()` | Set on insert, auto-updated on update |

All timestamps are timezone-aware.

## Check Constraints (Domain Rules Enforced in DB)

| Table | Constraint | Rule |
|-------|-----------|------|
| users | `account_status` | status IN ('active', 'inactive', 'suspended') |
| research_proposals | `ck_research_proposals_status` | status IN ('draft','submitted','under_review','revision_requested','approved','rejected','withdrawn') |
| research_proposals | `ck_research_proposals_submission` | submitted_at IS NULL OR status <> 'draft' |
| research_projects | `ck_research_projects_status` | status IN ('active','on_hold','completed','cancelled','archived') |
| research_projects | `ck_research_projects_dates` | expected_end_date IS NULL OR expected_end_date >= start_date |
| research_projects | `ck_research_projects_actual_end` | actual_end_date IS NULL OR actual_end_date >= start_date |
| grant_opportunities | `ck_grant_opportunities_status` | status IN ('draft','open','closed','awarded','cancelled') |
| grant_opportunities | `ck_grant_opportunities_dates` | application_closes_at >= application_opens_at |
| grant_opportunities | `ck_grant_opportunities_min_amount` | min_funding_amount >= 0 |
| grant_applications | `ck_grant_applications_status` | status IN ('draft','submitted','under_review','approved','rejected','withdrawn') |
| grant_applications | `ck_grant_applications_amount` | requested_amount >= 0 |
| grant_awards | `ck_grant_awards_status` | status IN ('active','closed','cancelled') |
| grant_awards | `ck_grant_awards_amount` | awarded_amount >= 0 |
| grant_awards | `ck_grant_awards_dates` | award_end_date >= award_start_date |
| grant_expenditures | `ck_grant_expenditures_status` | status IN ('draft','submitted','approved','rejected','paid','voided') |
| grant_expenditures | `ck_grant_expenditures_amount` | amount >= 0 |
| grant_progress_reports | `ck_grant_progress_reports_status` | status IN ('draft','submitted','under_review','revision_requested','approved','rejected') |
| grant_progress_reports | `ck_grant_progress_reports_period` | period_end >= period_start |
| publications | `ck_publications_status` | status IN ('draft','submitted','under_verification','verified','rejected','withdrawn') |
| project_milestones | `ck_project_milestones_status` | status IN ('pending','in_progress','submitted','approved','revision_requested','overdue','completed','cancelled') |
| project_milestones | `ck_project_milestones_completed` | completed_at IS NULL OR status = 'completed' |
| project_supervisors | `ck_project_supervisors_role` | assignment_role IN ('primary','co_supervisor') |
| project_supervisors | `ck_project_supervisors_dates` | ended_at IS NULL OR ended_at >= started_at |
| proposal_supervisors | `ck_proposal_supervisors_role` | assignment_role IN ('primary','co_supervisor') |
| proposal_reviews | `ck_proposal_reviews_decision` | decision IN ('approved','rejected','revision_requested','commented') |
| progress_reports | `ck_progress_reports_status` | status IN ('draft','submitted','under_review','revision_requested','approved','rejected') |
| progress_reports | `ck_progress_reports_period` | period_end >= period_start |
| student_profiles | `ck_student_profiles_account_status` | status IN ('active','inactive','graduated','suspended') |
| student_profiles | `ck_student_profiles_gender` | gender IN ('female','male','non_binary','undisclosed') |
| staff_profiles | `ck_staff_profiles_gender` | gender IN ('female','male','non_binary','undisclosed') |
| approval_workflow_versions | `ck_approval_workflow_versions_publication_state` | publication_state IN ('draft','published') |
| approval_instances | `ck_approval_instances_status` | status IN ('pending','in_progress','approved','rejected','cancelled') |
| alert_events | `ck_alert_events_severity` | severity IN ('info','warning','critical') |
| alert_events | `ck_alert_events_status` | status IN ('active','acknowledged','resolved','dismissed') |
| retention_policies | `ck_retention_policies_action` | post_retention_action IN ('review','archive','anonymize','delete') |
| notification_preferences | `ck_notification_preferences_channel` | channel = 'in_app' |

## Indexes

### Tenant-Scoped Unique Indexes (most tables)

Pattern: `uq_<table>_id_university` on `(id, university_id)`.

### Domain-Specific Indexes

| Table | Index | Columns | Purpose |
|-------|-------|---------|---------|
| research_proposals | `ix_research_proposals_department_status` | (department_id, status) | Filter proposals by department + status |
| research_projects | `ix_research_projects_department_status` | (department_id, status) | Filter projects by department + status |
| research_topics | `ix_research_topics_department_status` | (department_id, is_active) | Filter topics by department + active |
| research_topics | `ix_research_topics_normalized_title` | (normalized_title) | Duplicate topic detection |
| grant_applications | `ix_grant_applications_opportunity_status` | (opportunity_id, status) | List applications by opportunity + status |
| grant_expenditures | `ix_grant_expenditures_award_date` | (award_id, expenditure_date) | Expenditures by award + date |
| progress_reports | `ix_progress_reports_project_period` | (project_id, period_start, period_end) | Reports by project + period |
| publications | `ix_publications_status_date` | (verification_status, publication_date) | Publications by status + date |
| stored_files | `ix_stored_files_uploader_created` | (uploader_id, created_at) | Files by uploader |
| notifications | `ix_notifications_recipient_created` | (recipient_id, created_at) | Notifications by recipient |
| notifications | `ix_notifications_recipient_unread_created` | (recipient_id, read_at, created_at) | Unread notifications |
| user_roles | `ix_user_roles_role_id` | (role_id) | Look up user_roles by role |
| audit_logs | `ix_audit_logs_entity_integer_event` | (entity_type, entity_integer, event_at) | Audit by integer entity |
| audit_logs | `ix_audit_logs_entity_uuid_event` | (entity_type, entity_uuid, event_at) | Audit by UUID entity |
| audit_logs | `ix_audit_logs_request_id` | (request_id) | Audit by request ID |

### Partial Indexes (PostgreSQL-specific)

| Table | Index | Predicate | Purpose |
|-------|-------|-----------|---------|
| user_roles | `uq_user_roles_active_assignment` | `revoked_at IS NULL` | One active role assignment per user/role/university |
| project_participants | `uq_project_participants_active_student` | `ended_at IS NULL` | One active participation per student/project |
| project_participants | `uq_project_participants_active_lead` | `is_lead = true AND ended_at IS NULL` | One active lead per project |
| project_supervisors | `uq_project_supervisors_active_staff` | `ended_at IS NULL` | One active supervision per staff/project |
| project_supervisors | `uq_project_supervisors_primary_active` | `assignment_role = 'primary' AND ended_at IS NULL` | One active primary supervisor per project |
| proposal_supervisors | `uq_proposal_supervisors_active` | `ended_at IS NULL` | One active supervision per staff/proposal |
| proposal_supervisors | `uq_proposal_supervisors_primary_active` | `assignment_role = 'primary' AND ended_at IS NULL` | One active primary supervisor per proposal |
| proposal_participants | `uq_proposal_participants_lead` | `is_lead = true` | One lead per proposal |
| publication_authors | `uq_publication_authors_corresponding` | `is_corresponding = true` | One corresponding author per publication |
| publications | `uq_publications_normalized_doi` | `normalized_doi IS NOT NULL` | Unique DOI |
| retention_policies | `uq_retention_policies_university_category_global` | `department_id IS NULL` | One global policy per category/university |
| retention_policies | `uq_retention_policies_university_category_department` | `department_id IS NOT NULL` | One dept policy per category/university |
| department_leadership | `uq_department_leadership_active` | `ended_at IS NULL` | One active leader per department |
| alert_rules | `uq_approval_workflows_department_scope` | `department_id IS NOT NULL` | One workflow per type/department/university |
| alert_rules | `uq_approval_workflows_university_scope` | `department_id IS NULL` | One workflow per type/university (global scope) |

## Alembic Migrations

| File | Revision | Description |
|------|----------|-------------|
| `3a5bb0b54636_create_initial_schema.py` | Initial | Initial schema creation |
| `7f2e6e8c4a91_complete_current_schema.py` | Complete schema | Additional tables |
| `b1c2d3e4f5a6_remove_duplicate_unique_constraints.py` | HEAD | Removed duplicate unique constraints |
| `c4d6e8f0a1b2_split_audit_entity_identifiers.py` | — | Split audit entity identifiers |
| `e7f9a1c3b5d7_add_notification_preferences.py` | — | Added notification_preferences table |

### Migration Commands

```bash
# From repo root
alembic upgrade head        # Apply all migrations
alembic current             # Show current revision
alembic history             # Show migration history
alembic revision -m "msg"   # Create a new migration
```

## Test Database

- Environment variable: `PMS_TEST_DATABASE_URL`
- Must NOT be `pms_db` (development database) — conftest enforces this.
- Must be at Alembic head `b1c2d3e4f5a6` — conftest verifies this.
- Tests use transactional rollback: each test runs in a transaction that is rolled back afterward.
- All 60 tables exist in the test database.

### Example Test Run

```bash
PMS_TEST_DATABASE_URL='postgresql+psycopg://apple@127.0.0.1:5433/pms_test_db' \
  .venv/bin/python -m pytest backend/tests -q
```

## Schema Diagram Source

`docs/pms_schema.dbml` contains a DBML representation of all 60 tables and their foreign key relationships, generated from `Base.metadata`. Note: DBML cannot represent PostgreSQL triggers/functions, ORM event guards, partial-index predicates, server-side trigger behavior, or Alembic migration history.

## Related Documents

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Full system architecture
- [`ARCHITECTURE_ESSENTIALS.md`](ARCHITECTURE_ESSENTIALS.md) — Concise reference
- [`AGENTS.md`](../AGENTS.md) — AI development instructions (database conventions section)
- [`PRD.md`](../PRD.md) — Product requirements
