import uuid
import warnings
from types import SimpleNamespace

from sqlalchemy import Integer, Uuid
from sqlalchemy.exc import SAWarning
from sqlalchemy.orm import configure_mappers

from backend.app.models import (
    ApprovalInstance,
    ApprovalWorkflow,
    ApprovalWorkflowVersion,
    ApprovalWorkflowStep,
    Base,
    StaffProfile,
    StudentProfile,
    User,
)
from backend.app.models.approval import (
    APPROVAL_TRIGGER_SQL,
    _ensure_workflow_identity_mutable,
    _reject_published_version_update,
    _validate_step_version_transition,
)


class _Result:
    def __init__(self, value):
        self.value = value

    def one_or_none(self):
        return self.value

    def first(self):
        return self.value


class _SequentialConnection:
    def __init__(self, *results):
        self.results = list(results)

    def execute(self, _statement):
        return _Result(self.results.pop(0))


def _unique(table_name: str, columns: tuple[str, ...]):
    table = Base.metadata.tables[table_name]
    return next(
        constraint
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
        and tuple(column.name for column in constraint.columns) == columns
    )


def _foreign_key(table_name: str, name: str):
    table = Base.metadata.tables[table_name]
    return next(constraint for constraint in table.foreign_key_constraints if constraint.name == name)


def test_registry_and_mapper_configuration_without_warnings() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", SAWarning)
        configure_mappers()
    assert len(Base.metadata.tables) == 60
    assert len(list(Base.registry.mappers)) == 60


def test_profiles_are_university_scoped_collections() -> None:
    user = next(mapper for mapper in Base.registry.mappers if mapper.local_table.name == "users")
    assert user.relationships["student_profiles"].uselist is True
    assert user.relationships["staff_profiles"].uselist is True
    assert tuple(_unique("student_profiles", ("user_id", "university_id")).columns.keys()) == (
        "user_id",
        "university_id",
    )
    assert tuple(_unique("staff_profiles", ("user_id", "university_id")).columns.keys()) == (
        "user_id",
        "university_id",
    )
    assert Base.metadata.tables["student_profiles"].c.user_id.unique is not True
    assert Base.metadata.tables["staff_profiles"].c.user_id.unique is not True


def test_one_user_can_hold_student_and_staff_profiles_at_two_universities() -> None:
    user = User(full_name="Global User", email="global@example.test", password_hash="hash")
    university_a = uuid.uuid4()
    university_b = uuid.uuid4()
    user.student_profiles = [
        StudentProfile(user_id=1, university_id=university_a, student_id="A-1", department_id=1, academic_level="1"),
        StudentProfile(user_id=1, university_id=university_b, student_id="B-1", department_id=1, academic_level="1"),
    ]
    user.staff_profiles = [
        StaffProfile(user_id=1, university_id=university_a, staff_id="A-S1", department_id=1, job_title="Supervisor"),
        StaffProfile(user_id=1, university_id=university_b, staff_id="B-S1", department_id=1, job_title="Supervisor"),
    ]
    assert {profile.university_id for profile in user.student_profiles} == {university_a, university_b}
    assert {profile.university_id for profile in user.staff_profiles} == {university_a, university_b}


def test_department_leadership_requires_exact_staff_department() -> None:
    constraint = _foreign_key(
        "department_leadership", "fk_department_leadership_staff_department_university"
    )
    assert tuple(constraint.columns.keys()) == ("staff_id", "department_id", "university_id")
    assert tuple(element.target_fullname for element in constraint.elements) == (
        "staff_profiles.id",
        "staff_profiles.department_id",
        "staff_profiles.university_id",
    )
    assert tuple(_unique("staff_profiles", ("id", "department_id", "university_id")).columns.keys()) == (
        "id",
        "department_id",
        "university_id",
    )


