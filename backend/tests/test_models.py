from sqlalchemy import Integer, Uuid
from sqlalchemy.orm import configure_mappers

from backend.app.models import Base, INITIAL_ROLE_CODES


def setup_module() -> None:
    configure_mappers()


def test_complete_model_registry_is_loaded() -> None:
    expected = {
        "users",
        "roles",
        "user_roles",
        "faculties",
        "departments",
        "student_profiles",
        "staff_profiles",
        "universities",
        "research_topics",
        "research_proposals",
        "research_projects",
        "publications",
        "grant_opportunities",
        "grant_applications",
        "grant_awards",
        "approval_workflows",
        "approval_instances",
        "notifications",
        "stored_files",
        "audit_logs",
        "retention_policies",
    }
    assert expected <= set(Base.metadata.tables)
    assert len(list(Base.registry.mappers)) == len(Base.metadata.tables)


def test_all_foreign_keys_resolve_to_registered_columns() -> None:
    for table in Base.metadata.tables.values():
        for foreign_key in table.foreign_keys:
            assert foreign_key.column.table.name in Base.metadata.tables
            assert foreign_key.column.name in foreign_key.column.table.c


def test_existing_integer_and_new_uuid_primary_keys() -> None:
    existing = {
        "users",
        "roles",
        "user_roles",
        "faculties",
        "departments",
        "student_profiles",
        "staff_profiles",
    }
    for table_name in existing:
        assert isinstance(Base.metadata.tables[table_name].c.id.type, Integer)

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing:
            assert isinstance(table.c.id.type, Uuid)


def test_required_partial_indexes_and_constraints_exist() -> None:
    publications = Base.metadata.tables["publications"]
    doi_index = next(i for i in publications.indexes if i.name == "uq_publications_normalized_doi")
    assert doi_index.unique is True
    assert "normalized_doi IS NOT NULL" in str(doi_index.dialect_options["postgresql"]["where"])

    authors = Base.metadata.tables["publication_authors"]
    assert any(i.name == "uq_publication_authors_corresponding" for i in authors.indexes)
    assert any(c.name == "ck_publication_authors_identity" for c in authors.constraints)

    project_participants = Base.metadata.tables["project_participants"]
    assert any(i.name == "uq_project_participants_active_lead" for i in project_participants.indexes)


def test_key_relationship_cardinality_and_seed_roles() -> None:
    user_mapper = Base.registry.mappers
    user = next(mapper for mapper in user_mapper if mapper.local_table.name == "users")
    assert user.relationships["student_profile"].uselist is False
    assert user.relationships["staff_profile"].uselist is False

    grant_application = next(
        mapper for mapper in Base.registry.mappers if mapper.local_table.name == "grant_applications"
    )
    assert grant_application.relationships["award"].uselist is False
    assert INITIAL_ROLE_CODES == (
        "student",
        "supervisor",
        "department_head",
        "research_admin",
        "grant_admin",
        "university_admin",
    )
