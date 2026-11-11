"""Pytest configuration and shared fixtures for PMS API and database tests."""

from __future__ import annotations

import os
import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.core.security import create_access_token, hash_password
from backend.app.main import app
from backend.app.models import Role, University, UniversityMembership, User, UserRole

TEST_DATABASE_ENV = "PMS_TEST_DATABASE_URL"
DEVELOPMENT_DATABASE = "pms_db"
EXPECTED_ALEMBIC_HEAD = "b1c2d3e4f5a6"


@pytest.fixture(scope="session")
def postgres_engine() -> Generator[Engine, None, None]:
    raw_url = os.environ.get(TEST_DATABASE_ENV)
    if not raw_url:
        pytest.skip(f"{TEST_DATABASE_ENV} is not configured; live PostgreSQL tests skipped")

    parsed_url = make_url(raw_url)
    if not parsed_url.database:
        pytest.fail(f"{TEST_DATABASE_ENV} must include an explicit database name")
    if parsed_url.database == DEVELOPMENT_DATABASE:
        pytest.fail(f"Live API tests refuse the development database {DEVELOPMENT_DATABASE!r}")

    engine = create_engine(raw_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            current_database = connection.scalar(text("SELECT current_database()"))
            if current_database == DEVELOPMENT_DATABASE:
                pytest.fail("The explicit test URL resolved to the development database")
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            if revision != EXPECTED_ALEMBIC_HEAD:
                pytest.fail(f"Test database revision {revision} != expected {EXPECTED_ALEMBIC_HEAD}")
    except Exception:
        engine.dispose()
        raise

    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(postgres_engine: Engine) -> Generator[Session, None, None]:
    connection = postgres_engine.connect()
    outer_transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )

    try:
        yield session
    finally:
        session.close()
        if outer_transaction.is_active:
            outer_transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


def create_user_helper(
    db: Session,
    email: str | None = None,
    full_name: str = "Test User",
    password: str = "SecurePass123!",
    status: str = "active",
) -> User:
    if email is None:
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        status=status,
        email_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_university_helper(
    db: Session,
    name: str = "Test University",
    code: str | None = None,
) -> University:
    if code is None:
        code = f"TU-{uuid.uuid4().hex[:6].upper()}"
    univ = University(
        name=name,
        code=code,
        is_active=True,
    )
    db.add(univ)
    db.commit()
    db.refresh(univ)
    return univ


def create_membership_helper(
    db: Session,
    university_id: uuid.UUID,
    user_id: int,
    is_active: bool = True,
) -> UniversityMembership:
    membership = UniversityMembership(
        university_id=university_id,
        user_id=user_id,
        is_active=is_active,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def make_auth_headers(
    user: User,
    university_id: uuid.UUID | None = None,
) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id), "email": user.email})
    headers = {"Authorization": f"Bearer {token}"}
    if university_id is not None:
        headers["X-University-ID"] = str(university_id)
    return headers


def assign_role_helper(db: Session, university_id: uuid.UUID, user_id: int, role_code: str) -> UserRole:
    """Assign a role (reference data, upserted by code) to a user in a university.

    Idempotent: an already-assigned (non-revoked) role returns the existing
    UserRole row instead of creating a duplicate.
    """
    role = db.scalar(select(Role).where(Role.code == role_code))
    if not role:
        role = Role(code=role_code, name=role_code.replace("_", " ").title())
        db.add(role)
        db.flush()

    existing = db.scalar(
        select(UserRole).where(
            UserRole.university_id == university_id,
            UserRole.user_id == user_id,
            UserRole.role_id == role.id,
            UserRole.revoked_at.is_(None),
        )
    )
    if existing:
        return existing

    assignment = UserRole(
        university_id=university_id,
        user_id=user_id,
        role_id=role.id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def create_university_admin_helper(
    db: Session,
    email: str | None = None,
    full_name: str = "University Admin",
    university_name: str = "Admin University",
) -> tuple[User, University, dict[str, str]]:
    """Create a user, university, membership, and university_admin role assignment.

    Returns (user, university, auth_headers_with_university_id).
    """
    user = create_user_helper(db, email=email, full_name=full_name)
    univ = create_university_helper(db, name=university_name)
    create_membership_helper(db, univ.id, user.id)
    assign_role_helper(db, univ.id, user.id, "university_admin")
    headers = make_auth_headers(user, univ.id)
    return user, univ, headers