def test_progress_report_milestone_is_project_and_university_scoped() -> None:
    constraint = _foreign_key(
        "progress_reports", "fk_progress_reports_milestone_project_university"
    )
    assert tuple(constraint.columns.keys()) == ("milestone_id", "project_id", "university_id")
    assert tuple(element.target_fullname for element in constraint.elements) == (
        "project_milestones.id",
        "project_milestones.project_id",
        "project_milestones.university_id",
    )
    assert Base.metadata.tables["progress_reports"].c.milestone_id.nullable is True
    assert tuple(_unique("project_milestones", ("id", "project_id", "university_id")).columns.keys()) == (
        "id",
        "project_id",
        "university_id",
    )


def test_two_versions_can_coexist_under_one_stable_workflow() -> None:
    workflow_id = uuid.uuid4()
    university_id = uuid.uuid4()
    version_one = ApprovalWorkflowVersion(
        id=uuid.uuid4(),
        workflow_id=workflow_id,
        university_id=university_id,
        version_number=1,
        publication_state="draft",
    )
    version_two = ApprovalWorkflowVersion(
        id=uuid.uuid4(),
        workflow_id=workflow_id,
        university_id=university_id,
        version_number=2,
        publication_state="draft",
    )
    assert version_one.workflow_id == version_two.workflow_id
    assert version_one.id != version_two.id
    assert version_one.version_number != version_two.version_number


def test_published_version_update_is_rejected_by_model_guard() -> None:
    try:
        _reject_published_version_update("published")
    except ValueError as error:
        assert "immutable" in str(error)
    else:
        raise AssertionError("published workflow version update was not rejected")


def test_step_cannot_move_from_published_version_to_draft_version() -> None:
    workflow_id = uuid.uuid4()
    university_id = uuid.uuid4()
    published_version_id = uuid.uuid4()
    draft_version_id = uuid.uuid4()
    step = ApprovalWorkflowStep(
        workflow_version_id=draft_version_id,
        workflow_id=workflow_id,
        university_id=university_id,
        step_number=1,
        name="Draft step",
    )
    details_published = SimpleNamespace(
        workflow_id=workflow_id,
        university_id=university_id,
        publication_state="published",
    )
    details_draft = SimpleNamespace(
        workflow_id=workflow_id,
        university_id=university_id,
        publication_state="draft",
    )
    try:
        _validate_step_version_transition(
            _SequentialConnection(details_published, details_draft, details_draft),
            step,
            published_version_id,
        )
    except ValueError as error:
        assert "published" in str(error)
    else:
        raise AssertionError("published step reassignment was not rejected")


def test_draft_step_edit_remains_allowed_when_both_versions_are_draft() -> None:
    workflow_id = uuid.uuid4()
    university_id = uuid.uuid4()
    version_id = uuid.uuid4()
    step = ApprovalWorkflowStep(
        workflow_version_id=version_id,
        workflow_id=workflow_id,
        university_id=university_id,
        step_number=1,
        name="Draft step",
    )
    details = SimpleNamespace(
        workflow_id=workflow_id,
        university_id=university_id,
        publication_state="draft",
    )
    _validate_step_version_transition(_SequentialConnection(details, details, details), step, version_id)


def test_workflow_identity_change_is_rejected_after_history_exists() -> None:
    workflow_id = uuid.uuid4()
    try:
        _ensure_workflow_identity_mutable(
            _SequentialConnection(SimpleNamespace(id=uuid.uuid4())),
            workflow_id,
        )
    except ValueError as error:
        assert "identity" in str(error)
    else:
        raise AssertionError("workflow identity change was not rejected")


def test_trigger_sql_covers_version_step_identity_and_active_pointer_guards() -> None:
    trigger_sql = "\n".join(APPROVAL_TRIGGER_SQL)
    for function_name in (
        "pms_guard_approval_workflow_version",
        "pms_guard_approval_workflow_step",
        "pms_guard_approval_workflow_identity",
        "pms_guard_approval_active_version",
    ):
        assert function_name in trigger_sql
    assert "OLD.publication_state = 'published'" in trigger_sql
    assert "NEW.publication_state" in trigger_sql
    assert "OLD.workflow_version_id" in trigger_sql
    assert "NEW.workflow_version_id" in trigger_sql
    assert "NEW.active_version_id" in trigger_sql
    assert "selected_state IS DISTINCT FROM 'published'" in trigger_sql


