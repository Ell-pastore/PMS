"""Complete current PMS schema after the original seven-table baseline.

Revision ID: 7f2e6e8c4a91
Revises: 3a5bb0b54636
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '7f2e6e8c4a91'
down_revision: Union[str, None] = '3a5bb0b54636'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The baseline has no tenant key on these tables.  Refuse to guess a tenant
    # for existing rows; a separate, reviewed data migration is required first.
    op.execute(sa.text("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM faculties)
               OR EXISTS (SELECT 1 FROM departments)
               OR EXISTS (SELECT 1 FROM user_roles)
               OR EXISTS (SELECT 1 FROM staff_profiles)
               OR EXISTS (SELECT 1 FROM student_profiles) THEN
                RAISE EXCEPTION 'PMS tenant migration requires an explicit backfill for existing baseline rows';
            END IF;
        END $$;
    """))

    # Create the new roots before adding tenant foreign keys to baseline tables.
    op.create_table('permissions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('code', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_table('universities',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_table('university_memberships',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('university_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('university_id', 'user_id', name='uq_university_memberships_university_user'),
        sa.UniqueConstraint('user_id', 'university_id', name='uq_university_memberships_user_university')
    )

    # Bring the seven baseline tables to their current tenant-aware definitions.
    op.add_column('faculties', sa.Column('university_id', sa.Uuid(), nullable=False))
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('departments', sa.Column('university_id', sa.Uuid(), nullable=False))
    op.add_column('user_roles', sa.Column('university_id', sa.Uuid(), nullable=False))
    op.add_column('user_roles', sa.Column('assigned_by_id', sa.Integer(), nullable=True))
    op.add_column('user_roles', sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('staff_profiles', sa.Column('university_id', sa.Uuid(), nullable=False))
    op.add_column('staff_profiles', sa.Column('academic_designation', sa.String(length=128), nullable=True))
    op.add_column('staff_profiles', sa.Column('gender', sa.String(length=32), nullable=True))
    op.add_column('student_profiles', sa.Column('university_id', sa.Uuid(), nullable=False))
    op.add_column('student_profiles', sa.Column('gender', sa.String(length=32), nullable=True))
    op.add_column('student_profiles', sa.Column('enrollment_date', sa.Date(), nullable=True))
    op.add_column('student_profiles', sa.Column('academic_account_status', sa.String(length=32), server_default='active', nullable=False))

    op.drop_constraint('faculties_code_key', 'faculties', type_='unique')
    op.drop_constraint('departments_faculty_id_fkey', 'departments', type_='foreignkey')
    op.drop_constraint('staff_profiles_department_id_fkey', 'staff_profiles', type_='foreignkey')
    op.drop_constraint('student_profiles_department_id_fkey', 'student_profiles', type_='foreignkey')
    op.drop_constraint('uq_departments_faculty_name', 'departments', type_='unique')
    op.drop_constraint('departments_code_key', 'departments', type_='unique')
    op.drop_constraint('uq_user_roles_user_role', 'user_roles', type_='unique')
    op.drop_constraint('staff_profiles_staff_id_key', 'staff_profiles', type_='unique')
    op.drop_constraint('staff_profiles_user_id_key', 'staff_profiles', type_='unique')
    op.drop_constraint('student_profiles_student_id_key', 'student_profiles', type_='unique')
    op.drop_constraint('student_profiles_user_id_key', 'student_profiles', type_='unique')

    op.create_unique_constraint('uq_faculties_id_university', 'faculties', ['id', 'university_id'])
    op.create_unique_constraint('uq_faculties_university_code', 'faculties', ['university_id', 'code'])
    op.create_foreign_key('fk_faculties_university', 'faculties', 'universities', ['university_id'], ['id'], ondelete='RESTRICT')
    op.create_unique_constraint('uq_departments_id_university', 'departments', ['id', 'university_id'])
    op.create_unique_constraint('uq_departments_faculty_name', 'departments', ['university_id', 'faculty_id', 'name'])
    op.create_unique_constraint('uq_departments_faculty_code', 'departments', ['university_id', 'faculty_id', 'code'])
    op.create_foreign_key('fk_departments_university', 'departments', 'universities', ['university_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_departments_faculty_university', 'departments', 'faculties', ['faculty_id', 'university_id'], ['id', 'university_id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_user_roles_university', 'user_roles', 'universities', ['university_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_user_roles_assigned_by_user', 'user_roles', 'users', ['assigned_by_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_user_roles_membership', 'user_roles', 'university_memberships', ['university_id', 'user_id'], ['university_id', 'user_id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_user_roles_assigned_by_membership', 'user_roles', 'university_memberships', ['university_id', 'assigned_by_id'], ['university_id', 'user_id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_staff_profiles_university', 'staff_profiles', 'universities', ['university_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_staff_profiles_membership', 'staff_profiles', 'university_memberships', ['user_id', 'university_id'], ['user_id', 'university_id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_staff_profiles_department_university', 'staff_profiles', 'departments', ['department_id', 'university_id'], ['id', 'university_id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_student_profiles_university', 'student_profiles', 'universities', ['university_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_student_profiles_membership', 'student_profiles', 'university_memberships', ['user_id', 'university_id'], ['user_id', 'university_id'], ondelete='RESTRICT')
    op.create_foreign_key('fk_student_profiles_department_university', 'student_profiles', 'departments', ['department_id', 'university_id'], ['id', 'university_id'], ondelete='RESTRICT')
    op.create_unique_constraint('uq_staff_profiles_user_university', 'staff_profiles', ['user_id', 'university_id'])
    op.create_unique_constraint('uq_staff_profiles_id_university', 'staff_profiles', ['id', 'university_id'])
    op.create_unique_constraint('uq_staff_profiles_id_department_university', 'staff_profiles', ['id', 'department_id', 'university_id'])
    op.create_unique_constraint('uq_staff_profiles_university_staff_id', 'staff_profiles', ['university_id', 'staff_id'])
    op.create_check_constraint('ck_staff_profiles_gender', 'staff_profiles', "gender IS NULL OR gender IN ('female', 'male', 'non_binary', 'undisclosed')")
    op.create_unique_constraint('uq_student_profiles_user_university', 'student_profiles', ['user_id', 'university_id'])
    op.create_unique_constraint('uq_student_profiles_id_university', 'student_profiles', ['id', 'university_id'])
    op.create_unique_constraint('uq_student_profiles_university_student_id', 'student_profiles', ['university_id', 'student_id'])
    op.create_check_constraint('ck_student_profiles_gender', 'student_profiles', "gender IS NULL OR gender IN ('female', 'male', 'non_binary', 'undisclosed')")
    op.create_check_constraint('ck_student_profiles_account_status', 'student_profiles', "academic_account_status IN ('active', 'inactive', 'graduated', 'suspended')")
    op.create_check_constraint('ck_user_roles_revoked_at', 'user_roles', 'revoked_at IS NULL OR revoked_at >= assigned_at')
    op.create_index('uq_user_roles_active_assignment', 'user_roles', ['university_id', 'user_id', 'role_id'], unique=True, postgresql_where=sa.text('revoked_at IS NULL'))

    op.create_table('account_verifications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('verification_type', sa.String(length=32), nullable=False),
    sa.Column('token_digest', sa.String(length=255), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_digest')
    )

    op.create_table('role_permissions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.Column('permission_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permissions_role_permission')
    )

    op.create_table('audit_logs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('acting_user_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=128), nullable=False),
    sa.Column('entity_type', sa.String(length=128), nullable=False),
    sa.Column('entity_id', sa.Uuid(), nullable=True),
    sa.Column('event_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('request_id', sa.String(length=128), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.ForeignKeyConstraint(['acting_user_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_audit_logs_actor_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['acting_user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('grant_opportunities',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('funding_organization', sa.String(length=255), nullable=False),
    sa.Column('eligibility_criteria', sa.Text(), nullable=True),
    sa.Column('application_opens_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('application_closes_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('min_funding_amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('max_funding_amount', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'open', 'closed', 'awarded', 'cancelled')", name='ck_grant_opportunities_status'),
    sa.CheckConstraint('application_closes_at >= application_opens_at', name='ck_grant_opportunities_dates'),
    sa.CheckConstraint('max_funding_amount IS NULL OR max_funding_amount >= min_funding_amount', name='ck_grant_opportunities_max_amount'),
    sa.CheckConstraint('min_funding_amount >= 0', name='ck_grant_opportunities_min_amount'),
    sa.ForeignKeyConstraint(['created_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_grant_opportunities_created_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'university_id', name='uq_grant_opportunities_id_university')
    )

    op.create_table('notifications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('recipient_id', sa.Integer(), nullable=False),
    sa.Column('notification_type', sa.String(length=64), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('entity_type', sa.String(length=128), nullable=True),
    sa.Column('entity_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['recipient_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_notifications_recipient_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('publications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('abstract', sa.Text(), nullable=True),
    sa.Column('publication_type', sa.String(length=64), nullable=False),
    sa.Column('doi', sa.String(length=255), nullable=True),
    sa.Column('normalized_doi', sa.String(length=255), nullable=True),
    sa.Column('journal', sa.String(length=255), nullable=True),
    sa.Column('publisher', sa.String(length=255), nullable=True),
    sa.Column('publication_date', sa.Date(), nullable=True),
    sa.Column('volume', sa.String(length=64), nullable=True),
    sa.Column('issue', sa.String(length=64), nullable=True),
    sa.Column('page_range', sa.String(length=64), nullable=True),
    sa.Column('url', sa.String(length=2048), nullable=True),
    sa.Column('verification_status', sa.String(length=32), server_default='draft', nullable=False),
    sa.Column('submitter_id', sa.Integer(), nullable=False),
    sa.Column('verifier_id', sa.Integer(), nullable=True),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("verification_status IN ('draft', 'submitted', 'under_verification', 'verified', 'rejected', 'withdrawn')", name='ck_publications_status'),
    sa.ForeignKeyConstraint(['submitter_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_publications_submitter_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['submitter_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['verifier_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_publications_verifier_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['verifier_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'university_id', name='uq_publications_id_university')
    )

    op.create_table('stored_files',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('uploader_id', sa.Integer(), nullable=False),
    sa.Column('storage_key', sa.String(length=1024), nullable=False),
    sa.Column('original_filename', sa.String(length=512), nullable=False),
    sa.Column('content_type', sa.String(length=255), nullable=False),
    sa.Column('file_size_bytes', sa.Integer(), nullable=False),
    sa.Column('checksum', sa.String(length=128), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('file_size_bytes >= 0', name='ck_stored_files_size'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['uploader_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_stored_files_uploader_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['uploader_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'university_id', name='uq_stored_files_id_university'),
    sa.UniqueConstraint('storage_key')
    )

    op.create_table('system_settings',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('setting_key', sa.String(length=128), nullable=False),
    sa.Column('setting_value', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('updated_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['updated_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_system_settings_updated_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('university_id', 'setting_key', name='uq_system_settings_university_key')
    )

    op.create_table('university_settings',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('max_supervisors_per_project', sa.Integer(), nullable=False),
    sa.Column('max_active_projects_per_student', sa.Integer(), nullable=False),
    sa.Column('max_active_supervisees_per_supervisor', sa.Integer(), nullable=False),
    sa.Column('student_inactivity_days', sa.Integer(), nullable=False),
    sa.Column('milestone_reminder_days', sa.Integer(), nullable=False),
    sa.Column('default_proposal_review_days', sa.Integer(), nullable=False),
    sa.Column('updated_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('default_proposal_review_days > 0', name='ck_university_settings_review'),
    sa.CheckConstraint('max_active_projects_per_student > 0', name='ck_university_settings_projects'),
    sa.CheckConstraint('max_active_supervisees_per_supervisor > 0', name='ck_university_settings_supervisees'),
    sa.CheckConstraint('max_supervisors_per_project > 0', name='ck_university_settings_supervisors'),
    sa.CheckConstraint('milestone_reminder_days >= 0', name='ck_university_settings_reminder'),
    sa.CheckConstraint('student_inactivity_days > 0', name='ck_university_settings_inactivity'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['updated_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_university_settings_updated_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('university_id')
    )

    op.create_table('alert_rules',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=True),
    sa.Column('rule_type', sa.String(length=64), nullable=False),
    sa.Column('threshold_value', sa.Integer(), nullable=True),
    sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('is_enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("rule_type IN ('student_inactivity', 'overdue_milestone', 'duplicate_topic')", name='ck_alert_rules_type'),
    sa.CheckConstraint('threshold_value IS NULL OR threshold_value >= 0', name='ck_alert_rules_threshold'),
    sa.ForeignKeyConstraint(['created_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_alert_rules_created_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['department_id', 'university_id'], ['departments.id', 'departments.university_id'], name='fk_alert_rules_department_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'university_id', name='uq_alert_rules_id_university')
    )

    op.create_table('approval_workflows',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('workflow_type', sa.String(length=128), nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=True),
    sa.Column('active_version_id', sa.Uuid(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_approval_workflows_created_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['department_id', 'university_id'], ['departments.id', 'departments.university_id'], name='fk_approval_workflows_department_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'university_id', name='uq_approval_workflows_id_university')
    )

    op.create_table('department_settings',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=False),
    sa.Column('max_supervisors_per_project', sa.Integer(), nullable=True),
    sa.Column('max_active_projects_per_student', sa.Integer(), nullable=True),
    sa.Column('max_active_supervisees_per_supervisor', sa.Integer(), nullable=True),
    sa.Column('student_inactivity_days', sa.Integer(), nullable=True),
    sa.Column('milestone_reminder_days', sa.Integer(), nullable=True),
    sa.Column('default_proposal_review_days', sa.Integer(), nullable=True),
    sa.Column('updated_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('default_proposal_review_days IS NULL OR default_proposal_review_days > 0', name='ck_department_settings_review'),
    sa.CheckConstraint('max_active_projects_per_student IS NULL OR max_active_projects_per_student > 0', name='ck_department_settings_projects'),
    sa.CheckConstraint('max_active_supervisees_per_supervisor IS NULL OR max_active_supervisees_per_supervisor > 0', name='ck_department_settings_supervisees'),
    sa.CheckConstraint('max_supervisors_per_project IS NULL OR max_supervisors_per_project > 0', name='ck_department_settings_supervisors'),
    sa.CheckConstraint('milestone_reminder_days IS NULL OR milestone_reminder_days >= 0', name='ck_department_settings_reminder'),
    sa.CheckConstraint('student_inactivity_days IS NULL OR student_inactivity_days > 0', name='ck_department_settings_inactivity'),
    sa.ForeignKeyConstraint(['department_id', 'university_id'], ['departments.id', 'departments.university_id'], name='fk_department_settings_department_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['updated_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_department_settings_updated_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('department_id', name='uq_department_settings_department')
    )

    op.create_table('milestone_templates',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('default_duration_days', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('default_duration_days > 0', name='ck_milestone_templates_duration'),
    sa.ForeignKeyConstraint(['created_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_milestone_templates_created_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['department_id', 'university_id'], ['departments.id', 'departments.university_id'], name='fk_milestone_templates_department_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'university_id', name='uq_milestone_templates_id_university')
    )

    op.create_table('publication_authors',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('publication_id', sa.Uuid(), nullable=False),
    sa.Column('internal_user_id', sa.Integer(), nullable=True),
    sa.Column('external_author_name', sa.String(length=255), nullable=True),
    sa.Column('external_affiliation', sa.String(length=255), nullable=True),
    sa.Column('author_order', sa.Integer(), nullable=False),
    sa.Column('is_corresponding', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('(internal_user_id IS NOT NULL AND external_author_name IS NULL) OR (internal_user_id IS NULL AND external_author_name IS NOT NULL)', name='ck_publication_authors_identity'),
    sa.CheckConstraint('author_order > 0', name='ck_publication_authors_order_positive'),
    sa.ForeignKeyConstraint(['internal_user_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_publication_authors_internal_user_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['internal_user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['publication_id', 'university_id'], ['publications.id', 'publications.university_id'], name='fk_publication_authors_publication_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('publication_id', 'author_order', name='uq_publication_authors_order')
    )

    op.create_table('publication_reviews',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('publication_id', sa.Uuid(), nullable=False),
    sa.Column('reviewer_id', sa.Integer(), nullable=False),
    sa.Column('decision', sa.String(length=32), nullable=False),
    sa.Column('comments', sa.Text(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("decision IN ('verified', 'rejected', 'revision_requested', 'commented')", name='ck_publication_reviews_decision'),
    sa.ForeignKeyConstraint(['publication_id', 'university_id'], ['publications.id', 'publications.university_id'], name='fk_publication_reviews_publication_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reviewer_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_publication_reviews_reviewer_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('research_topics',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('normalized_title', sa.String(length=500), nullable=False),
    sa.Column('abstract', sa.Text(), nullable=True),
    sa.Column('keywords', sa.Text(), nullable=True),
    sa.Column('department_id', sa.Integer(), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_research_topics_created_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['department_id', 'university_id'], ['departments.id', 'departments.university_id'], name='fk_research_topics_department_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'university_id', name='uq_research_topics_id_university')
    )

    op.create_table('retention_policies',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('record_category', sa.String(length=128), nullable=False),
    sa.Column('retention_days', sa.Integer(), nullable=False),
    sa.Column('post_retention_action', sa.String(length=32), server_default='review', nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=True),
    sa.Column('is_enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("post_retention_action IN ('review', 'archive', 'anonymize', 'delete')", name='ck_retention_policies_action'),
    sa.CheckConstraint('retention_days > 0', name='ck_retention_policies_days'),
    sa.ForeignKeyConstraint(['created_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_retention_policies_created_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['department_id', 'university_id'], ['departments.id', 'departments.university_id'], name='fk_retention_policies_department_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('alert_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('rule_id', sa.Uuid(), nullable=False),
    sa.Column('alert_type', sa.String(length=64), nullable=False),
    sa.Column('target_entity_type', sa.String(length=128), nullable=False),
    sa.Column('target_entity_id', sa.Uuid(), nullable=False),
    sa.Column('severity', sa.String(length=16), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
    sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("severity IN ('info', 'warning', 'critical')", name='ck_alert_events_severity'),
    sa.CheckConstraint("status IN ('active', 'acknowledged', 'resolved', 'dismissed')", name='ck_alert_events_status'),
    sa.ForeignKeyConstraint(['rule_id', 'university_id'], ['alert_rules.id', 'alert_rules.university_id'], name='fk_alert_events_rule_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'university_id', name='uq_alert_events_id_university')
    )

    op.create_table('approval_workflow_versions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('workflow_id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('version_number', sa.Integer(), nullable=False),
    sa.Column('publication_state', sa.String(length=32), server_default='draft', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("publication_state IN ('draft', 'published')", name='ck_approval_workflow_versions_publication_state'),
    sa.CheckConstraint('version_number > 0', name='ck_approval_workflow_versions_number'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['workflow_id', 'university_id'], ['approval_workflows.id', 'approval_workflows.university_id'], name='fk_approval_workflow_versions_workflow_university', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'workflow_id', 'university_id', name='uq_approval_workflow_versions_id_workflow_university'),
    sa.UniqueConstraint('workflow_id', 'version_number', name='uq_approval_workflow_versions_workflow_number')
    )

    op.create_table('department_leadership',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=False),
    sa.Column('staff_id', sa.Integer(), nullable=False),
    sa.Column('appointed_by_id', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('ended_at IS NULL OR ended_at >= started_at', name='ck_department_leadership_dates'),
    sa.ForeignKeyConstraint(['appointed_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_department_leadership_appointed_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['appointed_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['department_id', 'university_id'], ['departments.id', 'departments.university_id'], name='fk_department_leadership_department_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['staff_id', 'department_id', 'university_id'], ['staff_profiles.id', 'staff_profiles.department_id', 'staff_profiles.university_id'], name='fk_department_leadership_staff_department_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('research_proposals',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('topic_id', sa.Uuid(), nullable=False),
    sa.Column('submitting_user_id', sa.Integer(), nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('abstract', sa.Text(), nullable=True),
    sa.Column('research_problem', sa.Text(), nullable=True),
    sa.Column('objectives', sa.Text(), nullable=True),
    sa.Column('methodology', sa.Text(), nullable=True),
    sa.Column('expected_outcomes', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'submitted', 'under_review', 'revision_requested', 'approved', 'rejected', 'withdrawn')", name='ck_research_proposals_status'),
    sa.CheckConstraint("submitted_at IS NULL OR status <> 'draft'", name='ck_research_proposals_submission'),
    sa.ForeignKeyConstraint(['department_id', 'university_id'], ['departments.id', 'departments.university_id'], name='fk_research_proposals_department_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['submitting_user_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_research_proposals_submitter_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['submitting_user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['topic_id', 'university_id'], ['research_topics.id', 'research_topics.university_id'], name='fk_research_proposals_topic_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'university_id', name='uq_research_proposals_id_university')
    )

    op.create_table('approval_instances',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('workflow_version_id', sa.Uuid(), nullable=False),
    sa.Column('workflow_id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('target_entity_type', sa.String(length=128), nullable=False),
    sa.Column('target_entity_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
    sa.Column('initiated_by_id', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("status IN ('pending', 'in_progress', 'approved', 'rejected', 'cancelled')", name='ck_approval_instances_status'),
    sa.ForeignKeyConstraint(['initiated_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_approval_instances_initiator_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['initiated_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['workflow_version_id', 'workflow_id', 'university_id'], ['approval_workflow_versions.id', 'approval_workflow_versions.workflow_id', 'approval_workflow_versions.university_id'], name='fk_approval_instances_version_workflow_university', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'workflow_version_id', 'workflow_id', 'university_id', name='uq_approval_instances_id_version_workflow_university')
    )

    op.create_table('approval_workflow_steps',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('workflow_version_id', sa.Uuid(), nullable=False),
    sa.Column('workflow_id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('step_number', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('required_role_id', sa.Integer(), nullable=True),
    sa.Column('required_approvals', sa.Integer(), server_default='1', nullable=False),
    sa.Column('is_mandatory', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.CheckConstraint('required_approvals > 0', name='ck_approval_workflow_steps_required'),
    sa.CheckConstraint('step_number > 0', name='ck_approval_workflow_steps_number'),
    sa.ForeignKeyConstraint(['required_role_id'], ['roles.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['workflow_version_id', 'workflow_id', 'university_id'], ['approval_workflow_versions.id', 'approval_workflow_versions.workflow_id', 'approval_workflow_versions.university_id'], name='fk_approval_workflow_steps_version_workflow_university', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'workflow_version_id', 'workflow_id', 'university_id', name='uq_approval_workflow_steps_id_version_workflow_university'),
    sa.UniqueConstraint('workflow_version_id', 'step_number', name='uq_approval_workflow_steps_version_number')
    )

    op.create_table('duplicate_topic_candidates',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('alert_event_id', sa.Uuid(), nullable=False),
    sa.Column('topic_a_id', sa.Uuid(), nullable=False),
    sa.Column('topic_b_id', sa.Uuid(), nullable=False),
    sa.Column('review_status', sa.String(length=32), server_default='pending', nullable=False),
    sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('topic_a_id < topic_b_id', name='ck_duplicate_topic_candidates_order'),
    sa.ForeignKeyConstraint(['alert_event_id', 'university_id'], ['alert_events.id', 'alert_events.university_id'], name='fk_duplicate_candidates_alert_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reviewed_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_duplicate_candidates_reviewer_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['topic_a_id', 'university_id'], ['research_topics.id', 'research_topics.university_id'], name='fk_duplicate_candidates_topic_a_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['topic_b_id', 'university_id'], ['research_topics.id', 'research_topics.university_id'], name='fk_duplicate_candidates_topic_b_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('alert_event_id'),
    sa.UniqueConstraint('alert_event_id', name='uq_duplicate_topic_candidates_alert')
    )

    op.create_table('proposal_participants',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('proposal_id', sa.Uuid(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('participation_role', sa.String(length=64), nullable=False),
    sa.Column('is_lead', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.ForeignKeyConstraint(['proposal_id', 'university_id'], ['research_proposals.id', 'research_proposals.university_id'], name='fk_proposal_participants_proposal_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['student_id', 'university_id'], ['student_profiles.id', 'student_profiles.university_id'], name='fk_proposal_participants_student_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('proposal_id', 'student_id', name='uq_proposal_participants_proposal_student')
    )

    op.create_table('proposal_reviews',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('proposal_id', sa.Uuid(), nullable=False),
    sa.Column('reviewer_id', sa.Integer(), nullable=False),
    sa.Column('decision', sa.String(length=32), nullable=False),
    sa.Column('comments', sa.Text(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("decision IN ('approved', 'rejected', 'revision_requested', 'commented')", name='ck_proposal_reviews_decision'),
    sa.ForeignKeyConstraint(['proposal_id', 'university_id'], ['research_proposals.id', 'research_proposals.university_id'], name='fk_proposal_reviews_proposal_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reviewer_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_proposal_reviews_reviewer_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('proposal_revisions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('proposal_id', sa.Uuid(), nullable=False),
    sa.Column('revision_number', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('abstract', sa.Text(), nullable=True),
    sa.Column('research_problem', sa.Text(), nullable=True),
    sa.Column('objectives', sa.Text(), nullable=True),
    sa.Column('methodology', sa.Text(), nullable=True),
    sa.Column('expected_outcomes', sa.Text(), nullable=True),
    sa.Column('submitted_by_id', sa.Integer(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('revision_number > 0', name='ck_proposal_revisions_number'),
    sa.ForeignKeyConstraint(['proposal_id', 'university_id'], ['research_proposals.id', 'research_proposals.university_id'], name='fk_proposal_revisions_proposal_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['submitted_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_proposal_revisions_submitter_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['submitted_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('proposal_id', 'revision_number', name='uq_proposal_revisions_number')
    )

    op.create_table('proposal_status_history',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('proposal_id', sa.Uuid(), nullable=False),
    sa.Column('previous_status', sa.String(length=32), nullable=True),
    sa.Column('new_status', sa.String(length=32), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_proposal_history_actor_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['proposal_id', 'university_id'], ['research_proposals.id', 'research_proposals.university_id'], name='fk_proposal_history_proposal_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('proposal_supervisors',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('proposal_id', sa.Uuid(), nullable=False),
    sa.Column('staff_id', sa.Integer(), nullable=False),
    sa.Column('assigned_by_id', sa.Integer(), nullable=False),
    sa.Column('assignment_role', sa.String(length=32), nullable=False),
    sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("assignment_role IN ('primary', 'co_supervisor')", name='ck_proposal_supervisors_role'),
    sa.CheckConstraint('ended_at IS NULL OR ended_at >= assigned_at', name='ck_proposal_supervisors_dates'),
    sa.ForeignKeyConstraint(['assigned_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_proposal_supervisors_assigned_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['proposal_id', 'university_id'], ['research_proposals.id', 'research_proposals.university_id'], name='fk_proposal_supervisors_proposal_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['staff_id', 'university_id'], ['staff_profiles.id', 'staff_profiles.university_id'], name='fk_proposal_supervisors_staff_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('research_projects',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('proposal_id', sa.Uuid(), nullable=False),
    sa.Column('department_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('abstract', sa.Text(), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('expected_end_date', sa.Date(), nullable=True),
    sa.Column('actual_end_date', sa.Date(), nullable=True),
    sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('active', 'on_hold', 'completed', 'cancelled', 'archived')", name='ck_research_projects_status'),
    sa.CheckConstraint('actual_end_date IS NULL OR actual_end_date >= start_date', name='ck_research_projects_actual_end'),
    sa.CheckConstraint('expected_end_date IS NULL OR expected_end_date >= start_date', name='ck_research_projects_dates'),
    sa.ForeignKeyConstraint(['created_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_research_projects_created_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['department_id', 'university_id'], ['departments.id', 'departments.university_id'], name='fk_research_projects_department_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['proposal_id', 'university_id'], ['research_proposals.id', 'research_proposals.university_id'], name='fk_research_projects_proposal_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'university_id', name='uq_research_projects_id_university'),
    sa.UniqueConstraint('proposal_id')
    )

    op.create_table('approval_actions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('instance_id', sa.Uuid(), nullable=False),
    sa.Column('step_id', sa.Uuid(), nullable=False),
    sa.Column('workflow_version_id', sa.Uuid(), nullable=False),
    sa.Column('workflow_id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('acting_user_id', sa.Integer(), nullable=False),
    sa.Column('decision', sa.String(length=32), nullable=False),
    sa.Column('comments', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['acting_user_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_approval_actions_actor_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['acting_user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['instance_id', 'workflow_version_id', 'workflow_id', 'university_id'], ['approval_instances.id', 'approval_instances.workflow_version_id', 'approval_instances.workflow_id', 'approval_instances.university_id'], name='fk_approval_actions_instance_version_workflow_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['step_id', 'workflow_version_id', 'workflow_id', 'university_id'], ['approval_workflow_steps.id', 'approval_workflow_steps.workflow_version_id', 'approval_workflow_steps.workflow_id', 'approval_workflow_steps.university_id'], name='fk_approval_actions_step_version_workflow_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('grant_applications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('opportunity_id', sa.Uuid(), nullable=False),
    sa.Column('applicant_id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=True),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('proposal', sa.Text(), nullable=False),
    sa.Column('requested_amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'submitted', 'under_review', 'approved', 'rejected', 'withdrawn')", name='ck_grant_applications_status'),
    sa.CheckConstraint('requested_amount >= 0', name='ck_grant_applications_amount'),
    sa.ForeignKeyConstraint(['applicant_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_grant_applications_applicant_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['applicant_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['opportunity_id', 'university_id'], ['grant_opportunities.id', 'grant_opportunities.university_id'], name='fk_grant_applications_opportunity_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id', 'university_id'], ['research_projects.id', 'research_projects.university_id'], name='fk_grant_applications_project_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'university_id', name='uq_grant_applications_id_university')
    )

    op.create_table('project_milestones',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('template_id', sa.Uuid(), nullable=True),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('sequence_number', sa.Integer(), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("completed_at IS NULL OR status = 'completed'", name='ck_project_milestones_completed'),
    sa.CheckConstraint("status IN ('pending', 'in_progress', 'submitted', 'approved', 'revision_requested', 'overdue', 'completed', 'cancelled')", name='ck_project_milestones_status'),
    sa.CheckConstraint('sequence_number > 0', name='ck_project_milestones_sequence'),
    sa.ForeignKeyConstraint(['created_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_project_milestones_created_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id', 'university_id'], ['research_projects.id', 'research_projects.university_id'], name='fk_project_milestones_project_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['template_id', 'university_id'], ['milestone_templates.id', 'milestone_templates.university_id'], name='fk_project_milestones_template_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'project_id', 'university_id', name='uq_project_milestones_id_project_university'),
    sa.UniqueConstraint('id', 'university_id', name='uq_project_milestones_id_university'),
    sa.UniqueConstraint('project_id', 'sequence_number', name='uq_project_milestones_sequence')
    )

    op.create_table('project_participants',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('participation_role', sa.String(length=64), nullable=False),
    sa.Column('is_lead', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('ended_at IS NULL OR ended_at >= started_at', name='ck_project_participants_dates'),
    sa.ForeignKeyConstraint(['project_id', 'university_id'], ['research_projects.id', 'research_projects.university_id'], name='fk_project_participants_project_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['student_id', 'university_id'], ['student_profiles.id', 'student_profiles.university_id'], name='fk_project_participants_student_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('project_status_history',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('previous_status', sa.String(length=32), nullable=True),
    sa.Column('new_status', sa.String(length=32), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_project_history_actor_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id', 'university_id'], ['research_projects.id', 'research_projects.university_id'], name='fk_project_history_project_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('project_supervisors',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('staff_id', sa.Integer(), nullable=False),
    sa.Column('assigned_by_id', sa.Integer(), nullable=False),
    sa.Column('assignment_role', sa.String(length=32), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("assignment_role IN ('primary', 'co_supervisor')", name='ck_project_supervisors_role'),
    sa.CheckConstraint('ended_at IS NULL OR ended_at >= started_at', name='ck_project_supervisors_dates'),
    sa.ForeignKeyConstraint(['assigned_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_project_supervisors_assigned_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id', 'university_id'], ['research_projects.id', 'research_projects.university_id'], name='fk_project_supervisors_project_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['staff_id', 'university_id'], ['staff_profiles.id', 'staff_profiles.university_id'], name='fk_project_supervisors_staff_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('publication_projects',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('publication_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id', 'university_id'], ['research_projects.id', 'research_projects.university_id'], name='fk_publication_projects_project_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['publication_id', 'university_id'], ['publications.id', 'publications.university_id'], name='fk_publication_projects_publication_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('publication_id', 'project_id', name='uq_publication_projects_publication_project')
    )

    op.create_table('student_activity',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=True),
    sa.Column('activity_type', sa.String(length=64), nullable=False),
    sa.Column('activity_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id', 'university_id'], ['research_projects.id', 'research_projects.university_id'], name='fk_student_activity_project_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['student_id', 'university_id'], ['student_profiles.id', 'student_profiles.university_id'], name='fk_student_activity_student_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('grant_application_participants',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('participation_role', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['application_id', 'university_id'], ['grant_applications.id', 'grant_applications.university_id'], name='fk_grant_application_participants_application_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_grant_application_participants_user_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('application_id', 'user_id', name='uq_grant_application_participants_application_user')
    )

    op.create_table('grant_application_reviews',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('reviewer_id', sa.Integer(), nullable=False),
    sa.Column('decision', sa.String(length=32), nullable=False),
    sa.Column('recommended_amount', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('comments', sa.Text(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("decision IN ('approved', 'rejected', 'revision_requested', 'commented')", name='ck_grant_application_reviews_decision'),
    sa.CheckConstraint('recommended_amount IS NULL OR recommended_amount >= 0', name='ck_grant_application_reviews_amount'),
    sa.ForeignKeyConstraint(['application_id', 'university_id'], ['grant_applications.id', 'grant_applications.university_id'], name='fk_grant_application_reviews_application_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reviewer_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_grant_application_reviews_reviewer_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('grant_application_status_history',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('previous_status', sa.String(length=32), nullable=True),
    sa.Column('new_status', sa.String(length=32), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_grant_application_history_actor_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['application_id', 'university_id'], ['grant_applications.id', 'grant_applications.university_id'], name='fk_grant_application_history_application_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('grant_awards',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('award_reference', sa.String(length=128), nullable=False),
    sa.Column('awarded_amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('award_start_date', sa.Date(), nullable=False),
    sa.Column('award_end_date', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
    sa.Column('approved_by_id', sa.Integer(), nullable=False),
    sa.Column('approved_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('active', 'closed', 'cancelled')", name='ck_grant_awards_status'),
    sa.CheckConstraint('award_end_date >= award_start_date', name='ck_grant_awards_dates'),
    sa.CheckConstraint('awarded_amount >= 0', name='ck_grant_awards_amount'),
    sa.ForeignKeyConstraint(['application_id', 'university_id'], ['grant_applications.id', 'grant_applications.university_id'], name='fk_grant_awards_application_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['approved_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_grant_awards_approved_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('application_id'),
    sa.UniqueConstraint('application_id', name='uq_grant_awards_application'),
    sa.UniqueConstraint('award_reference'),
    sa.UniqueConstraint('award_reference', name='uq_grant_awards_reference'),
    sa.UniqueConstraint('id', 'university_id', name='uq_grant_awards_id_university')
    )

    op.create_table('progress_reports',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('milestone_id', sa.Uuid(), nullable=True),
    sa.Column('submitter_id', sa.Integer(), nullable=False),
    sa.Column('period_start', sa.Date(), nullable=False),
    sa.Column('period_end', sa.Date(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('challenges', sa.Text(), nullable=True),
    sa.Column('next_steps', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'submitted', 'under_review', 'revision_requested', 'approved', 'rejected')", name='ck_progress_reports_status'),
    sa.CheckConstraint('period_end >= period_start', name='ck_progress_reports_period'),
    sa.ForeignKeyConstraint(['milestone_id', 'project_id', 'university_id'], ['project_milestones.id', 'project_milestones.project_id', 'project_milestones.university_id'], name='fk_progress_reports_milestone_project_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id', 'university_id'], ['research_projects.id', 'research_projects.university_id'], name='fk_progress_reports_project_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['submitter_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_progress_reports_submitter_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['submitter_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'university_id', name='uq_progress_reports_id_university')
    )

    op.create_table('document_attachments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('stored_file_id', sa.Uuid(), nullable=False),
    sa.Column('proposal_id', sa.Uuid(), nullable=True),
    sa.Column('project_id', sa.Uuid(), nullable=True),
    sa.Column('progress_report_id', sa.Uuid(), nullable=True),
    sa.Column('grant_application_id', sa.Uuid(), nullable=True),
    sa.Column('document_type', sa.String(length=64), nullable=False),
    sa.Column('uploader_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('num_nonnulls(proposal_id, project_id, progress_report_id, grant_application_id) = 1', name='ck_document_attachments_one_target'),
    sa.ForeignKeyConstraint(['grant_application_id', 'university_id'], ['grant_applications.id', 'grant_applications.university_id'], name='fk_document_attachments_application_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['progress_report_id', 'university_id'], ['progress_reports.id', 'progress_reports.university_id'], name='fk_document_attachments_report_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id', 'university_id'], ['research_projects.id', 'research_projects.university_id'], name='fk_document_attachments_project_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['proposal_id', 'university_id'], ['research_proposals.id', 'research_proposals.university_id'], name='fk_document_attachments_proposal_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['stored_file_id', 'university_id'], ['stored_files.id', 'stored_files.university_id'], name='fk_document_attachments_file_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['uploader_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_document_attachments_uploader_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['uploader_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('grant_expenditures',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('award_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=True),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('expenditure_date', sa.Date(), nullable=False),
    sa.Column('reference_number', sa.String(length=128), nullable=True),
    sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
    sa.Column('recorded_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'submitted', 'approved', 'rejected', 'paid', 'voided')", name='ck_grant_expenditures_status'),
    sa.CheckConstraint('amount >= 0', name='ck_grant_expenditures_amount'),
    sa.ForeignKeyConstraint(['award_id', 'university_id'], ['grant_awards.id', 'grant_awards.university_id'], name='fk_grant_expenditures_award_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id', 'university_id'], ['research_projects.id', 'research_projects.university_id'], name='fk_grant_expenditures_project_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['recorded_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_grant_expenditures_recorded_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['recorded_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('grant_progress_reports',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('award_id', sa.Uuid(), nullable=False),
    sa.Column('period_start', sa.Date(), nullable=False),
    sa.Column('period_end', sa.Date(), nullable=False),
    sa.Column('narrative', sa.Text(), nullable=False),
    sa.Column('financial_summary', sa.Text(), nullable=True),
    sa.Column('submitter_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'submitted', 'under_review', 'revision_requested', 'approved', 'rejected')", name='ck_grant_progress_reports_status'),
    sa.CheckConstraint('period_end >= period_start', name='ck_grant_progress_reports_period'),
    sa.ForeignKeyConstraint(['award_id', 'university_id'], ['grant_awards.id', 'grant_awards.university_id'], name='fk_grant_reports_award_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['submitter_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_grant_reports_submitter_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['submitter_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('grant_project_allocations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('award_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('allocated_amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('allocated_amount >= 0', name='ck_grant_project_allocations_amount'),
    sa.ForeignKeyConstraint(['award_id', 'university_id'], ['grant_awards.id', 'grant_awards.university_id'], name='fk_grant_allocations_award_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_grant_allocations_created_by_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id', 'university_id'], ['research_projects.id', 'research_projects.university_id'], name='fk_grant_allocations_project_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('award_id', 'project_id', name='uq_grant_project_allocations_award_project')
    )

    op.create_table('progress_report_reviews',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('report_id', sa.Uuid(), nullable=False),
    sa.Column('reviewer_id', sa.Integer(), nullable=False),
    sa.Column('decision', sa.String(length=32), nullable=False),
    sa.Column('feedback', sa.Text(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("decision IN ('approved', 'rejected', 'revision_requested', 'commented')", name='ck_progress_report_reviews_decision'),
    sa.ForeignKeyConstraint(['report_id', 'university_id'], ['progress_reports.id', 'progress_reports.university_id'], name='fk_progress_report_reviews_report_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reviewer_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_progress_report_reviews_reviewer_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('project_comments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('university_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=True),
    sa.Column('milestone_id', sa.Uuid(), nullable=True),
    sa.Column('progress_report_id', sa.Uuid(), nullable=True),
    sa.Column('author_id', sa.Integer(), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('num_nonnulls(project_id, milestone_id, progress_report_id) = 1', name='ck_project_comments_one_target'),
    sa.ForeignKeyConstraint(['author_id', 'university_id'], ['university_memberships.user_id', 'university_memberships.university_id'], name='fk_project_comments_author_membership', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['milestone_id', 'university_id'], ['project_milestones.id', 'project_milestones.university_id'], name='fk_project_comments_milestone_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['progress_report_id', 'university_id'], ['progress_reports.id', 'progress_reports.university_id'], name='fk_project_comments_report_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id', 'university_id'], ['research_projects.id', 'research_projects.university_id'], name='fk_project_comments_project_university', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )

    # The workflow active-version FK is the only circular edge. Create it
    # after both workflow tables exist; the model uses use_alter for this edge.
    op.create_foreign_key('fk_approval_workflows_active_version', 'approval_workflows', 'approval_workflow_versions', ['active_version_id', 'id', 'university_id'], ['id', 'workflow_id', 'university_id'], ondelete='RESTRICT')

    op.create_index('ix_account_verifications_user_expires', 'account_verifications', ['user_id', 'expires_at'], unique=False)
    op.create_index('ix_audit_logs_entity_event', 'audit_logs', ['entity_type', 'entity_id', 'event_at'], unique=False)
    op.create_index('ix_audit_logs_request_id', 'audit_logs', ['request_id'], unique=False)
    op.create_index('ix_notifications_recipient_created', 'notifications', ['recipient_id', 'created_at'], unique=False)
    op.create_index('ix_notifications_recipient_unread_created', 'notifications', ['recipient_id', 'read_at', 'created_at'], unique=False)
    op.create_index('ix_publications_status_date', 'publications', ['verification_status', 'publication_date'], unique=False)
    op.create_index('uq_publications_normalized_doi', 'publications', ['normalized_doi'], unique=True, postgresql_where=sa.text('normalized_doi IS NOT NULL'))
    op.create_index('ix_stored_files_uploader_created', 'stored_files', ['uploader_id', 'created_at'], unique=False)
    op.create_index('uq_approval_workflows_department_scope', 'approval_workflows', ['workflow_type', 'university_id', 'department_id'], unique=True, postgresql_where=sa.text('department_id IS NOT NULL'))
    op.create_index('uq_approval_workflows_university_scope', 'approval_workflows', ['workflow_type', 'university_id'], unique=True, postgresql_where=sa.text('department_id IS NULL'))
    op.create_index('uq_publication_authors_corresponding', 'publication_authors', ['publication_id'], unique=True, postgresql_where=sa.text('is_corresponding = true'))
    op.create_index('ix_research_topics_department_status', 'research_topics', ['department_id', 'is_active'], unique=False)
    op.create_index('ix_research_topics_normalized_title', 'research_topics', ['normalized_title'], unique=False)
    op.create_index('uq_retention_policies_university_category_department', 'retention_policies', ['university_id', 'record_category', 'department_id'], unique=True, postgresql_where=sa.text('department_id IS NOT NULL'))
    op.create_index('uq_retention_policies_university_category_global', 'retention_policies', ['university_id', 'record_category'], unique=True, postgresql_where=sa.text('department_id IS NULL'))
    op.create_index('ix_alert_events_status_detected', 'alert_events', ['status', 'detected_at'], unique=False)
    op.create_index('uq_department_leadership_active', 'department_leadership', ['department_id'], unique=True, postgresql_where=sa.text('ended_at IS NULL'))
    op.create_index('ix_research_proposals_department_status', 'research_proposals', ['department_id', 'status'], unique=False)
    op.create_index('ix_approval_instances_target', 'approval_instances', ['target_entity_type', 'target_entity_id'], unique=False)
    op.create_index('uq_proposal_participants_lead', 'proposal_participants', ['proposal_id'], unique=True, postgresql_where=sa.text('is_lead = true'))
    op.create_index('ix_proposal_reviews_proposal_reviewed_at', 'proposal_reviews', ['proposal_id', 'reviewed_at'], unique=False)
    op.create_index('uq_proposal_supervisors_active', 'proposal_supervisors', ['proposal_id', 'staff_id'], unique=True, postgresql_where=sa.text('ended_at IS NULL'))
    op.create_index('uq_proposal_supervisors_primary_active', 'proposal_supervisors', ['proposal_id'], unique=True, postgresql_where=sa.text("assignment_role = 'primary' AND ended_at IS NULL"))
    op.create_index('ix_research_projects_department_status', 'research_projects', ['department_id', 'status'], unique=False)
    op.create_index('ix_grant_applications_opportunity_status', 'grant_applications', ['opportunity_id', 'status'], unique=False)
    op.create_index('uq_project_participants_active_lead', 'project_participants', ['project_id'], unique=True, postgresql_where=sa.text('is_lead = true AND ended_at IS NULL'))
    op.create_index('uq_project_participants_active_student', 'project_participants', ['project_id', 'student_id'], unique=True, postgresql_where=sa.text('ended_at IS NULL'))
    op.create_index('uq_project_supervisors_active_staff', 'project_supervisors', ['project_id', 'staff_id'], unique=True, postgresql_where=sa.text('ended_at IS NULL'))
    op.create_index('uq_project_supervisors_primary_active', 'project_supervisors', ['project_id'], unique=True, postgresql_where=sa.text("assignment_role = 'primary' AND ended_at IS NULL"))
    op.create_index('ix_student_activity_student_recorded', 'student_activity', ['student_id', 'recorded_at'], unique=False)
    op.create_index('ix_progress_reports_project_period', 'progress_reports', ['project_id', 'period_start', 'period_end'], unique=False)
    op.create_index('ix_document_attachments_target_project', 'document_attachments', ['project_id'], unique=False)
    op.create_index('ix_document_attachments_target_proposal', 'document_attachments', ['proposal_id'], unique=False)
    op.create_index('ix_grant_expenditures_award_date', 'grant_expenditures', ['award_id', 'expenditure_date'], unique=False)
    op.create_index('ix_project_comments_project_created', 'project_comments', ['project_id', 'created_at'], unique=False)

    op.execute("\n    CREATE OR REPLACE FUNCTION pms_guard_approval_workflow_version()\n    RETURNS trigger\n    LANGUAGE plpgsql\n    AS $function$\n    BEGIN\n        IF TG_OP = 'INSERT' THEN\n            IF NEW.publication_state IS DISTINCT FROM 'draft' THEN\n                RAISE EXCEPTION 'Approval workflow versions must be created as drafts'\n                    USING ERRCODE = 'check_violation';\n            END IF;\n            RETURN NEW;\n        END IF;\n\n        IF TG_OP = 'DELETE' THEN\n            IF OLD.publication_state = 'published' THEN\n                RAISE EXCEPTION 'Published approval workflow versions cannot be deleted'\n                    USING ERRCODE = 'restrict_violation';\n            END IF;\n            RETURN OLD;\n        END IF;\n\n        IF OLD.publication_state = 'published' THEN\n            RAISE EXCEPTION 'Published approval workflow versions are immutable'\n                USING ERRCODE = 'restrict_violation';\n        END IF;\n        RETURN NEW;\n    END;\n    $function$;\n    ")
    op.execute("\n    CREATE OR REPLACE FUNCTION pms_guard_approval_workflow_step()\n    RETURNS trigger\n    LANGUAGE plpgsql\n    AS $function$\n    DECLARE\n        old_workflow_id uuid;\n        old_university_id uuid;\n        old_state text;\n        new_workflow_id uuid;\n        new_university_id uuid;\n        new_state text;\n    BEGIN\n        IF TG_OP = 'DELETE' THEN\n            SELECT workflow_id, university_id, publication_state\n              INTO old_workflow_id, old_university_id, old_state\n              FROM approval_workflow_versions\n             WHERE id = OLD.workflow_version_id;\n            IF old_state = 'published' THEN\n                RAISE EXCEPTION 'Steps belonging to published approval workflow versions cannot be deleted'\n                    USING ERRCODE = 'restrict_violation';\n            END IF;\n            IF old_workflow_id IS DISTINCT FROM OLD.workflow_id\n               OR old_university_id IS DISTINCT FROM OLD.university_id THEN\n                RAISE EXCEPTION 'Approval workflow step identity is inconsistent'\n                    USING ERRCODE = 'foreign_key_violation';\n            END IF;\n            RETURN OLD;\n        END IF;\n\n        SELECT workflow_id, university_id, publication_state\n          INTO new_workflow_id, new_university_id, new_state\n          FROM approval_workflow_versions\n         WHERE id = NEW.workflow_version_id;\n        IF new_state = 'published' THEN\n            RAISE EXCEPTION 'Steps belonging to published approval workflow versions are immutable'\n                USING ERRCODE = 'restrict_violation';\n        END IF;\n        IF new_workflow_id IS DISTINCT FROM NEW.workflow_id\n           OR new_university_id IS DISTINCT FROM NEW.university_id THEN\n            RAISE EXCEPTION 'Approval workflow step identity is inconsistent'\n                USING ERRCODE = 'foreign_key_violation';\n        END IF;\n\n        IF TG_OP = 'UPDATE' THEN\n            SELECT workflow_id, university_id, publication_state\n              INTO old_workflow_id, old_university_id, old_state\n              FROM approval_workflow_versions\n             WHERE id = OLD.workflow_version_id;\n            IF old_state = 'published' THEN\n                RAISE EXCEPTION 'Steps belonging to published approval workflow versions are immutable'\n                    USING ERRCODE = 'restrict_violation';\n            END IF;\n            IF old_workflow_id IS DISTINCT FROM OLD.workflow_id\n               OR old_university_id IS DISTINCT FROM OLD.university_id THEN\n                RAISE EXCEPTION 'Approval workflow step identity is inconsistent'\n                    USING ERRCODE = 'foreign_key_violation';\n            END IF;\n        END IF;\n        RETURN NEW;\n    END;\n    $function$;\n    ")
    op.execute("\n    CREATE OR REPLACE FUNCTION pms_guard_approval_workflow_identity()\n    RETURNS trigger\n    LANGUAGE plpgsql\n    AS $function$\n    BEGIN\n        IF OLD.workflow_type IS DISTINCT FROM NEW.workflow_type\n           OR OLD.department_id IS DISTINCT FROM NEW.department_id\n           OR OLD.university_id IS DISTINCT FROM NEW.university_id\n           OR OLD.created_by_id IS DISTINCT FROM NEW.created_by_id THEN\n            IF EXISTS (\n                SELECT 1\n                  FROM approval_workflow_versions\n                 WHERE workflow_id = OLD.id\n            ) OR EXISTS (\n                SELECT 1\n                  FROM approval_instances\n                 WHERE workflow_id = OLD.id\n            ) THEN\n                RAISE EXCEPTION 'Approval workflow identity cannot change after history exists'\n                    USING ERRCODE = 'restrict_violation';\n            END IF;\n        END IF;\n        RETURN NEW;\n    END;\n    $function$;\n    ")
    op.execute("\n    CREATE OR REPLACE FUNCTION pms_guard_approval_active_version()\n    RETURNS trigger\n    LANGUAGE plpgsql\n    AS $function$\n    DECLARE\n        selected_workflow_id uuid;\n        selected_university_id uuid;\n        selected_state text;\n    BEGIN\n        IF NEW.active_version_id IS NULL THEN\n            RETURN NEW;\n        END IF;\n\n        SELECT workflow_id, university_id, publication_state\n          INTO selected_workflow_id, selected_university_id, selected_state\n          FROM approval_workflow_versions\n         WHERE id = NEW.active_version_id;\n        IF NOT FOUND\n           OR selected_workflow_id IS DISTINCT FROM NEW.id\n           OR selected_university_id IS DISTINCT FROM NEW.university_id THEN\n            RAISE EXCEPTION 'The active approval workflow version must belong to its workflow'\n                USING ERRCODE = 'foreign_key_violation';\n        END IF;\n        IF selected_state IS DISTINCT FROM 'published' THEN\n            RAISE EXCEPTION 'The active approval workflow version must be published'\n                USING ERRCODE = 'check_violation';\n        END IF;\n        RETURN NEW;\n    END;\n    $function$;\n    ")
    op.execute('\n    CREATE TRIGGER trg_approval_workflow_versions_guard\n    BEFORE INSERT OR UPDATE OR DELETE ON approval_workflow_versions\n    FOR EACH ROW EXECUTE FUNCTION pms_guard_approval_workflow_version();\n    ')
    op.execute('\n    CREATE TRIGGER trg_approval_workflow_steps_guard\n    BEFORE INSERT OR UPDATE OR DELETE ON approval_workflow_steps\n    FOR EACH ROW EXECUTE FUNCTION pms_guard_approval_workflow_step();\n    ')
    op.execute('\n    CREATE TRIGGER trg_approval_workflows_identity_guard\n    BEFORE UPDATE ON approval_workflows\n    FOR EACH ROW EXECUTE FUNCTION pms_guard_approval_workflow_identity();\n    ')
    op.execute('\n    CREATE TRIGGER trg_approval_workflows_active_version_guard\n    BEFORE INSERT OR UPDATE OF active_version_id ON approval_workflows\n    FOR EACH ROW EXECUTE FUNCTION pms_guard_approval_active_version();\n    ')


def downgrade() -> None:
    # Remove trigger objects before their protected tables are dropped.
    op.execute('DROP TRIGGER IF EXISTS trg_approval_workflows_active_version_guard ON approval_workflows')
    op.execute('DROP TRIGGER IF EXISTS trg_approval_workflows_identity_guard ON approval_workflows')
    op.execute('DROP TRIGGER IF EXISTS trg_approval_workflow_steps_guard ON approval_workflow_steps')
    op.execute('DROP TRIGGER IF EXISTS trg_approval_workflow_versions_guard ON approval_workflow_versions')
    op.execute('DROP FUNCTION IF EXISTS pms_guard_approval_active_version()')
    op.execute('DROP FUNCTION IF EXISTS pms_guard_approval_workflow_identity()')
    op.execute('DROP FUNCTION IF EXISTS pms_guard_approval_workflow_step()')
    op.execute('DROP FUNCTION IF EXISTS pms_guard_approval_workflow_version()')

    op.drop_constraint('fk_approval_workflows_active_version', 'approval_workflows', type_='foreignkey')

    op.drop_index('ix_project_comments_project_created', table_name='project_comments')
    op.drop_index('ix_grant_expenditures_award_date', table_name='grant_expenditures')
    op.drop_index('ix_document_attachments_target_proposal', table_name='document_attachments')
    op.drop_index('ix_document_attachments_target_project', table_name='document_attachments')
    op.drop_index('ix_progress_reports_project_period', table_name='progress_reports')
    op.drop_index('ix_student_activity_student_recorded', table_name='student_activity')
    op.drop_index('uq_project_supervisors_primary_active', table_name='project_supervisors')
    op.drop_index('uq_project_supervisors_active_staff', table_name='project_supervisors')
    op.drop_index('uq_project_participants_active_student', table_name='project_participants')
    op.drop_index('uq_project_participants_active_lead', table_name='project_participants')
    op.drop_index('ix_grant_applications_opportunity_status', table_name='grant_applications')
    op.drop_index('ix_research_projects_department_status', table_name='research_projects')
    op.drop_index('uq_proposal_supervisors_primary_active', table_name='proposal_supervisors')
    op.drop_index('uq_proposal_supervisors_active', table_name='proposal_supervisors')
    op.drop_index('ix_proposal_reviews_proposal_reviewed_at', table_name='proposal_reviews')
    op.drop_index('uq_proposal_participants_lead', table_name='proposal_participants')
    op.drop_index('ix_approval_instances_target', table_name='approval_instances')
    op.drop_index('ix_research_proposals_department_status', table_name='research_proposals')
    op.drop_index('uq_department_leadership_active', table_name='department_leadership')
    op.drop_index('ix_alert_events_status_detected', table_name='alert_events')
    op.drop_index('uq_retention_policies_university_category_global', table_name='retention_policies')
    op.drop_index('uq_retention_policies_university_category_department', table_name='retention_policies')
    op.drop_index('ix_research_topics_normalized_title', table_name='research_topics')
    op.drop_index('ix_research_topics_department_status', table_name='research_topics')
    op.drop_index('uq_publication_authors_corresponding', table_name='publication_authors')
    op.drop_index('uq_approval_workflows_university_scope', table_name='approval_workflows')
    op.drop_index('uq_approval_workflows_department_scope', table_name='approval_workflows')
    op.drop_index('uq_user_roles_active_assignment', table_name='user_roles')
    op.drop_index('ix_stored_files_uploader_created', table_name='stored_files')
    op.drop_index('uq_publications_normalized_doi', table_name='publications')
    op.drop_index('ix_publications_status_date', table_name='publications')
    op.drop_index('ix_notifications_recipient_unread_created', table_name='notifications')
    op.drop_index('ix_notifications_recipient_created', table_name='notifications')
    op.drop_index('ix_audit_logs_request_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_entity_event', table_name='audit_logs')
    op.drop_index('ix_account_verifications_user_expires', table_name='account_verifications')

    op.drop_table('project_comments')
    op.drop_table('progress_report_reviews')
    op.drop_table('grant_project_allocations')
    op.drop_table('grant_progress_reports')
    op.drop_table('grant_expenditures')
    op.drop_table('document_attachments')
    op.drop_table('progress_reports')
    op.drop_table('grant_awards')
    op.drop_table('grant_application_status_history')
    op.drop_table('grant_application_reviews')
    op.drop_table('grant_application_participants')
    op.drop_table('student_activity')
    op.drop_table('publication_projects')
    op.drop_table('project_supervisors')
    op.drop_table('project_status_history')
    op.drop_table('project_participants')
    op.drop_table('project_milestones')
    op.drop_table('grant_applications')
    op.drop_table('approval_actions')
    op.drop_table('research_projects')
    op.drop_table('proposal_supervisors')
    op.drop_table('proposal_status_history')
    op.drop_table('proposal_revisions')
    op.drop_table('proposal_reviews')
    op.drop_table('proposal_participants')
    op.drop_table('duplicate_topic_candidates')
    op.drop_table('approval_workflow_steps')
    op.drop_table('approval_instances')
    op.drop_table('research_proposals')
    op.drop_table('department_leadership')
    op.drop_table('approval_workflow_versions')
    op.drop_table('alert_events')
    op.drop_table('retention_policies')
    op.drop_table('research_topics')
    op.drop_table('publication_reviews')
    op.drop_table('publication_authors')
    op.drop_table('milestone_templates')
    op.drop_table('department_settings')
    op.drop_table('approval_workflows')
    op.drop_table('alert_rules')
    op.drop_table('university_settings')
    op.drop_table('system_settings')
    op.drop_table('stored_files')
    op.drop_table('publications')
    op.drop_table('notifications')
    op.drop_table('grant_opportunities')
    op.drop_table('audit_logs')
    op.drop_table('university_memberships')
    op.drop_table('role_permissions')
    op.drop_table('account_verifications')
    op.drop_table('universities')
    op.drop_table('permissions')

    # Restore the original seven-table baseline definitions.
    op.drop_constraint('fk_student_profiles_department_university', 'student_profiles', type_='foreignkey')
    op.drop_constraint('fk_student_profiles_membership', 'student_profiles', type_='foreignkey')
    op.drop_constraint('fk_student_profiles_university', 'student_profiles', type_='foreignkey')
    op.drop_constraint('fk_staff_profiles_department_university', 'staff_profiles', type_='foreignkey')
    op.drop_constraint('fk_staff_profiles_membership', 'staff_profiles', type_='foreignkey')
    op.drop_constraint('fk_staff_profiles_university', 'staff_profiles', type_='foreignkey')
    op.drop_constraint('fk_user_roles_assigned_by_membership', 'user_roles', type_='foreignkey')
    op.drop_constraint('fk_user_roles_membership', 'user_roles', type_='foreignkey')
    op.drop_constraint('fk_user_roles_assigned_by_user', 'user_roles', type_='foreignkey')
    op.drop_constraint('fk_user_roles_university', 'user_roles', type_='foreignkey')
    op.drop_constraint('fk_departments_faculty_university', 'departments', type_='foreignkey')
    op.drop_constraint('fk_departments_university', 'departments', type_='foreignkey')
    op.drop_constraint('fk_faculties_university', 'faculties', type_='foreignkey')

    op.create_foreign_key('departments_faculty_id_fkey', 'departments', 'faculties', ['faculty_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key('staff_profiles_department_id_fkey', 'staff_profiles', 'departments', ['department_id'], ['id'], ondelete='RESTRICT')
    op.create_foreign_key('student_profiles_department_id_fkey', 'student_profiles', 'departments', ['department_id'], ['id'], ondelete='RESTRICT')

    op.drop_constraint('uq_student_profiles_university_student_id', 'student_profiles', type_='unique')
    op.drop_constraint('uq_student_profiles_id_university', 'student_profiles', type_='unique')
    op.drop_constraint('uq_student_profiles_user_university', 'student_profiles', type_='unique')
    op.drop_constraint('ck_student_profiles_account_status', 'student_profiles', type_='check')
    op.drop_constraint('ck_student_profiles_gender', 'student_profiles', type_='check')
    op.drop_constraint('uq_staff_profiles_university_staff_id', 'staff_profiles', type_='unique')
    op.drop_constraint('uq_staff_profiles_id_department_university', 'staff_profiles', type_='unique')
    op.drop_constraint('uq_staff_profiles_id_university', 'staff_profiles', type_='unique')
    op.drop_constraint('uq_staff_profiles_user_university', 'staff_profiles', type_='unique')
    op.drop_constraint('ck_staff_profiles_gender', 'staff_profiles', type_='check')
    op.drop_constraint('ck_user_roles_revoked_at', 'user_roles', type_='check')
    op.drop_index('uq_user_roles_active_assignment', table_name='user_roles')
    op.drop_constraint('uq_departments_faculty_code', 'departments', type_='unique')
    op.drop_constraint('uq_departments_faculty_name', 'departments', type_='unique')
    op.drop_constraint('uq_departments_id_university', 'departments', type_='unique')
    op.drop_constraint('uq_faculties_university_code', 'faculties', type_='unique')
    op.drop_constraint('uq_faculties_id_university', 'faculties', type_='unique')

    op.drop_column('student_profiles', 'academic_account_status')
    op.drop_column('student_profiles', 'enrollment_date')
    op.drop_column('student_profiles', 'gender')
    op.drop_column('student_profiles', 'university_id')
    op.drop_column('staff_profiles', 'gender')
    op.drop_column('staff_profiles', 'academic_designation')
    op.drop_column('staff_profiles', 'university_id')
    op.drop_column('user_roles', 'revoked_at')
    op.drop_column('user_roles', 'assigned_by_id')
    op.drop_column('user_roles', 'university_id')
    op.drop_column('departments', 'university_id')
    op.drop_column('users', 'email_verified_at')
    op.drop_column('faculties', 'university_id')

    op.create_unique_constraint('faculties_code_key', 'faculties', ['code'])
    op.create_unique_constraint('uq_departments_faculty_name', 'departments', ['faculty_id', 'name'])
    op.create_unique_constraint('departments_code_key', 'departments', ['code'])
    op.create_unique_constraint('uq_user_roles_user_role', 'user_roles', ['user_id', 'role_id'])
    op.create_unique_constraint('staff_profiles_staff_id_key', 'staff_profiles', ['staff_id'])
    op.create_unique_constraint('staff_profiles_user_id_key', 'staff_profiles', ['user_id'])
    op.create_unique_constraint('student_profiles_student_id_key', 'student_profiles', ['student_id'])
    op.create_unique_constraint('student_profiles_user_id_key', 'student_profiles', ['user_id'])
