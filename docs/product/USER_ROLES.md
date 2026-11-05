# PMS User Roles and Permissions

## Overview

PMS uses role-based access control (RBAC) for global administrative operations, combined with multi-tenant isolation for all domain operations. Roles are assigned to users within a specific university context.

## Role Model

| Table | Purpose |
|-------|---------|
| `roles` | Role definitions (id, code, name, description, is_active) |
| `user_roles` | Assigns a role to a user within a university (composite FK to `university_memberships`) |
| `permissions` | Permission definitions (id, code, description, is_active) |
| `role_permissions` | Junction table linking roles to permissions (role_id, permission_id) |

## Seeded Role Codes

Defined in `backend/app/models/seed.py` (`INITIAL_ROLE_CODES`). These are reference data and must be explicitly seeded via `seed_initial_roles(session)` — the helper is **not** called automatically on application startup.

| Role Code | Name | Typical Responsibilities |
|-----------|------|-------------------------|
| `student` | Student | Enrolled researcher; creates proposals, participates in projects, submits progress reports |
| `supervisor` | Supervisor | Academic staff; reviews proposals, supervises projects, approves milestones |
| `department_head` | Department Head | Manages departments, oversees departmental research activity |
| `research_admin` | Research Admin | Manages research topics, approval workflows, audit logs |
| `grant_admin` | Grant Admin | Creates grant opportunities, reviews applications, issues awards |
| `university_admin` | University Admin | Top-level administrator; manages users, roles, permissions, universities, system settings |

## Special Roles

### superadmin

- Referenced in `backend/app/core/dependencies.py` as a bypass for `require_roles()` checks.
- `TenantContext.has_role()` returns `True` if `"superadmin"` is in the user's roles.
- **Not seeded** — must be manually assigned via direct database insert if needed.
- Still requires tenant context (`get_tenant_context`) for university-scoped operations.

## Role Assignment

Roles are assigned through the User Roles (Tenant) API (`/api/v1/user-roles`):

- `POST /user-roles` — Assign a role to a user within a university (201).
- `GET /user-roles` — List user roles (paginated; filter by `user_id`, `role_id`, `active_only`).
- `POST /user-roles/{user_role_id}/revoke` — Revoke a user role (200).
- `DELETE /user-roles/{user_role_id}` — Delete a user role assignment (200).

### Constraints

- The user must have an active `UniversityMembership` in the target university.
- The assigner (if provided) must also have an active membership in that university.
- A user cannot have the same role actively assigned twice in the same university (partial unique index on `revoked_at IS NULL`).
- Revoking sets `revoked_at` rather than hard-deleting (soft revoke).

## Permission Model

Permissions are defined in the `permissions` table and linked to roles via `role_permissions`. Permission CRUD and role-permission assignment are restricted to `university_admin`:

- `POST /roles/permissions` — Create permission (201).
- `GET /roles/permissions` — List permissions (paginated).
- `POST /roles/permissions/assign` — Assign permission to role (201).
- `DELETE /roles/permissions/assignments/{assignment_id}` — Remove assignment (200).

## Authorization Enforcement

### Route-Level RBAC (`require_roles`)

Global administrative routes require the `university_admin` role:

| Route Group | Required Role |
|-------------|--------------|
| `GET /users` (list) | `university_admin` |
| `POST/GET/PUT/DELETE /roles` | `university_admin` |
| `POST/GET /roles/permissions` | `university_admin` |
| `POST/DELETE /roles/permissions/assign...` | `university_admin` |
| `POST/GET/PUT/DELETE /universities` | `university_admin` |

### Self-Access Exception

`GET/PATCH /users/{user_id}` allows a user to access their own profile without the `university_admin` role. Accessing another user's profile requires `university_admin`.

### Domain-Level Authorization

Domain routes (proposals, projects, grants, publications, etc.) rely on **tenant isolation**, not role-based checks:
- Every query is filtered by `tenant.university_id`.
- Cross-tenant access returns 404 (existence not leaked).
- No domain-level RBAC (e.g., `grant_admin` is not required to create grant awards).

This is an intentional design decision — domain-level RBAC would invent authorization rules not present in the seeded role semantics.

## Access Matrix

| Operation | student | supervisor | department_head | research_admin | grant_admin | university_admin | superadmin |
|-----------|---------|------------|-----------------|----------------|-------------|------------------|------------|
| Create proposal | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create project | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create grant opportunity | ❌ | ❌ | ❌ | ❌ | ✅* | ✅ | ✅ |
| Create role | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Create permission | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Create university | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| List users | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Access own profile | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Access another user's profile | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Cross-tenant access | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ (bypass) |

* `grant_admin` can create grant opportunities in practice (tenant-scoped), but the route is not role-restricted — any authenticated member of a university can create one. Domain-level RBAC is not implemented.

## Related Documents

- [`AGENTS.md`](../AGENTS.md) — Authorization rules
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Authorization architecture
- [`SECURITY.md`](SECURITY.md) — Authorization and multi-tenancy
- [`PRD.md`](../PRD.md) — User roles and permissions section
