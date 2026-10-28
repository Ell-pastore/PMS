"""Split polymorphic audit identifiers by primary-key type.

Revision ID: c4d6e8f0a1b2
Revises: 7f2e6e8c4a91
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d6e8f0a1b2"
down_revision: Union[str, None] = "7f2e6e8c4a91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INTEGER_ENTITY_TYPES = (
    "'users', 'roles', 'user_roles', 'faculties', 'departments', 'student_profiles', 'staff_profiles'"
)
ENTITY_TYPE_CHECK = f"""
    (entity_uuid IS NULL AND entity_integer IS NULL)
    OR (
        entity_uuid IS NULL
        AND entity_integer IS NOT NULL
        AND entity_type IN ({INTEGER_ENTITY_TYPES})
    )
    OR (
        entity_uuid IS NOT NULL
        AND entity_integer IS NULL
        AND entity_type NOT IN ({INTEGER_ENTITY_TYPES})
    )
"""


def upgrade() -> None:
    # The old column could only contain UUIDs.  Refuse to reinterpret a legacy
    # value as an integer entity identifier based solely on entity_type.
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                      FROM audit_logs
                     WHERE entity_id IS NOT NULL
                       AND entity_type IN ({INTEGER_ENTITY_TYPES})
                ) THEN
                    RAISE EXCEPTION
                        'Audit identifier migration found legacy UUID values for integer entity types';
                END IF;
            END $$;
            """
        )
    )

    op.add_column("audit_logs", sa.Column("entity_uuid", sa.Uuid(), nullable=True))
    op.add_column("audit_logs", sa.Column("entity_integer", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE audit_logs SET entity_uuid = entity_id WHERE entity_id IS NOT NULL"
        )
    )
    op.drop_index("ix_audit_logs_entity_event", table_name="audit_logs")
    op.drop_column("audit_logs", "entity_id")
    op.create_check_constraint(
        "ck_audit_logs_entity_identifier_type",
        "audit_logs",
        ENTITY_TYPE_CHECK,
    )
    op.create_index(
        "ix_audit_logs_entity_uuid_event",
        "audit_logs",
        ["entity_type", "entity_uuid", "event_at"],
        unique=False,
        postgresql_where=sa.text("entity_uuid IS NOT NULL"),
    )
    op.create_index(
        "ix_audit_logs_entity_integer_event",
        "audit_logs",
        ["entity_type", "entity_integer", "event_at"],
        unique=False,
        postgresql_where=sa.text("entity_integer IS NOT NULL"),
    )


def downgrade() -> None:
    # Integer identifiers cannot be losslessly converted back to UUIDs.
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM audit_logs WHERE entity_integer IS NOT NULL
                ) THEN
                    RAISE EXCEPTION
                        'Audit identifier downgrade is unsafe while integer identifiers exist';
                END IF;
            END $$;
            """
        )
    )

    op.drop_index("ix_audit_logs_entity_integer_event", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_uuid_event", table_name="audit_logs")
    op.drop_constraint(
        "ck_audit_logs_entity_identifier_type",
        "audit_logs",
        type_="check",
    )
    op.add_column("audit_logs", sa.Column("entity_id", sa.Uuid(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE audit_logs SET entity_id = entity_uuid WHERE entity_uuid IS NOT NULL"
        )
    )
    op.drop_column("audit_logs", "entity_integer")
    op.drop_column("audit_logs", "entity_uuid")
    op.create_index(
        "ix_audit_logs_entity_event",
        "audit_logs",
        ["entity_type", "entity_id", "event_at"],
        unique=False,
    )
