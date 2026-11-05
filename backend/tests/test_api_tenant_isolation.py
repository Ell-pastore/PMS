"""Tests for multi-university tenant isolation.

Verifies that users in University A cannot access, create, update, or delete
resources belonging to University B, even when supplying valid IDs directly.
"""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.tests.conftest import (
    create_membership_helper,
    create_university_helper,
    create_user_helper,
    make_auth_headers,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _setup_two_tenants(db: Session):
    """Create two users each in their own university. Returns (user_a, univ_a, user_b, univ_b)."""
    user_a = create_user_helper(db)
    user_b = create_user_helper(db)
    univ_a = create_university_helper(db)
    univ_b = create_university_helper(db)
    create_membership_helper(db, univ_a.id, user_a.id)
    create_membership_helper(db, univ_b.id, user_b.id)
    return user_a, univ_a, user_b, univ_b


def _create_faculty(client: TestClient, headers: dict, name: str, code: str) -> dict:
    resp = client.post(
        "/api/v1/faculties",
        json={"name": name, "code": code, "is_active": True},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_department(
    client: TestClient, headers: dict, faculty_id: int, name: str, code: str
) -> dict:
    resp = client.post(
        "/api/v1/departments",
        json={"name": name, "code": code, "faculty_id": faculty_id, "is_active": True},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_research_topic(
    client: TestClient, headers: dict, department_id: int, title: str
) -> dict:
    resp = client.post(
        "/api/v1/research-topics",
        json={"title": title, "department_id": department_id},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Tenant isolation – faculty
# ---------------------------------------------------------------------------

def test_cannot_read_faculty_of_another_university(client: TestClient, db_session: Session):
    user_a, univ_a, user_b, univ_b = _setup_two_tenants(db_session)
    headers_a = make_auth_headers(user_a, univ_a.id)
    headers_b = make_auth_headers(user_b, univ_b.id)

    suffix = uuid.uuid4().hex[:6]
    faculty_a = _create_faculty(client, headers_a, f"Faculty A {suffix}", f"FA-{suffix[:8].upper()}")

    # user_b using their own university header cannot see university A's faculty
    resp = client.get(f"/api/v1/faculties/{faculty_a['id']}", headers=headers_b)
    assert resp.status_code == 404
    assert resp.json()["error"] == "NotFoundError"


def test_cannot_update_faculty_of_another_university(client: TestClient, db_session: Session):
    user_a, univ_a, user_b, univ_b = _setup_two_tenants(db_session)
    headers_a = make_auth_headers(user_a, univ_a.id)
    headers_b = make_auth_headers(user_b, univ_b.id)

    suffix = uuid.uuid4().hex[:6]
    faculty_a = _create_faculty(client, headers_a, f"Faculty A {suffix}", f"FB-{suffix[:8].upper()}")

    resp = client.patch(
        f"/api/v1/faculties/{faculty_a['id']}",
        json={"name": "Tampered Name"},
        headers=headers_b,
    )
    # Should be 404 — resource invisible to this tenant, not 200 (overwrite) or 403 (leaking existence)
    assert resp.status_code == 404


def test_cannot_delete_faculty_of_another_university(client: TestClient, db_session: Session):
    user_a, univ_a, user_b, univ_b = _setup_two_tenants(db_session)
    headers_a = make_auth_headers(user_a, univ_a.id)
    headers_b = make_auth_headers(user_b, univ_b.id)

    suffix = uuid.uuid4().hex[:6]
    faculty_a = _create_faculty(client, headers_a, f"Faculty X {suffix}", f"FX-{suffix[:8].upper()}")

    resp = client.delete(f"/api/v1/faculties/{faculty_a['id']}", headers=headers_b)
    assert resp.status_code == 404

    # Confirm it still exists for university A
    resp_check = client.get(f"/api/v1/faculties/{faculty_a['id']}", headers=headers_a)
    assert resp_check.status_code == 200


# ---------------------------------------------------------------------------
# Tenant isolation – research topics
# ---------------------------------------------------------------------------

def test_cannot_access_research_topic_of_another_university(client: TestClient, db_session: Session):
    user_a, univ_a, user_b, univ_b = _setup_two_tenants(db_session)
    headers_a = make_auth_headers(user_a, univ_a.id)
    headers_b = make_auth_headers(user_b, univ_b.id)

    suffix = uuid.uuid4().hex[:6]
    faculty_a = _create_faculty(client, headers_a, f"Faculty T {suffix}", f"FT-{suffix[:8].upper()}")
    dept_a = _create_department(client, headers_a, faculty_a["id"], f"Dept T {suffix}", f"DT-{suffix[:8].upper()}")
    topic_a = _create_research_topic(client, headers_a, dept_a["id"], f"Topic A {suffix}")

    # user_b cannot read it
    resp = client.get(f"/api/v1/research-topics/{topic_a['id']}", headers=headers_b)
    assert resp.status_code == 404

    # user_b cannot update it
    resp_up = client.patch(
        f"/api/v1/research-topics/{topic_a['id']}",
        json={"title": "Tampered Topic"},
        headers=headers_b,
    )
    assert resp_up.status_code == 404


def test_list_endpoints_scoped_to_own_university(client: TestClient, db_session: Session):
    user_a, univ_a, user_b, univ_b = _setup_two_tenants(db_session)
    headers_a = make_auth_headers(user_a, univ_a.id)
    headers_b = make_auth_headers(user_b, univ_b.id)

    suffix = uuid.uuid4().hex[:6]
    _create_faculty(client, headers_a, f"Exclusive Faculty {suffix}", f"EF-{suffix[:8].upper()}")

    # user_b's faculties list should not include user_a's faculty
    resp_b = client.get("/api/v1/faculties", headers=headers_b)
    assert resp_b.status_code == 200
    items_b = resp_b.json()["items"]
    faculty_names_b = {f["name"] for f in items_b}
    assert f"Exclusive Faculty {suffix}" not in faculty_names_b

    # user_a's list should include it
    resp_a = client.get("/api/v1/faculties", headers=headers_a)
    assert resp_a.status_code == 200
    items_a = resp_a.json()["items"]
    faculty_names_a = {f["name"] for f in items_a}
    assert f"Exclusive Faculty {suffix}" in faculty_names_a


# ---------------------------------------------------------------------------
# Tenant isolation – membership required
# ---------------------------------------------------------------------------

def test_no_university_header_returns_403(client: TestClient, db_session: Session):
    user = create_user_helper(db_session)
    # Using auth but no X-University-ID header
    headers = make_auth_headers(user)
    resp = client.get("/api/v1/faculties", headers=headers)
    assert resp.status_code in (403, 400)  # ForbiddenError for missing tenant header


def test_non_member_cannot_access_university_resources(client: TestClient, db_session: Session):
    user_a, univ_a, _, _ = _setup_two_tenants(db_session)
    outsider = create_user_helper(db_session)

    # outsider has no membership in univ_a but supplies the univ_a header
    headers_outsider = make_auth_headers(outsider, univ_a.id)
    resp = client.get("/api/v1/faculties", headers=headers_outsider)
    # Must be forbidden — not a member
    assert resp.status_code == 403


def test_cross_university_department_creation_blocked(client: TestClient, db_session: Session):
    user_a, univ_a, user_b, univ_b = _setup_two_tenants(db_session)
    headers_a = make_auth_headers(user_a, univ_a.id)
    headers_b = make_auth_headers(user_b, univ_b.id)

    suffix = uuid.uuid4().hex[:6]
    faculty_a = _create_faculty(client, headers_a, f"Faculty C {suffix}", f"FC-{suffix[:8].upper()}")

    # user_b tries to create a department referencing university A's faculty_id
    resp = client.post(
        "/api/v1/departments",
        json={"name": f"Injected Dept {suffix}", "code": f"ID-{suffix[:8].upper()}", "faculty_id": faculty_a["id"]},
        headers=headers_b,
    )
    # Faculty does not exist in university B scope → 400 ForeignKeyViolationError or 404
    assert resp.status_code in (400, 404)

