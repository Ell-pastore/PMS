"""Live PostgreSQL integrity tests.

These tests deliberately require ``PMS_TEST_DATABASE_URL``.  They never fall
back to the application's ``DATABASE_URL`` because the latter is the local
development database.  Every test uses one outer transaction and rolls it
back; expected failures use nested savepoints so the transaction remains
usable for the rest of the test.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine, delete, insert, select, text, update
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import Base


TEST_DATABASE_ENV = "PMS_TEST_DATABASE_URL"
DEVELOPMENT_DATABASE = "pms_db"
EXPECTED_ALEMBIC_HEAD = "e7f9a1c3b5d7"


@dataclass(frozen=True)
class Tenant:
    university_id: uuid.UUID
    faculty_id: int
    department_id: int


@dataclass(frozen=True)
class ProjectGraph:
    topic_id: uuid.UUID
    proposal_id: uuid.UUID
    project_id: uuid.UUID
    milestone_id: uuid.UUID


def _table(name: str):
    return Base.metadata.tables[name]


def _int_id() -> int:
    # Negative IDs avoid colliding with ordinary seeded integer IDs while
    # retaining the seven legacy integer-PK tables' production types.
    return -(uuid.uuid4().int % 2_000_000_000) - 1


def _add_user(session: Session, label: str) -> int:
    user_id = _int_id()
    suffix = uuid.uuid4().hex
    session.execute(
        insert(_table("users")).values(
            id=user_id,
            full_name=f"Integrity Test {label}",
            email=f"pms-integrity-{suffix}@example.test",
            password_hash="test-only-hash",
            status="active",
            email_verified=False,
        )
    )
    return user_id


def _add_tenant(session: Session, label: str, user_id: int) -> Tenant:
    university_id = uuid.uuid4()
    faculty_id = _int_id()
    department_id = _int_id()
    suffix = uuid.uuid4().hex
    session.execute(
        insert(_table("universities")).values(
            id=university_id,
            name=f"Integrity University {label}",
            code=f"IT-{suffix[:20]}",
            is_active=True,
        )
    )
    session.execute(
        insert(_table("university_memberships")).values(
            id=uuid.uuid4(),
            university_id=university_id,
            user_id=user_id,
            is_active=True,
        )
    )
    session.execute(
        insert(_table("faculties")).values(
            id=faculty_id,
            name=f"Integrity Faculty {label}",
            code=f"IF-{suffix[:20]}",
            university_id=university_id,
            is_active=True,
        )
    )
    session.execute(
        insert(_table("departments")).values(
            id=department_id,
            name=f"Integrity Department {label}",
            code=f"ID-{suffix[:20]}",
            faculty_id=faculty_id,
            university_id=university_id,
            is_active=True,
        )
    )
    return Tenant(university_id, faculty_id, department_id)


def _add_department(session: Session, tenant: Tenant, label: str) -> int:
    department_id = _int_id()
    suffix = uuid.uuid4().hex
    session.execute(
        insert(_table("departments")).values(
            id=department_id,
            name=f"Integrity Department {label}",
            code=f"ID-{suffix[:20]}",
            faculty_id=tenant.faculty_id,
            university_id=tenant.university_id,
            is_active=True,
        )
    )
    return department_id


def _add_project_graph(session: Session, tenant: Tenant, user_id: int, label: str) -> ProjectGraph:
    topic_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    project_id = uuid.uuid4()
    milestone_id = uuid.uuid4()
    session.execute(
        insert(_table("research_topics")).values(
            id=topic_id,
            university_id=tenant.university_id,
            title=f"Integrity Topic {label}",
            normalized_title=f"integrity topic {label}".casefold(),
            department_id=tenant.department_id,
            created_by_id=user_id,
            is_active=True,
        )
    )
    session.execute(
        insert(_table("research_proposals")).values(
            id=proposal_id,
            university_id=tenant.university_id,
            topic_id=topic_id,
            submitting_user_id=user_id,
            department_id=tenant.department_id,
            title=f"Integrity Proposal {label}",
            status="draft",
        )
    )
    session.execute(
        insert(_table("research_projects")).values(
            id=project_id,
            university_id=tenant.university_id,
            proposal_id=proposal_id,
            department_id=tenant.department_id,
            title=f"Integrity Project {label}",
            start_date=date.today(),
            status="active",
            created_by_id=user_id,
        )
    )
    session.execute(
        insert(_table("project_milestones")).values(
            id=milestone_id,
            university_id=tenant.university_id,
            project_id=project_id,
            title=f"Integrity Milestone {label}",
            sequence_number=1,
            due_date=date.today(),
            status="pending",
            created_by_id=user_id,
        )
    )
    return ProjectGraph(topic_id, proposal_id, project_id, milestone_id)


def _reject(session: Session, statement) -> None:
    """Assert a database constraint failure without poisoning the outer txn."""

    savepoint = session.begin_nested()
    try:
        with pytest.raises(IntegrityError):
            session.execute(statement)
    finally:
        # pytest.raises consumes the expected exception before the context
        # manager can see it.  Explicitly roll back the savepoint so PostgreSQL
        # leaves the outer transaction usable for the next assertion.
        if savepoint.is_active:
            savepoint.rollback()


@pytest.fixture(scope="session")
def postgres_engine() -> Engine:
    raw_url = os.environ.get(TEST_DATABASE_ENV)
    if not raw_url:
        pytest.skip(f"{TEST_DATABASE_ENV} is not configured; live PostgreSQL tests were not run")

    parsed_url = make_url(raw_url)
    if not parsed_url.database:
        pytest.fail(f"{TEST_DATABASE_ENV} must include an explicit database name")
    if parsed_url.database == DEVELOPMENT_DATABASE:
        pytest.fail(f"live integrity tests refuse the development database {DEVELOPMENT_DATABASE!r}")

    engine = create_engine(raw_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            current_database = connection.scalar(text("SELECT current_database()"))
            if current_database == DEVELOPMENT_DATABASE:
                pytest.fail("the explicit test URL resolved to the development database")
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            if revision != EXPECTED_ALEMBIC_HEAD:
                pytest.fail("the explicit test database is not at the expected Alembic head")
    except Exception:
        engine.dispose()
        raise

    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(postgres_engine: Engine):
    connection = postgres_engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, expire_on_commit=False)
    try:
        yield session
    finally:
        session.rollback()
        if outer_transaction.is_active:
            outer_transaction.rollback()
        session.close()
        connection.close()


def test_profile_cardinality_and_tenant_foreign_keys(db_session: Session):
    user_id = _add_user(db_session, "profiles")
    university_a = _add_tenant(db_session, "A", user_id)
    university_b = _add_tenant(db_session, "B", user_id)

    for index, tenant in enumerate((university_a, university_b), start=1):
        db_session.execute(
            insert(_table("student_profiles")).values(
                id=_int_id(),
                user_id=user_id,
                university_id=tenant.university_id,
                student_id=f"student-{index}-{uuid.uuid4().hex[:8]}",
                department_id=tenant.department_id,
                academic_level=" postgraduate ".strip(),
                academic_account_status="active",
            )
        )
        db_session.execute(
            insert(_table("staff_profiles")).values(
                id=_int_id(),
                user_id=user_id,
                university_id=tenant.university_id,
                staff_id=f"staff-{index}-{uuid.uuid4().hex[:8]}",
                department_id=tenant.department_id,
                job_title="Researcher",
            )
        )
    db_session.flush()

    _reject(
        db_session,
        insert(_table("student_profiles")).values(
            id=_int_id(),
            user_id=user_id,
            university_id=university_a.university_id,
            student_id=f"duplicate-{uuid.uuid4().hex}",
            department_id=university_a.department_id,
            academic_level="undergraduate",
            academic_account_status="active",
        ),
    )
    _reject(
        db_session,
        insert(_table("staff_profiles")).values(
            id=_int_id(),
            user_id=user_id,
            university_id=university_a.university_id,
            staff_id=f"duplicate-{uuid.uuid4().hex}",
            department_id=university_a.department_id,
            job_title="Researcher",
        ),
    )
    _reject(
        db_session,
        insert(_table("student_profiles")).values(
            id=_int_id(),
            user_id=user_id,
            university_id=university_a.university_id,
            student_id=f"wrong-department-{uuid.uuid4().hex}",
            department_id=university_b.department_id,
            academic_level="undergraduate",
            academic_account_status="active",
        ),
    )


def test_department_leadership_matches_staff_department(db_session: Session):
    user_id = _add_user(db_session, "leadership")
    tenant = _add_tenant(db_session, "leadership", user_id)
    other_department_id = _add_department(db_session, tenant, "other")
    staff_id = _int_id()
    db_session.execute(
        insert(_table("staff_profiles")).values(
            id=staff_id,
            user_id=user_id,
            university_id=tenant.university_id,
            staff_id=f"leader-{uuid.uuid4().hex}",
            department_id=tenant.department_id,
            job_title="Professor",
        )
    )
    db_session.flush()

    _reject(
        db_session,
        insert(_table("department_leadership")).values(
            id=uuid.uuid4(),
            university_id=tenant.university_id,
            department_id=other_department_id,
            staff_id=staff_id,
            appointed_by_id=user_id,
            started_at=datetime.now(timezone.utc),
        ),
    )


def test_role_history_partial_unique_index_and_check(db_session: Session):
    user_id = _add_user(db_session, "roles")
    tenant = _add_tenant(db_session, "roles", user_id)
    role_id = _int_id()
    suffix = uuid.uuid4().hex
    db_session.execute(
        insert(_table("roles")).values(
            id=role_id,
            code=f"integrity-{suffix}",
            name=f"Integrity Role {suffix}",
            is_active=True,
        )
    )
    assignment = dict(
        university_id=tenant.university_id,
        user_id=user_id,
        role_id=role_id,
        assigned_at=datetime.now(timezone.utc),
    )
    db_session.execute(insert(_table("user_roles")).values(id=_int_id(), **assignment))
    _reject(db_session, insert(_table("user_roles")).values(id=_int_id(), **assignment))

    db_session.execute(
        update(_table("user_roles"))
        .where(_table("user_roles").c.user_id == user_id)
        .values(revoked_at=datetime.now(timezone.utc))
    )
    db_session.execute(insert(_table("user_roles")).values(id=_int_id(), **assignment))
    _reject(
        db_session,
        insert(_table("user_roles")).values(
            id=_int_id(),
            university_id=tenant.university_id,
            user_id=user_id,
            role_id=role_id,
            assigned_at=datetime.now(timezone.utc),
            revoked_at=datetime.now(timezone.utc).replace(year=2000),
        ),
    )


def test_progress_report_milestone_and_project_tenant_keys(db_session: Session):
    user_id = _add_user(db_session, "reports")
    tenant_a = _add_tenant(db_session, "reports-a", user_id)
    tenant_b = _add_tenant(db_session, "reports-b", user_id)
    project_a = _add_project_graph(db_session, tenant_a, user_id, "a")
    project_b = _add_project_graph(db_session, tenant_a, user_id, "b")
    db_session.flush()

    valid_report = dict(
        university_id=tenant_a.university_id,
        project_id=project_a.project_id,
        milestone_id=project_a.milestone_id,
        submitter_id=user_id,
        period_start=date.today(),
        period_end=date.today(),
        title="Valid integrity report",
        content="Valid report",
    )
    db_session.execute(insert(_table("progress_reports")).values(id=uuid.uuid4(), **valid_report))
    db_session.flush()

    _reject(
        db_session,
        insert(_table("progress_reports")).values(
            id=uuid.uuid4(),
            **{**valid_report, "project_id": project_b.project_id},
        ),
    )
    _reject(
        db_session,
        insert(_table("progress_reports")).values(
            id=uuid.uuid4(),
            **{**valid_report, "university_id": tenant_b.university_id, "milestone_id": None},
        ),
    )
    db_session.execute(
        insert(_table("progress_reports")).values(
            **{**valid_report, "id": uuid.uuid4(), "milestone_id": None},
        )
    )


def test_postgres_checks_nullability_and_partial_publication_index(db_session: Session):
    user_id = _add_user(db_session, "checks")
    tenant = _add_tenant(db_session, "checks", user_id)

    _reject(
        db_session,
        insert(_table("users")).values(
            id=_int_id(),
            full_name="Invalid Status",
            email=f"invalid-status-{uuid.uuid4().hex}@example.test",
            password_hash="test-only-hash",
            status="not-a-status",
            email_verified=False,
        ),
    )
    case_insensitive_email = f"Case-{uuid.uuid4().hex}@Example.test"
    db_session.execute(
        insert(_table("users")).values(
            id=_int_id(),
            full_name="Case Email One",
            email=case_insensitive_email,
            password_hash="test-only-hash",
            status="active",
            email_verified=False,
        )
    )
    _reject(
        db_session,
        insert(_table("users")).values(
            id=_int_id(),
            full_name="Case Email Two",
            email=case_insensitive_email.swapcase(),
            password_hash="test-only-hash",
            status="active",
            email_verified=False,
        ),
    )
    publication = dict(
        university_id=tenant.university_id,
        title="Integrity Publication",
        publication_type="journal",
        normalized_doi=f"10.0000/{uuid.uuid4().hex}",
        submitter_id=user_id,
    )
    db_session.execute(insert(_table("publications")).values(id=uuid.uuid4(), **publication))
    _reject(db_session, insert(_table("publications")).values(id=uuid.uuid4(), **publication))
    _reject(
        db_session,
        insert(_table("publications")).values(
            id=uuid.uuid4(),
            university_id=tenant.university_id,
            title="Missing required submitter",
            publication_type="journal",
            submitter_id=None,
        ),
    )


def test_postgres_audit_identifier_types_and_constraints(db_session: Session):
    user_id = _add_user(db_session, "audit")
    tenant = _add_tenant(db_session, "audit", user_id)
    uuid_identifier = uuid.uuid4()
    audit_values = dict(
        university_id=tenant.university_id,
        acting_user_id=user_id,
        action="integrity-test",
        entity_type="research_projects",
    )

    db_session.execute(
        insert(_table("audit_logs")).values(
            id=uuid.uuid4(),
            **audit_values,
            entity_uuid=uuid_identifier,
            entity_integer=None,
        )
    )
    db_session.execute(
        insert(_table("audit_logs")).values(
            id=uuid.uuid4(),
            **{**audit_values, "entity_type": "users"},
            entity_uuid=None,
            entity_integer=user_id,
        )
    )
    db_session.flush()

    _reject(
        db_session,
        insert(_table("audit_logs")).values(
            id=uuid.uuid4(),
            **audit_values,
            entity_uuid=uuid_identifier,
            entity_integer=user_id,
        ),
    )
    _reject(
        db_session,
        insert(_table("audit_logs")).values(
            id=uuid.uuid4(),
            **{**audit_values, "entity_type": "users"},
            entity_uuid=uuid_identifier,
            entity_integer=None,
        ),
    )
    _reject(
        db_session,
        insert(_table("audit_logs")).values(
            id=uuid.uuid4(),
            **audit_values,
            entity_uuid=None,
            entity_integer=user_id,
        ),
    )


def test_postgres_notification_preferences_tenant_scope_and_constraints(db_session: Session):
    user_id = _add_user(db_session, "notification-preferences")
    other_user_id = _add_user(db_session, "notification-preferences-other")
    tenant_a = _add_tenant(db_session, "notification-a", user_id)
    tenant_b = _add_tenant(db_session, "notification-b", user_id)
    other_tenant = _add_tenant(db_session, "notification-other", other_user_id)
    preferences = _table("notification_preferences")

    preference_id = uuid.uuid4()
    db_session.execute(
        insert(preferences).values(
            id=preference_id,
            user_id=user_id,
            university_id=tenant_a.university_id,
            notification_type="overdue_milestone",
        )
    )
    db_session.execute(
        insert(preferences).values(
            id=uuid.uuid4(),
            user_id=user_id,
            university_id=tenant_b.university_id,
            notification_type="overdue_milestone",
        )
    )
    db_session.flush()
    stored = db_session.execute(
        select(preferences).where(preferences.c.id == preference_id)
    ).mappings().one()
    assert stored["channel"] == "in_app"
    assert stored["is_enabled"] is True

    _reject(
        db_session,
        insert(preferences).values(
            id=uuid.uuid4(),
            user_id=user_id,
            university_id=tenant_a.university_id,
            notification_type="overdue_milestone",
            channel="in_app",
        ),
    )
    _reject(
        db_session,
        insert(preferences).values(
            id=uuid.uuid4(),
            user_id=other_user_id,
            university_id=tenant_a.university_id,
            notification_type="student_inactivity",
        ),
    )
    _reject(
        db_session,
        insert(preferences).values(
            id=uuid.uuid4(),
            user_id=user_id,
            university_id=tenant_a.university_id,
            notification_type="student_inactivity",
            channel="email",
        ),
    )
    _reject(
        db_session,
        insert(preferences).values(
            id=uuid.uuid4(),
            user_id=user_id,
            university_id=tenant_a.university_id,
            notification_type="   ",
        ),
    )
    _reject(
        db_session,
        insert(preferences).values(
            id=uuid.uuid4(),
            user_id=user_id,
            university_id=tenant_a.university_id,
            notification_type="student_inactivity",
            is_enabled=None,
        ),
    )

    db_session.execute(
        update(_table("university_memberships"))
        .where(
            _table("university_memberships").c.user_id == user_id,
            _table("university_memberships").c.university_id == tenant_a.university_id,
        )
        .values(is_active=False)
    )
    retained = db_session.execute(
        select(preferences.c.id).where(preferences.c.id == preference_id)
    ).scalar_one()
    assert retained == preference_id


def test_approval_version_triggers_and_cross_version_action_fks(db_session: Session):
    user_id = _add_user(db_session, "approval")
    tenant = _add_tenant(db_session, "approval", user_id)
    workflow_id = uuid.uuid4()
    version_one = uuid.uuid4()
    version_two = uuid.uuid4()
    step_one = uuid.uuid4()
    step_two = uuid.uuid4()
    instance_id = uuid.uuid4()

    db_session.execute(
        insert(_table("approval_workflows")).values(
            id=workflow_id,
            university_id=tenant.university_id,
            workflow_type="integrity",
            department_id=None,
            created_by_id=user_id,
        )
    )
    db_session.execute(
        insert(_table("approval_workflow_versions")).values(
            id=version_one,
            workflow_id=workflow_id,
            university_id=tenant.university_id,
            version_number=1,
            publication_state="draft",
        )
    )
    db_session.execute(
        insert(_table("approval_workflow_steps")).values(
            id=step_one,
            workflow_version_id=version_one,
            workflow_id=workflow_id,
            university_id=tenant.university_id,
            step_number=1,
            name="First step",
            required_approvals=1,
            is_mandatory=True,
        )
    )
    db_session.execute(
        update(_table("approval_workflow_versions"))
        .where(_table("approval_workflow_versions").c.id == version_one)
        .values(publication_state="published")
    )
    db_session.execute(
        update(_table("approval_workflows"))
        .where(_table("approval_workflows").c.id == workflow_id)
        .values(active_version_id=version_one)
    )
    db_session.execute(
        insert(_table("approval_workflow_versions")).values(
            id=version_two,
            workflow_id=workflow_id,
            university_id=tenant.university_id,
            version_number=2,
            publication_state="draft",
        )
    )
    db_session.execute(
        insert(_table("approval_workflow_steps")).values(
            id=step_two,
            workflow_version_id=version_two,
            workflow_id=workflow_id,
            university_id=tenant.university_id,
            step_number=1,
            name="Second version step",
            required_approvals=1,
            is_mandatory=True,
        )
    )
    db_session.execute(
        insert(_table("approval_instances")).values(
            id=instance_id,
            workflow_version_id=version_one,
            workflow_id=workflow_id,
            university_id=tenant.university_id,
            target_entity_type="test",
            target_entity_id=uuid.uuid4(),
            status="pending",
            initiated_by_id=user_id,
        )
    )
    db_session.execute(
        insert(_table("approval_actions")).values(
            id=uuid.uuid4(),
            instance_id=instance_id,
            step_id=step_one,
            workflow_version_id=version_one,
            workflow_id=workflow_id,
            university_id=tenant.university_id,
            acting_user_id=user_id,
            decision="approved",
        )
    )
    db_session.flush()

    versions = _table("approval_workflow_versions")
    steps = _table("approval_workflow_steps")
    workflows = _table("approval_workflows")
    actions = _table("approval_actions")
    _reject(db_session, update(versions).where(versions.c.id == version_one).values(version_number=9))
    _reject(db_session, delete(versions).where(versions.c.id == version_one))
    _reject(
        db_session,
        insert(steps).values(
            id=uuid.uuid4(),
            workflow_version_id=version_one,
            workflow_id=workflow_id,
            university_id=tenant.university_id,
            step_number=9,
            name="Published insert",
            required_approvals=1,
            is_mandatory=True,
        ),
    )
    _reject(
        db_session,
        update(steps).where(steps.c.id == step_one).values(workflow_version_id=version_two),
    )
    _reject(
        db_session,
        update(workflows).where(workflows.c.id == workflow_id).values(active_version_id=version_two),
    )
    _reject(
        db_session,
        update(workflows).where(workflows.c.id == workflow_id).values(workflow_type="changed"),
    )
    _reject(
        db_session,
        insert(actions).values(
            id=uuid.uuid4(),
            instance_id=instance_id,
            step_id=step_two,
            workflow_version_id=version_one,
            workflow_id=workflow_id,
            university_id=tenant.university_id,
            acting_user_id=user_id,
            decision="approved",
        ),
    )
