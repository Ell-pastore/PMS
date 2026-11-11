"""Explicit, application-controlled reference-data seeding helpers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .role import Role


INITIAL_ROLE_CODES = (
    "student",
    "supervisor",
    "department_head",
    "research_admin",
    "grant_admin",
    "university_admin",
    "superadmin",
)


def seed_initial_roles(session: Session) -> None:
    """Insert the standard roles when explicitly invoked by an operator.

    This helper is intentionally not called during application import or FastAPI
    startup. Privileged roles are reference data and must still be assigned by
    an authorized workflow. ``superadmin`` is seeded so the cross-tenant bypass
    in ``core/dependencies.py`` can be exercised once the role is assigned to
    a user, but seeding does not grant it to anyone.
    """

    existing_codes = set(session.scalars(select(Role.code)).all())
    for code in INITIAL_ROLE_CODES:
        if code not in existing_codes:
            session.add(Role(code=code, name=code.replace("_", " ").title()))
