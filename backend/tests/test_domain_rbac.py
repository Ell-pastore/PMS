"""Tests for domain-level RBAC on mutation routes.

Verifies that plain members are rejected (403 ForbiddenError) on gated
mutations, that domain role holders and university admins succeed, that
superadmin bypasses role checks, and that reads stay open to all members.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Role
from backend.tests.conftest import (
    assign_role_helper,
    create_membership_helper,
    create_university_helper,
    create_user_helper,
    make_auth_headers,
)


def _member_with(db: Session, *role_codes: str):
    """Create a member user in a new university and assign the given role codes.

    Returns (user, univ, headers).
    """
    user = create_user_helper(db)
    univ = create_university_helper(db)
    create_membership_helper(db, univ.id, user.id)
    for code in role_codes:
        assign_role_helper(db, univ.id, user.id, code)
    return user, univ, make_auth_headers(user, univ.id)


def _member_in(db: Session, univ, *role_codes: str):
    """Create a member user inside an existing university and assign roles."""
    user = create_user_helper(db)
    create_membership_helper(db, univ.id, user.id)
    for code in role_codes:
        assign_role_helper(db, univ.id, user.id, code)
    return user, univ, make_auth_headers(user, univ.id)


def _assert_forbidden(resp) -> None:
    assert resp.status_code == 403, resp.text
    body = resp.json()
    assert body["error"] == "ForbiddenError"
    assert body["error_code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# Plain members are blocked on gated mutations
# ---------------------------------------------------------------------------

def test_member_forbidden_on_gated_mutations(client: TestClient, db_session: Session):
    admin, univ, admin_headers = _member_with(db_session, "university_admin")
    member, _, member_headers = _member_with(db_session)

    # Organization structure the gated payloads reference.
    suffix = uuid.uuid4().hex[:6].upper()
    resp = client.post(
        "/api/v1/faculties",
        json={"name": "RBAC Faculty", "code": f"RF-{suffix}", "is_active": True},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    faculty_id = resp.json()["id"]
    resp = client.post(
        "/api/v1/departments",
        json={"name": "RBAC Dept", "code": f"RD-{suffix}", "faculty_id": faculty_id, "is_active": True},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    department_id = resp.json()["id"]

    # Any role row works for the user-roles payload: the 403 fires before FK checks.
    admin_role = db_session.scalar(select(Role).where(Role.code == "university_admin"))

    cases = [
        ("post", "/api/v1/faculties", {"name": "Nope", "code": f"NF-{suffix}", "is_active": True}),
        ("patch", f"/api/v1/faculties/{faculty_id}", {"name": "Tampered"}),
        ("delete", f"/api/v1/faculties/{faculty_id}", None),
        ("post", "/api/v1/departments", {"name": "Nope", "code": f"ND-{suffix}", "faculty_id": faculty_id, "is_active": True}),
        ("post", "/api/v1/research-topics", {"title": "Nope", "department_id": department_id}),
        ("post", "/api/v1/grant-opportunities", {
            "title": "Nope",
            "funding_organization": "Org",
            "application_opens_at": "2025-01-01T00:00:00Z",
            "application_closes_at": "2025-12-31T00:00:00Z",
            "min_funding_amount": 1000,
            "currency": "USD",
        }),
        ("post", "/api/v1/grant-awards", {
            "application_id": str(uuid.uuid4()),
            "award_reference": f"AW-{suffix}",
            "awarded_amount": 100,
            "currency": "USD",
            "award_start_date": "2025-01-01",
            "award_end_date": "2025-12-31",
        }),
        ("post", "/api/v1/university-memberships", {"user_id": member.id, "is_active": True}),
        ("post", "/api/v1/user-roles", {"user_id": member.id, "role_id": admin_role.id}),
        ("post", "/api/v1/milestone-templates", {
            "department_id": department_id,
            "name": "Nope",
            "default_duration_days": 30,
        }),
        ("post", "/api/v1/approval-workflows", {"workflow_type": "proposal"}),
        ("post", "/api/v1/audit-logs", {"action": "create", "entity_type": "test"}),
        ("post", "/api/v1/retention-policies", {
            "record_category": "progress_reports",
            "retention_days": 365,
        }),
    ]
    for method, url, payload in cases:
        call = getattr(client, method)
        if payload is None:
            _assert_forbidden(call(url, headers=member_headers))
        else:
            _assert_forbidden(call(url, json=payload, headers=member_headers))


# ---------------------------------------------------------------------------
# Role holders succeed on their domains and are blocked elsewhere
# ---------------------------------------------------------------------------

def test_university_admin_can_perform_gated_mutations(client: TestClient, db_session: Session):
    admin, univ, headers = _member_with(db_session, "university_admin")
    other = create_user_helper(db_session)

    resp = client.post(
        "/api/v1/faculties",
        json={"name": "Admin Faculty", "code": f"AF-{uuid.uuid4().hex[:6].upper()}", "is_active": True},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.post("/api/v1/university-memberships", json={"user_id": other.id}, headers=headers)
    assert resp.status_code == 201, resp.text

    admin_role = db_session.scalar(select(Role).where(Role.code == "university_admin"))
    resp = client.post(
        "/api/v1/user-roles",
        json={"user_id": other.id, "role_id": admin_role.id},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.post(
        "/api/v1/settings/system",
        json={"setting_key": f"test_key_{uuid.uuid4().hex[:6]}", "setting_value": {"v": 1}},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text


def test_grant_admin_can_manage_grants_but_not_faculties(client: TestClient, db_session: Session):
    _, _, headers = _member_with(db_session, "grant_admin")

    resp = client.post(
        "/api/v1/grant-opportunities",
        json={
            "title": "Grant Admin Opp",
            "funding_organization": "Org",
            "application_opens_at": "2025-01-01T00:00:00Z",
            "application_closes_at": "2025-12-31T00:00:00Z",
            "min_funding_amount": 1000,
            "currency": "USD",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    _assert_forbidden(
        client.post(
            "/api/v1/faculties",
            json={"name": "Nope", "code": f"NF-{uuid.uuid4().hex[:6].upper()}", "is_active": True},
            headers=headers,
        )
    )


def test_research_admin_can_manage_topics_but_not_grants(client: TestClient, db_session: Session):
    admin, univ, admin_headers = _member_with(db_session, "university_admin")
    _, _, headers = _member_in(db_session, univ, "research_admin")

    suffix = uuid.uuid4().hex[:6].upper()
    resp = client.post(
        "/api/v1/faculties",
        json={"name": "RA Faculty", "code": f"RAF-{suffix}", "is_active": True},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    resp = client.post(
        "/api/v1/departments",
        json={"name": "RA Dept", "code": f"RAD-{suffix}", "faculty_id": resp.json()["id"], "is_active": True},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    department_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/research-topics",
        json={"title": "Research Admin Topic", "department_id": department_id},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    _assert_forbidden(
        client.post(
            "/api/v1/grant-opportunities",
            json={
                "title": "Nope",
                "funding_organization": "Org",
                "application_opens_at": "2025-01-01T00:00:00Z",
                "application_closes_at": "2025-12-31T00:00:00Z",
                "min_funding_amount": 1000,
                "currency": "USD",
            },
            headers=headers,
        )
    )


def test_department_head_can_manage_departments(client: TestClient, db_session: Session):
    admin, univ, admin_headers = _member_with(db_session, "university_admin")
    _, _, headers = _member_in(db_session, univ, "department_head")

    suffix = uuid.uuid4().hex[:6].upper()
    resp = client.post(
        "/api/v1/faculties",
        json={"name": "DH Faculty", "code": f"DHF-{suffix}", "is_active": True},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.post(
        "/api/v1/departments",
        json={"name": "DH Dept", "code": f"DHD-{suffix}", "faculty_id": resp.json()["id"], "is_active": True},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    # Department heads cannot create faculties.
    _assert_forbidden(
        client.post(
            "/api/v1/faculties",
            json={"name": "Nope", "code": f"NF-{suffix}", "is_active": True},
            headers=headers,
        )
    )


# ---------------------------------------------------------------------------
# Superadmin bypass and open reads
# ---------------------------------------------------------------------------

def test_superadmin_bypasses_role_requirements(client: TestClient, db_session: Session):
    _, univ, headers = _member_with(db_session, "superadmin")

    # Superadmin passes every gate without holding the domain role.
    resp = client.post(
        "/api/v1/faculties",
        json={"name": "SA Faculty", "code": f"SAF-{uuid.uuid4().hex[:6].upper()}", "is_active": True},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.post(
        "/api/v1/grant-opportunities",
        json={
            "title": "SA Opp",
            "funding_organization": "Org",
            "application_opens_at": "2025-01-01T00:00:00Z",
            "application_closes_at": "2025-12-31T00:00:00Z",
            "min_funding_amount": 1000,
            "currency": "USD",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text


def test_reads_stay_open_to_plain_members(client: TestClient, db_session: Session):
    _, _, headers = _member_with(db_session)

    for url in (
        "/api/v1/faculties",
        "/api/v1/departments",
        "/api/v1/research-topics",
        "/api/v1/grant-opportunities",
        "/api/v1/milestone-templates",
        "/api/v1/approval-workflows",
        "/api/v1/retention-policies",
    ):
        resp = client.get(url, headers=headers)
        assert resp.status_code == 200, (url, resp.text)