def test_approval_instance_references_exact_version() -> None:
    university_id = uuid.uuid4()
    workflow_id = uuid.uuid4()
    version_one_id = uuid.uuid4()
    version_two_id = uuid.uuid4()
    instance = ApprovalInstance(
        workflow_version_id=version_one_id,
        workflow_id=workflow_id,
        university_id=university_id,
        target_entity_type="research_proposal",
        target_entity_id=uuid.uuid4(),
        initiated_by_id=1,
    )
    assert instance.workflow_version_id == version_one_id
    assert instance.workflow_version_id != version_two_id
    constraint = _foreign_key(
        "approval_instances", "fk_approval_instances_version_workflow_university"
    )
    assert tuple(constraint.columns.keys()) == (
        "workflow_version_id",
        "workflow_id",
        "university_id",
    )
    assert tuple(element.target_fullname for element in constraint.elements) == (
        "approval_workflow_versions.id",
        "approval_workflow_versions.workflow_id",
        "approval_workflow_versions.university_id",
    )


def test_active_version_pointer_is_tenant_safe_and_single_valued() -> None:
    constraint = _foreign_key("approval_workflows", "fk_approval_workflows_active_version")
    assert tuple(constraint.columns.keys()) == ("active_version_id", "id", "university_id")
    assert tuple(element.target_fullname for element in constraint.elements) == (
        "approval_workflow_versions.id",
        "approval_workflow_versions.workflow_id",
        "approval_workflow_versions.university_id",
    )
    workflow = next(
        mapper for mapper in Base.registry.mappers if mapper.local_table.name == "approval_workflows"
    )
    assert workflow.relationships["active_version"].uselist is False
    assert any(index.name == "uq_approval_workflows_department_scope" for index in Base.metadata.tables["approval_workflows"].indexes)
    assert any(index.name == "uq_approval_workflows_university_scope" for index in Base.metadata.tables["approval_workflows"].indexes)


def test_steps_and_actions_are_version_scoped() -> None:
    step_fk = _foreign_key(
        "approval_workflow_steps", "fk_approval_workflow_steps_version_workflow_university"
    )
    assert tuple(step_fk.columns.keys()) == (
        "workflow_version_id",
        "workflow_id",
        "university_id",
    )
    action_step_fk = _foreign_key(
        "approval_actions", "fk_approval_actions_step_version_workflow_university"
    )
    action_instance_fk = _foreign_key(
        "approval_actions", "fk_approval_actions_instance_version_workflow_university"
    )
    assert tuple(action_step_fk.columns.keys()) == (
        "step_id",
        "workflow_version_id",
        "workflow_id",
        "university_id",
    )
    assert tuple(action_instance_fk.columns.keys()) == (
        "instance_id",
        "workflow_version_id",
        "workflow_id",
        "university_id",
    )
    assert tuple(_unique("approval_workflow_steps", ("workflow_version_id", "step_number")).columns.keys()) == (
        "workflow_version_id",
        "step_number",
    )


def test_primary_key_layout_includes_one_justified_uuid_version_table() -> None:
    integer_tables = {
        "users",
        "roles",
        "user_roles",
        "faculties",
        "departments",
        "student_profiles",
        "staff_profiles",
    }
    assert len(Base.metadata.tables) == 60
    assert sum(isinstance(table.c.id.type, Uuid) for table in Base.metadata.tables.values()) == 53
    for table_name, table in Base.metadata.tables.items():
        expected_type = Integer if table_name in integer_tables else Uuid
        assert isinstance(table.c.id.type, expected_type)
