"""Tests for service-layer delete guards.

Blocked deletions must return 400 SpecializedOperationError (RESTRICTED_OPERATION)
instead of leaking raw database integrity errors. Deletable entities with only
machine-derived bookkeeping rows (status history, draft workflow versions)
must succeed.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.tests.conftest import (
    create_membership_helper,
    create_university_helper,
    create_university_admin_helper,
    create_user_helper,
    make_auth_headers,
)


def _assert_blocked(resp) -> None:
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["error"] == "SpecializedOperationError"
    assert body["error_code"] == "RESTRICTED_OPERATION"
    assert "Cannot" in body["detail"]


def _assert_deleted(resp) -> None:
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "success"


class _Setup:
    """Creates an admin tenant with faculty/department/topic building blocks."""

    def __init__(self, client: TestClient, db: Session) -> None:
        self.client = client
        self.db = db
        self.admin, self.univ, self.headers = create_university_admin_helper(db)
        suffix = uuid.uuid4().hex[:6].upper()

        resp = client.post(
            "/api/v1/faculties",
            json={"name": "Guard Faculty", "code": f"GF-{suffix}", "is_active": True},
            headers=self.headers,
        )
        assert resp.status_code == 201, resp.text
        self.faculty = resp.json()

        resp = client.post(
            "/api/v1/departments",
            json={
                "name": "Guard Dept",
                "code": f"GD-{suffix}",
                "faculty_id": self.faculty["id"],
                "is_active": True,
            },
            headers=self.headers,
        )
        assert resp.status_code == 201, resp.text
        self.department = resp.json()

        resp = client.post(
            "/api/v1/research-topics",
            json={"title": "Guard Topic", "department_id": self.department["id"]},
            headers=self.headers,
        )
        assert resp.status_code == 201, resp.text
        self.topic = resp.json()

        # Student member with a student profile usable as proposal participant.
        self.student_user = create_user_helper(db)
        create_membership_helper(db, self.univ.id, self.student_user.id)
        resp = client.post(
            "/api/v1/student-profiles",
            json={
                "user_id": self.student_user.id,
                "student_id": f"STU-{suffix}",
                "department_id": self.department["id"],
                "academic_level": "masters",
            },
            headers=self.headers,
        )
        assert resp.status_code == 201, resp.text
        self.student_profile = resp.json()

        # Staff member with a staff profile usable as proposal supervisor.
        self.staff_user = create_user_helper(db)
        create_membership_helper(db, self.univ.id, self.staff_user.id)
        resp = client.post(
            "/api/v1/staff-profiles",
            json={
                "user_id": self.staff_user.id,
                "staff_id": f"STA-{suffix}",
                "department_id": self.department["id"],
                "job_title": "Lecturer",
            },
            headers=self.headers,
        )
        assert resp.status_code == 201, resp.text
        self.staff_profile = resp.json()

    def create_proposal(self, title: str = "Guard Proposal") -> dict:
        resp = self.client.post(
            "/api/v1/research-proposals",
            json={
                "title": title,
                "topic_id": str(self.topic["id"]),
                "department_id": self.department["id"],
                "abstract": "abstract",
            },
            headers=self.headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    def create_project(self, proposal: dict, title: str = "Guard Project") -> dict:
        resp = self.client.post(
            "/api/v1/research-projects",
            json={
                "title": title,
                "proposal_id": str(proposal["id"]),
                "department_id": self.department["id"],
                "start_date": "2025-01-01",
                "status": "active",
            },
            headers=self.headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    def create_opportunity(self) -> dict:
        resp = self.client.post(
            "/api/v1/grant-opportunities",
            json={
                "title": "Guard Opportunity",
                "funding_organization": "Org",
                "application_opens_at": "2025-01-01T00:00:00Z",
                "application_closes_at": "2025-12-31T00:00:00Z",
                "min_funding_amount": 1000,
                "currency": "USD",
            },
            headers=self.headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    def create_application(self, opportunity: dict) -> dict:
        resp = self.client.post(
            "/api/v1/grant-applications",
            json={
                "opportunity_id": str(opportunity["id"]),
                "title": "Guard Application",
                "proposal": "proposal text",
                "requested_amount": 5000,
                "currency": "USD",
            },
            headers=self.headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()


# ---------------------------------------------------------------------------
# Proposals
# ---------------------------------------------------------------------------

def test_delete_draft_proposal_without_children_succeeds(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    proposal = setup.create_proposal()

    resp = client.delete(f"/api/v1/research-proposals/{proposal['id']}", headers=setup.headers)
    _assert_deleted(resp)

    resp = client.get(f"/api/v1/research-proposals/{proposal['id']}", headers=setup.headers)
    assert resp.status_code == 404


def test_delete_proposal_with_participant_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    proposal = setup.create_proposal()

    resp = client.post(
        f"/api/v1/research-proposals/{proposal['id']}/participants",
        json={"student_id": setup.student_profile["id"], "participation_role": "lead", "is_lead": True},
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.delete(f"/api/v1/research-proposals/{proposal['id']}", headers=setup.headers)
    _assert_blocked(resp)
    assert "participants" in resp.json()["detail"]


def test_delete_submitted_proposal_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    proposal = setup.create_proposal()

    resp = client.post(f"/api/v1/research-proposals/{proposal['id']}/submit", headers=setup.headers)
    assert resp.status_code == 200, resp.text

    resp = client.delete(f"/api/v1/research-proposals/{proposal['id']}", headers=setup.headers)
    _assert_blocked(resp)


# ---------------------------------------------------------------------------
# Projects, milestones, templates
# ---------------------------------------------------------------------------

def test_delete_project_without_children_succeeds(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    project = setup.create_project(setup.create_proposal())

    resp = client.delete(f"/api/v1/research-projects/{project['id']}", headers=setup.headers)
    _assert_deleted(resp)


def test_delete_project_with_milestone_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    project = setup.create_project(setup.create_proposal())

    resp = client.post(
        f"/api/v1/research-projects/{project['id']}/milestones",
        json={"title": "M1", "sequence_number": 1, "due_date": "2025-06-01"},
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.delete(f"/api/v1/research-projects/{project['id']}", headers=setup.headers)
    _assert_blocked(resp)
    assert "milestones" in resp.json()["detail"]


def test_delete_milestone_without_children_succeeds(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    project = setup.create_project(setup.create_proposal())

    resp = client.post(
        f"/api/v1/research-projects/{project['id']}/milestones",
        json={"title": "M1", "sequence_number": 1, "due_date": "2025-06-01"},
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text
    milestone_id = resp.json()["id"]

    resp = client.delete(f"/api/v1/project-milestones/{milestone_id}", headers=setup.headers)
    _assert_deleted(resp)


def test_delete_milestone_with_report_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    project = setup.create_project(setup.create_proposal())

    resp = client.post(
        f"/api/v1/research-projects/{project['id']}/milestones",
        json={"title": "M1", "sequence_number": 1, "due_date": "2025-06-01"},
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text
    milestone_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/progress-reports",
        json={
            "project_id": str(project["id"]),
            "milestone_id": str(milestone_id),
            "period_start": "2025-01-01",
            "period_end": "2025-02-01",
            "title": "Report",
            "content": "content",
        },
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.delete(f"/api/v1/project-milestones/{milestone_id}", headers=setup.headers)
    _assert_blocked(resp)
    assert "progress reports" in resp.json()["detail"]


def test_delete_template_without_milestones_succeeds(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    resp = client.post(
        "/api/v1/milestone-templates",
        json={
            "department_id": setup.department["id"],
            "name": "Guard Template",
            "default_duration_days": 30,
        },
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.delete(f"/api/v1/milestone-templates/{resp.json()['id']}", headers=setup.headers)
    _assert_deleted(resp)


def test_delete_template_with_milestone_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    resp = client.post(
        "/api/v1/milestone-templates",
        json={
            "department_id": setup.department["id"],
            "name": "Guard Template",
            "default_duration_days": 30,
        },
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text
    template_id = resp.json()["id"]

    project = setup.create_project(setup.create_proposal())
    resp = client.post(
        f"/api/v1/research-projects/{project['id']}/milestones",
        json={
            "title": "M1",
            "sequence_number": 1,
            "due_date": "2025-06-01",
            "template_id": str(template_id),
        },
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.delete(f"/api/v1/milestone-templates/{template_id}", headers=setup.headers)
    _assert_blocked(resp)
    assert "milestones" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Grants
# ---------------------------------------------------------------------------

def test_delete_draft_application_without_children_succeeds(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    application = setup.create_application(setup.create_opportunity())

    resp = client.delete(f"/api/v1/grant-applications/{application['id']}", headers=setup.headers)
    _assert_deleted(resp)


def test_delete_application_with_participant_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    application = setup.create_application(setup.create_opportunity())

    resp = client.post(
        f"/api/v1/grant-applications/{application['id']}/participants",
        json={"user_id": setup.student_user.id, "participation_role": "co_investigator"},
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.delete(f"/api/v1/grant-applications/{application['id']}", headers=setup.headers)
    _assert_blocked(resp)
    assert "participants" in resp.json()["detail"]


def test_delete_submitted_application_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    application = setup.create_application(setup.create_opportunity())

    resp = client.post(f"/api/v1/grant-applications/{application['id']}/submit", headers=setup.headers)
    assert resp.status_code == 200, resp.text

    resp = client.delete(f"/api/v1/grant-applications/{application['id']}", headers=setup.headers)
    _assert_blocked(resp)


def _create_award(client: TestClient, setup: _Setup, application: dict) -> dict:
    resp = client.post(
        "/api/v1/grant-awards",
        json={
            "application_id": str(application["id"]),
            "award_reference": f"AW-{uuid.uuid4().hex[:8].upper()}",
            "awarded_amount": 5000,
            "currency": "USD",
            "award_start_date": "2025-01-01",
            "award_end_date": "2025-12-31",
        },
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_delete_award_without_children_succeeds(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    award = _create_award(client, setup, setup.create_application(setup.create_opportunity()))

    resp = client.delete(f"/api/v1/grant-awards/{award['id']}", headers=setup.headers)
    _assert_deleted(resp)


def test_delete_award_with_expenditure_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    award = _create_award(client, setup, setup.create_application(setup.create_opportunity()))

    resp = client.post(
        f"/api/v1/grant-awards/{award['id']}/expenditures",
        json={
            "description": "Equipment",
            "amount": 100,
            "currency": "USD",
            "expenditure_date": "2025-03-01",
        },
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.delete(f"/api/v1/grant-awards/{award['id']}", headers=setup.headers)
    _assert_blocked(resp)
    assert "expenditures" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Publications, alerts, files
# ---------------------------------------------------------------------------

def test_delete_publication_with_author_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    resp = client.post(
        "/api/v1/publications",
        json={"title": "Guard Publication", "publication_type": "journal_article"},
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text
    publication = resp.json()

    resp = client.post(
        f"/api/v1/publications/{publication['id']}/authors",
        json={"external_author_name": "External Author", "author_order": 1},
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.delete(f"/api/v1/publications/{publication['id']}", headers=setup.headers)
    _assert_blocked(resp)
    assert "authors" in resp.json()["detail"]


def test_delete_alert_rule_with_event_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    resp = client.post(
        "/api/v1/alert-rules",
        json={"rule_type": "student_inactivity", "threshold_value": 30},
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text
    rule = resp.json()

    resp = client.post(
        "/api/v1/alert-events",
        json={
            "rule_id": str(rule["id"]),
            "alert_type": "student_inactivity",
            "target_entity_type": "student_profile",
            "target_entity_id": str(uuid.uuid4()),
            "severity": "warning",
            "message": "inactive student",
        },
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.delete(f"/api/v1/alert-rules/{rule['id']}", headers=setup.headers)
    _assert_blocked(resp)
    assert "alert events" in resp.json()["detail"]


def test_delete_stored_file_with_attachment_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    proposal = setup.create_proposal()

    resp = client.post(
        "/api/v1/stored-files",
        json={
            "storage_key": f"uploads/{uuid.uuid4()}",
            "original_filename": "doc.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 128,
        },
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text
    file_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/document-attachments",
        json={
            "stored_file_id": str(file_id),
            "proposal_id": str(proposal["id"]),
            "document_type": "proposal_document",
        },
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.delete(f"/api/v1/stored-files/{file_id}?hard_delete=true", headers=setup.headers)
    _assert_blocked(resp)
    assert "document attachments" in resp.json()["detail"]

    # Soft delete stays available for attached files.
    resp = client.delete(f"/api/v1/stored-files/{file_id}", headers=setup.headers)
    _assert_deleted(resp)


def test_delete_stored_file_hard_without_attachments_succeeds(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    resp = client.post(
        "/api/v1/stored-files",
        json={
            "storage_key": f"uploads/{uuid.uuid4()}",
            "original_filename": "doc.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 128,
        },
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text
    file_id = resp.json()["id"]

    resp = client.delete(f"/api/v1/stored-files/{file_id}?hard_delete=true", headers=setup.headers)
    _assert_deleted(resp)


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

def test_delete_staff_profile_with_supervisor_assignment_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    proposal = setup.create_proposal()

    resp = client.post(
        f"/api/v1/research-proposals/{proposal['id']}/supervisors",
        json={"staff_id": setup.staff_profile["id"], "assignment_role": "primary"},
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.delete(f"/api/v1/staff-profiles/{setup.staff_profile['id']}", headers=setup.headers)
    _assert_blocked(resp)
    assert "supervisor" in resp.json()["detail"]


def test_delete_student_profile_with_participant_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    proposal = setup.create_proposal()

    resp = client.post(
        f"/api/v1/research-proposals/{proposal['id']}/participants",
        json={"student_id": setup.student_profile["id"], "participation_role": "lead", "is_lead": True},
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.delete(f"/api/v1/student-profiles/{setup.student_profile['id']}", headers=setup.headers)
    _assert_blocked(resp)
    assert "participant" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Users, roles, universities, memberships
# ---------------------------------------------------------------------------

def test_delete_user_with_membership_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)

    resp = client.delete(f"/api/v1/users/{setup.student_user.id}", headers=setup.headers)
    _assert_blocked(resp)
    assert "memberships" in resp.json()["detail"]


def test_delete_user_without_membership_succeeds(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    orphan = create_user_helper(db_session)

    resp = client.delete(f"/api/v1/users/{orphan.id}", headers=setup.headers)
    _assert_deleted(resp)


def test_delete_role_with_assignment_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)

    # The admin's own university_admin role is assigned → blocked.
    resp = client.get("/api/v1/roles", headers=setup.headers)
    roles = {r["code"]: r for r in resp.json()["items"]}
    admin_role_id = roles["university_admin"]["id"]

    resp = client.delete(f"/api/v1/roles/{admin_role_id}", headers=setup.headers)
    _assert_blocked(resp)
    assert "assignments" in resp.json()["detail"]


def test_delete_unassigned_role_succeeds(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)

    resp = client.post(
        "/api/v1/roles",
        json={"code": f"temp_{uuid.uuid4().hex[:6]}", "name": "Temp Role"},
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.delete(f"/api/v1/roles/{resp.json()['id']}", headers=setup.headers)
    _assert_deleted(resp)


def test_delete_university_with_membership_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    univ = create_university_helper(db_session)
    member = create_user_helper(db_session)
    create_membership_helper(db_session, univ.id, member.id)

    resp = client.delete(f"/api/v1/universities/{univ.id}", headers=setup.headers)
    _assert_blocked(resp)
    assert "members" in resp.json()["detail"]


def test_delete_empty_university_succeeds(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    univ = create_university_helper(db_session)

    resp = client.delete(f"/api/v1/universities/{univ.id}", headers=setup.headers)
    _assert_deleted(resp)


def test_delete_membership_with_profile_blocked(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)

    resp = client.get(
        f"/api/v1/university-memberships?user_id={setup.staff_user.id}",
        headers=setup.headers,
    )
    assert resp.status_code == 200, resp.text
    membership_id = resp.json()["items"][0]["id"]

    resp = client.delete(f"/api/v1/university-memberships/{membership_id}", headers=setup.headers)
    _assert_blocked(resp)
    assert "profiles" in resp.json()["detail"]


def test_delete_plain_membership_succeeds(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)
    member = create_user_helper(db_session)
    resp = client.post(
        "/api/v1/university-memberships",
        json={"user_id": member.id},
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text
    membership_id = resp.json()["id"]

    resp = client.delete(f"/api/v1/university-memberships/{membership_id}", headers=setup.headers)
    _assert_deleted(resp)


# ---------------------------------------------------------------------------
# Approval workflows
# ---------------------------------------------------------------------------

def test_delete_workflow_and_draft_version_succeed(client: TestClient, db_session: Session):
    setup = _Setup(client, db_session)

    resp = client.post(
        "/api/v1/approval-workflows",
        json={"workflow_type": "proposal"},
        headers=setup.headers,
    )
    assert resp.status_code == 201, resp.text
    workflow_id = resp.json()["id"]

    resp = client.get(f"/api/v1/approval-workflows/{workflow_id}/versions", headers=setup.headers)
    assert resp.status_code == 200, resp.text
    version_id = resp.json()[0]["id"]

    # Draft version and its workflow are deletable in one transaction each.
    resp = client.delete(
        f"/api/v1/approval-workflows/{workflow_id}/versions/{version_id}",
        headers=setup.headers,
    )
    _assert_deleted(resp)

    resp = client.delete(f"/api/v1/approval-workflows/{workflow_id}", headers=setup.headers)
    _assert_deleted(resp)
