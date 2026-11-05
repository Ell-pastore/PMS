"""Tests for authentication, authorization, users, roles, and security."""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.core.security import verify_password
from backend.app.models.User import User
from backend.tests.conftest import (
    create_university_admin_helper,
    create_user_helper,
    make_auth_headers,
)


def test_user_registration_success(client: TestClient, db_session: Session):
    email = f"newuser_{uuid.uuid4().hex[:6]}@example.com"
    payload = {
        "email": email,
        "full_name": "New Registered User",
        "password": "Password123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert data["full_name"] == "New Registered User"
    assert "password_hash" not in data

    # Verify password was properly hashed in database
    db_user = db_session.query(User).filter(User.email == email).first()
    assert db_user is not None
    assert verify_password("Password123!", db_user.password_hash)


def test_user_registration_duplicate_email(client: TestClient, db_session: Session):
    existing = create_user_helper(db_session, email="duplicate@example.com")
    payload = {
        "email": existing.email,
        "full_name": "Duplicate User",
        "password": "Password123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["error"] == "DuplicateResourceError"


def test_login_success_and_failure(client: TestClient, db_session: Session):
    password = "MySecretPassword123!"
    user = create_user_helper(db_session, password=password)

    # Success
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
    )
    assert resp.status_code == 200
    token_data = resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # Wrong password
    resp_fail = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "WrongPassword!"},
    )
    assert resp_fail.status_code == 401
    assert resp_fail.json()["error"] == "UnauthorizedError"

    # Nonexistent email
    resp_unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent_pms@example.com", "password": password},
    )
    assert resp_unknown.status_code == 401


def test_auth_me_endpoint(client: TestClient, db_session: Session):
    user = create_user_helper(db_session)
    headers = make_auth_headers(user)

    # Authorized
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == user.id
    assert resp.json()["email"] == user.email

    # Unauthorized (no token)
    resp_anon = client.get("/api/v1/auth/me")
    assert resp_anon.status_code == 401


def test_users_crud_and_pagination(client: TestClient, db_session: Session):
    admin, _, headers = create_university_admin_helper(db_session)

    # List users with pagination (requires university_admin role)
    resp = client.get("/api/v1/users?page=1&page_size=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert data["page"] == 1
    assert data["page_size"] == 5

    # Retrieve specific user (self-access allowed)
    resp_user = client.get(f"/api/v1/users/{admin.id}", headers=headers)
    assert resp_user.status_code == 200
    assert resp_user.json()["id"] == admin.id

    # Update user via PATCH (self-access allowed)
    update_payload = {"full_name": "Updated Admin Name"}
    resp_up = client.patch(f"/api/v1/users/{admin.id}", json=update_payload, headers=headers)
    assert resp_up.status_code == 200
    assert resp_up.json()["full_name"] == "Updated Admin Name"

    # 404 for missing user
    resp_404 = client.get("/api/v1/users/9999999", headers=headers)
    assert resp_404.status_code == 404
    assert resp_404.json()["error"] == "NotFoundError"


def test_roles_and_permissions(client: TestClient, db_session: Session):
    admin, _, headers = create_university_admin_helper(db_session)

    # Create role (requires code + name)
    suffix = uuid.uuid4().hex[:6]
    role_code = f"ROLE_{suffix.upper()}"
    role_name = f"Role {suffix}"
    resp_role = client.post(
        "/api/v1/roles",
        json={"code": role_code, "name": role_name, "description": "Test role"},
        headers=headers,
    )
    assert resp_role.status_code == 201
    role_id = resp_role.json()["id"]

    # Duplicate role code should fail with 409
    resp_role_dup = client.post(
        "/api/v1/roles",
        json={"code": role_code, "name": f"AltName_{suffix}", "description": "Dup"},
        headers=headers,
    )
    assert resp_role_dup.status_code == 409

    # Create permission (requires code)
    perm_code = f"perm.{suffix}"
    resp_perm = client.post(
        "/api/v1/roles/permissions",
        json={"code": perm_code, "description": "Test permission"},
        headers=headers,
    )
    assert resp_perm.status_code == 201
    perm_id = resp_perm.json()["id"]

    # Assign permission to role
    resp_assign = client.post(
        "/api/v1/roles/permissions/assign",
        json={"role_id": role_id, "permission_id": perm_id},
        headers=headers,
    )
    assert resp_assign.status_code == 201
    assign_id = resp_assign.json()["id"]

    # Duplicate assignment should fail with 409
    resp_dup = client.post(
        "/api/v1/roles/permissions/assign",
        json={"role_id": role_id, "permission_id": perm_id},
        headers=headers,
    )
    assert resp_dup.status_code == 409

    # Delete assignment
    resp_del = client.delete(
        f"/api/v1/roles/permissions/assignments/{assign_id}",
        headers=headers,
    )
    assert resp_del.status_code == 200
