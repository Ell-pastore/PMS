"""PMS SQLAlchemy models for this domain."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    false,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .base import Base, TimestampMixin


def _uuid_column() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class AlertRule(TimestampMixin, Base):
    __tablename__ = "alert_rules"
    __table_args__ = (
        ForeignKeyConstraint(["department_id", "university_id"], ["departments.id", "departments.university_id"], ondelete="RESTRICT", name="fk_alert_rules_department_university"),
        ForeignKeyConstraint(["created_by_id", "university_id"], ["university_memberships.user_id", "university_memberships.university_id"], ondelete="RESTRICT", name="fk_alert_rules_created_by_membership"),
        UniqueConstraint("id", "university_id", name="uq_alert_rules_id_university"),
        CheckConstraint("rule_type IN ('student_inactivity', 'overdue_milestone', 'duplicate_topic')", name="ck_alert_rules_type"),
        CheckConstraint("threshold_value IS NULL OR threshold_value >= 0", name="ck_alert_rules_threshold"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    threshold_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    department: Mapped[Optional["Department"]] = relationship()
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    events: Mapped[list["AlertEvent"]] = relationship(back_populates="rule", passive_deletes=True)

class AlertEvent(Base):
    __tablename__ = "alert_events"
    __table_args__ = (
        ForeignKeyConstraint(["rule_id", "university_id"], ["alert_rules.id", "alert_rules.university_id"], ondelete="RESTRICT", name="fk_alert_events_rule_university"),
        UniqueConstraint("id", "university_id", name="uq_alert_events_id_university"),
        CheckConstraint("severity IN ('info', 'warning', 'critical')", name="ck_alert_events_severity"),
        CheckConstraint("status IN ('active', 'acknowledged', 'resolved', 'dismissed')", name="ck_alert_events_status"),
        Index("ix_alert_events_status_detected", "status", "detected_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    rule_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    rule: Mapped["AlertRule"] = relationship(back_populates="events")
    duplicate_candidate: Mapped[Optional["DuplicateTopicCandidate"]] = relationship(back_populates="alert_event", uselist=False, passive_deletes=True)

class DuplicateTopicCandidate(Base):
    __tablename__ = "duplicate_topic_candidates"
    __table_args__ = (
        ForeignKeyConstraint(["alert_event_id", "university_id"], ["alert_events.id", "alert_events.university_id"], ondelete="RESTRICT", name="fk_duplicate_candidates_alert_university"),
        ForeignKeyConstraint(["topic_a_id", "university_id"], ["research_topics.id", "research_topics.university_id"], ondelete="RESTRICT", name="fk_duplicate_candidates_topic_a_university"),
        ForeignKeyConstraint(["topic_b_id", "university_id"], ["research_topics.id", "research_topics.university_id"], ondelete="RESTRICT", name="fk_duplicate_candidates_topic_b_university"),
        ForeignKeyConstraint(["reviewed_by_id", "university_id"], ["university_memberships.user_id", "university_memberships.university_id"], ondelete="RESTRICT", name="fk_duplicate_candidates_reviewer_membership"),
        UniqueConstraint("alert_event_id", name="uq_duplicate_topic_candidates_alert"),
        CheckConstraint("topic_a_id < topic_b_id", name="ck_duplicate_topic_candidates_order"),
    )

    id: Mapped[uuid.UUID] = _uuid_column()
    university_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False)
    alert_event_id: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True)
    topic_a_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    topic_b_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    alert_event: Mapped["AlertEvent"] = relationship(back_populates="duplicate_candidate")
    topic_a: Mapped["ResearchTopic"] = relationship(foreign_keys=[topic_a_id])
    topic_b: Mapped["ResearchTopic"] = relationship(foreign_keys=[topic_b_id])
    reviewed_by: Mapped[Optional["User"]] = relationship(foreign_keys=[reviewed_by_id])
