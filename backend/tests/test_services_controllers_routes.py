"""Tests for service/controller/route fixes: RBAC, delete guards, field filters,
route ordering, status validation, and pagination envelope."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models import Role, UserRole
from backend.tests.conftest import (
    assign_role_helper,
    create_membership_helper,
    create_university_admin_helper,
    create_university_helper,
    create_user_helper,
    make_auth_headers,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_faculty(client, headers, name, code):
    resp = client.post(
        "/api/v1/faculties",
        json={"name": name, "code": code, "is_active": True},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_department(client, headers, faculty_id, name, code):
    resp = client.post(
        "/api/v1/departments",
        json={"name": name, "code": code, "faculty_id": faculty_id, "is_active": True},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_research_topic(client, headers, department_id, title):
    resp = client.post(
        "/api/v1/research-topics",
        json={"title": title, "department_id": department_id},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_research_proposal(client, headers, topic_id, department_id, title="Proposal"):
    resp = client.post(
        "/api/v1/research-proposals",
        json={
            "title": title,
            "topic_id": str(topic_id),
            "department_id": department_id,
            "abstract": "abstract",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_research_project(client, headers, proposal_id, department_id, title="Project"):
    resp = client.post(
        "/api/v1/research-projects",
        json={
            "title": title,
            "proposal_id": str(proposal_id),
            "department_id": department_id,
            "start_date": "2025-01-01",
            "status": "active",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_grant_opportunity(client, headers):
    resp = client.post(
        "/api/v1/grant-opportunities",
        json={
            "title": "Grant Opp",
            "funding_organization": "Org",
            "application_opens_at": "2025-01-01T00:00:00Z",
            "application_closes_at": "2025-12-31T00:00:00Z",
            "min_funding_amount": 1000,
            "currency": "USD",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_grant_application(client, headers, opportunity_id):
    resp = client.post(
        "/api/v1/grant-applications",
        json={
            "opportunity_id": str(opportunity_id),
            "title": "App",
            "proposal": "proposal text",
            "requested_amount": 5000,
            "currency": "USD",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _seed_university_admin_role(db: Session, university_id, user_id):
    """Ensure university_admin role exists and is assigned to the user."""
    role = db.scalar(
        __import__("sqlalchemy", fromlist=["select"]).select(Role).where(Role.code == "university_admin")
    ) if False else db.scalar(
        __import__("sqlalchemy").select(Role).where(Role.code == "university_admin")
    )
    # Simpler: query directly
    from sqlalchemy import select as _select
    role = db.scalar(_select(Role).where(Role.code == "university_admin"))
    if not role:
        role = Role(code="university_admin", name="University Admin")
        db.add(role)
        db.flush()
    db.add(UserRole(university_id=university_id, user_id=user_id, role_id=role.id))
    db.commit()


# ---------------------------------------------------------------------------
# Route ordering fix: /permissions not shadowed by /{role_id}
# ---------------------------------------------------------------------------

def test_permissions_endpoint_not_shadowed(client: TestClient, db_session: Session):
    admin, _, headers = create_university_admin_helper(db_session)
    # Before the fix, GET /api/v1/roles/permissions returned 422 (shadowed by /{role_id}).
    resp = client.get("/api/v1/roles/permissions", headers=headers)
    assert resp.status_code == 200, resp.text
    assert "items" in resp.json()

    # GET /roles/{role_id} still returns 404 for a missing role (not treated as permissions).
    resp = client.get("/api/v1/roles/9999999", headers=headers)
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# RBAC authorization on administrative global routes
# ---------------------------------------------------------------------------

def test_non_admin_cannot_list_users(client: TestClient, db_session: Session):
    user, univ, headers = create_university_admin_helper(db_session)
    # Downgrade the user to a plain member (no university_admin role).
    from sqlalchemy import select as _select
    db_session.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.university_id == univ.id,
    ).delete()
    db_session.commit()

    resp = client.get("/api/v1/users", headers=headers)
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"] == "ForbiddenError"


def test_admin_can_list_users(client: TestClient, db_session: Session):
    _, _, headers = create_university_admin_helper(db_session)
    resp = client.get("/api/v1/users", headers=headers)
    assert resp.status_code == 200, resp.text
    assert "items" in resp.json()


def test_non_admin_cannot_create_role(client: TestClient, db_session: Session):
    user, univ, headers = create_university_admin_helper(db_session)
    from sqlalchemy import select as _select
    db_session.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.university_id == univ.id,
    ).delete()
    db_session.commit()

    resp = client.post(
        "/api/v1/roles",
        json={"code": f"ROLE_{uuid.uuid4().hex[:6]}", "name": "Nope Role"},
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


def test_self_access_allowed_for_own_user(client: TestClient, db_session: Session):
    admin, _, headers = create_university_admin_helper(db_session)
    # A user can read their own profile without being university_admin (self-access).
    resp = client.get(f"/api/v1/users/{admin.id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == admin.id


def test_other_user_requires_admin(client: TestClient, db_session: Session):
    admin, univ, headers = create_university_admin_helper(db_session)
    other = create_user_helper(db_session)
    create_membership_helper(db_session, univ.id, other.id)
    other_headers = make_auth_headers(other, univ.id)
    # other has no university_admin role → cannot read admin's profile.
    resp = client.get(f"/api/v1/users/{admin.id}", headers=other_headers)
    assert resp.status_code == 403, resp.text


def test_non_admin_cannot_create_university(client: TestClient, db_session: Session):
    user, univ, headers = create_university_admin_helper(db_session)
    from sqlalchemy import select as _select
    db_session.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.university_id == univ.id,
    ).delete()
    db_session.commit()

    resp = client.post(
        "/api/v1/universities",
        json={"name": "New Univ", "code": "NEW", "is_active": True},
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# Delete guards
# ---------------------------------------------------------------------------

def test_delete_topic_with_proposals_blocked(client: TestClient, db_session: Session):
    admin, univ, headers = create_university_admin_helper(db_session)
    faculty = _create_faculty(client, headers, "Faculty Del", f"FD-{uuid.uuid4().hex[:4].upper()}")
    dept = _create_department(client, headers, faculty["id"], "Dept Del", f"DD-{uuid.uuid4().hex[:4].upper()}")
    topic = _create_research_topic(client, headers, dept["id"], "Topic To Protect")
    _create_research_proposal(client, headers, topic["id"], dept["id"], "Proposal Using Topic")

    resp = client.delete(f"/api/v1/research-topics/{topic['id']}", headers=headers)
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"] == "SpecializedOperationError"

    # Topic still exists.
    resp_check = client.get(f"/api/v1/research-topics/{topic['id']}", headers=headers)
    assert resp_check.status_code == 200


def test_delete_topic_without_proposals_allowed(client: TestClient, db_session: Session):
    admin, univ, headers = create_university_admin_helper(db_session)
    faculty = _create_faculty(client, headers, "Faculty Ok", f"FO-{uuid.uuid4().hex[:4].upper()}")
    dept = _create_department(client, headers, faculty["id"], "Dept Ok", f"DO-{uuid.uuid4().hex[:4].upper()}")
    topic = _create_research_topic(client, headers, dept["id"], "Topic No Proposal")

    resp = client.delete(f"/api/v1/research-topics/{topic['id']}", headers=headers)
    assert resp.status_code == 200, resp.text

    resp_check = client.get(f"/api/v1/research-topics/{topic['id']}", headers=headers)
    assert resp_check.status_code == 404


def test_delete_faculty_with_departments_blocked(client: TestClient, db_session: Session):
    admin, univ, headers = create_university_admin_helper(db_session)
    faculty = _create_faculty(client, headers, "Faculty With Dept", f"FWD-{uuid.uuid4().hex[:4].upper()}")
    _create_department(client, headers, faculty["id"], "Dept Inside", f"DI-{uuid.uuid4().hex[:4].upper()}")

    resp = client.delete(f"/api/v1/faculties/{faculty['id']}", headers=headers)
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"] == "SpecializedOperationError"


def test_delete_department_with_profiles_blocked(client: TestClient, db_session: Session):
    admin, univ, headers = create_university_admin_helper(db_session)
    faculty = _create_faculty(client, headers, "Faculty Prof", f"FP-{uuid.uuid4().hex[:4].upper()}")
    dept = _create_department(client, headers, faculty["id"], "Dept Prof", f"DP-{uuid.uuid4().hex[:4].upper()}")

    # Create a student profile in the department.
    user = create_user_helper(db_session)
    create_membership_helper(db_session, univ.id, user.id)
    resp = client.post(
        "/api/v1/student-profiles",
        json={
            "user_id": user.id,
            "student_id": f"S{uuid.uuid4().hex[:6].upper()}",
            "department_id": dept["id"],
            "academic_level": "undergraduate",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.delete(f"/api/v1/departments/{dept['id']}", headers=headers)
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"] == "SpecializedOperationError"


def test_delete_grant_opportunity_with_applications_blocked(client: TestClient, db_session: Session):
    admin, univ, headers = create_university_admin_helper(db_session)
    opp = _create_grant_opportunity(client, headers)
    app_ = _create_grant_application(client, headers, opp["id"])

    resp = client.delete(f"/api/v1/grant-opportunities/{opp['id']}", headers=headers)
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"] == "SpecializedOperationError"

    # Opportunity still exists.
    resp_check = client.get(f"/api/v1/grant-opportunities/{opp['id']}", headers=headers)
    assert resp_check.status_code == 200


# ---------------------------------------------------------------------------
# Field filters
# ---------------------------------------------------------------------------

def test_list_projects_filter_by_proposal_id(client: TestClient, db_session: Session):
    admin, univ, headers = create_university_admin_helper(db_session)
    faculty = _create_faculty(client, headers, "Faculty Filter", f"FF-{uuid.uuid4().hex[:4].upper()}")
    dept = _create_department(client, headers, faculty["id"], "Dept Filter", f"DF-{uuid.uuid4().hex[:4].upper()}")
    prop1 = _create_research_proposal(client, headers, _create_research_topic(client, headers, dept["id"], "T1")["id"], dept["id"], "P1")
    prop2 = _create_research_proposal(client, headers, _create_research_topic(client, headers, dept["id"], "T2")["id"], dept["id"], "P2")
    _create_research_project(client, headers, prop1["id"], dept["id"], "Project for P1")
    _create_research_project(client, headers, prop2["id"], dept["id"], "Project for P2")

    resp = client.get(f"/api/v1/research-projects?proposal_id={prop1['id']}", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["proposal_id"] == str(prop1["id"])


def test_list_proposals_filter_by_submitting_user(client: TestClient, db_session: Session):
    admin, univ, headers = create_university_admin_helper(db_session)
    faculty = _create_faculty(client, headers, "Faculty Sub", f"FS-{uuid.uuid4().hex[:4].upper()}")
    dept = _create_department(client, headers, faculty["id"], "Dept Sub", f"DS-{uuid.uuid4().hex[:4].upper()}")
    topic = _create_research_topic(client, headers, dept["id"], "Topic Sub")

    _create_research_proposal(client, headers, topic["id"], dept["id"], "Prop by Admin")

    other = create_user_helper(db_session)
    create_membership_helper(db_session, univ.id, other.id)
    other_headers = make_auth_headers(other, univ.id)
    _create_research_proposal(client, other_headers, topic["id"], dept["id"], "Prop by Other")

    resp = client.get(f"/api/v1/research-proposals?submitting_user_id={admin.id}", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["submitting_user_id"] == admin.id


def test_list_awards_filter_by_application_id(client: TestClient, db_session: Session):
    admin, univ, headers = create_university_admin_helper(db_session)
    opp = _create_grant_opportunity(client, headers)
    app_ = _create_grant_application(client, headers, opp["id"])

    # Submit then award.
    client.post(f"/api/v1/grant-applications/{app_['id']}/submit", headers=headers)
    resp = client.post(
        "/api/v1/grant-awards",
        json={
            "application_id": str(app_["id"]),
            "award_reference": f"REF-{uuid.uuid4().hex[:6].upper()}",
            "awarded_amount": 5000,
            "currency": "USD",
            "award_start_date": "2025-01-01",
            "award_end_date": "2025-12-31",
            "status": "active",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/v1/grant-awards?application_id={app_['id']}", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["application_id"] == str(app_["id"])


# ---------------------------------------------------------------------------
# Status validation on transitions
# ---------------------------------------------------------------------------

def test_invalid_project_status_rejected(client: TestClient, db_session: Session):
    admin, univ, headers = create_university_admin_helper(db_session)
    faculty = _create_faculty(client, headers, "Faculty Status", f"FST-{uuid.uuid4().hex[:4].upper()}")
    dept = _create_department(client, headers, faculty["id"], "Dept Status", f"DST-{uuid.uuid4().hex[:4].upper()}")
    topic = _create_research_topic(client, headers, dept["id"], "Topic Status")
    prop = _create_research_proposal(client, headers, topic["id"], dept["id"], "Prop Status")
    project = _create_research_project(client, headers, prop["id"], dept["id"], "Project Status")

    resp = client.post(
        f"/api/v1/research-projects/{project['id']}/status",
        json={"new_status": "not_a_real_status", "reason": "nope"},
        headers=headers,
    )
    # Schema pattern validation rejects invalid statuses with 422.
    assert resp.status_code == 422, resp.text


def test_valid_project_status_transition(client: TestClient, db_session: Session):
    admin, univ, headers = create_university_admin_helper(db_session)
    faculty = _create_faculty(client, headers, "Faculty Valid", f"FV-{uuid.uuid4().hex[:4].upper()}")
    dept = _create_department(client, headers, faculty["id"], "Dept Valid", f"DV-{uuid.uuid4().hex[:4].upper()}")
    topic = _create_research_topic(client, headers, dept["id"], "Topic Valid")
    prop = _create_research_proposal(client, headers, topic["id"], dept["id"], "Prop Valid")
    project = _create_research_project(client, headers, prop["id"], dept["id"], "Project Valid")

    resp = client.post(
        f"/api/v1/research-projects/{project['id']}/status",
        json={"new_status": "completed"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "completed"


# ---------------------------------------------------------------------------
# Pagination envelope
# ---------------------------------------------------------------------------

def test_pagination_envelope_consistency(client: TestClient, db_session: Session):
    admin, _, headers = create_university_admin_helper(db_session)
    # Create multiple faculties to paginate.
    for i in range(7):
        _create_faculty(client, headers, f"Page Faculty {i}", f"PF{i}-{uuid.uuid4().hex[:4].upper()}")

    resp = client.get("/api/v1/faculties?page=1&page_size=3", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert set(data.keys()) >= {"items", "total", "page", "page_size", "total_pages"}
    assert data["page"] == 1
    assert data["page_size"] == 3
    assert data["total"] >= 7
    assert data["total_pages"] >= 3
    assert len(data["items"]) <= 3


# ---------------------------------------------------------------------------
# Tenant isolation for delete guards
# ---------------------------------------------------------------------------

def test_delete_guard_respects_tenant_isolation(client: TestClient, db_session: Session):
    user_a, univ_a, user_b, univ_b = _setup_two_tenants_api(db_session)
    headers_a = make_auth_headers(user_a, univ_a.id)
    headers_b = make_auth_headers(user_b, univ_b.id)

    faculty_a = _create_faculty(client, headers_a, "Faculty Isolation A", f"IA-{uuid.uuid4().hex[:4].upper()}")
    dept_a = _create_department(client, headers_a, faculty_a["id"], "Dept Isolation A", f"DI-{uuid.uuid4().hex[:4].upper()}")
    topic_a = _create_research_topic(client, headers_a, dept_a["id"], "Topic Isolation A")

    # user_b cannot delete university A's topic (invisible → 404, not a guard error).
    resp = client.delete(f"/api/v1/research-topics/{topic_a['id']}", headers=headers_b)
    assert resp.status_code == 404, resp.text


def _setup_two_tenants_api(db: Session):
    user_a = create_user_helper(db)
    user_b = create_user_helper(db)
    univ_a = create_university_helper(db)
    univ_b = create_university_helper(db)
    create_membership_helper(db, univ_a.id, user_a.id)
    create_membership_helper(db, univ_b.id, user_b.id)
    # Grant setup rights so gated creation calls succeed; isolation must still hold.
    assign_role_helper(db, univ_a.id, user_a.id, "university_admin")
    assign_role_helper(db, univ_b.id, user_b.id, "university_admin")
    return user_a, univ_a, user_b, univ_b
