"""Service layer for notifications, preferences, alert rules, and events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..core.exceptions import (
    DuplicateResourceError,
    ForbiddenError,
    ForeignKeyViolationError,
    NotFoundError,
)
from ..core.pagination import PaginationParams, paginate
from ..models import (
    AlertEvent,
    AlertRule,
    Department,
    Notification,
    NotificationPreference,
    UniversityMembership,
)
from ..schemas.notifications_alerts import (
    AlertEventCreate,
    AlertEventUpdate,
    AlertRuleCreate,
    AlertRuleUpdate,
    NotificationCreate,
    NotificationPreferenceCreate,
    NotificationPreferenceUpdate,
)


class NotificationService:
    @staticmethod
    def create_notification(
        db: Session,
        university_id: uuid.UUID,
        data: NotificationCreate,
    ) -> Notification:
        recipient_membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == data.recipient_id,
            )
        )
        if not recipient_membership:
            raise ForeignKeyViolationError(f"Recipient {data.recipient_id} has no membership in this university")

        notif = Notification(
            university_id=university_id,
            recipient_id=data.recipient_id,
            notification_type=data.notification_type,
            title=data.title.strip(),
            message=data.message.strip(),
            entity_type=data.entity_type,
            entity_id=data.entity_id,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    @staticmethod
    def get_notification(
        db: Session,
        university_id: uuid.UUID,
        notification_id: uuid.UUID,
        user_id: int,
    ) -> Notification:
        notif = db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.university_id == university_id,
            )
        )
        if not notif:
            raise NotFoundError(f"Notification {notification_id} not found in this university")
        if notif.recipient_id != user_id:
            raise ForbiddenError("Cannot access notification belonging to another user")
        return notif

    @staticmethod
    def list_my_notifications(
        db: Session,
        university_id: uuid.UUID,
        user_id: int,
        params: PaginationParams,
        unread_only: bool = False,
        search: Optional[str] = None,
    ) -> tuple[Sequence[Notification], int, int]:
        query = (
            select(Notification)
            .where(
                Notification.university_id == university_id,
                Notification.recipient_id == user_id,
            )
            .order_by(Notification.created_at.desc())
        )
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        if search:
            s = f"%{search.strip()}%"
            query = query.where(or_(Notification.title.ilike(s), Notification.message.ilike(s)))
        return paginate(query, db, params)

    @staticmethod
    def mark_as_read(
        db: Session,
        university_id: uuid.UUID,
        notification_id: uuid.UUID,
        user_id: int,
    ) -> Notification:
        notif = NotificationService.get_notification(db, university_id, notification_id, user_id)
        if not notif.read_at:
            notif.read_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(notif)
        return notif

    @staticmethod
    def dismiss(
        db: Session,
        university_id: uuid.UUID,
        notification_id: uuid.UUID,
        user_id: int,
    ) -> Notification:
        notif = NotificationService.get_notification(db, university_id, notification_id, user_id)
        if not notif.dismissed_at:
            notif.dismissed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(notif)
        return notif

    @staticmethod
    def delete_notification(
        db: Session,
        university_id: uuid.UUID,
        notification_id: uuid.UUID,
        user_id: int,
    ) -> None:
        notif = NotificationService.get_notification(db, university_id, notification_id, user_id)
        db.delete(notif)
        db.commit()


class NotificationPreferenceService:
    @staticmethod
    def upsert_preference(
        db: Session,
        university_id: uuid.UUID,
        user_id: int,
        data: NotificationPreferenceCreate,
    ) -> NotificationPreference:
        pref = db.scalar(
            select(NotificationPreference).where(
                NotificationPreference.university_id == university_id,
                NotificationPreference.user_id == user_id,
                NotificationPreference.notification_type == data.notification_type.strip(),
                NotificationPreference.channel == data.channel,
            )
        )
        if not pref:
            pref = NotificationPreference(
                university_id=university_id,
                user_id=user_id,
                notification_type=data.notification_type.strip(),
                channel=data.channel,
                is_enabled=data.is_enabled,
            )
            db.add(pref)
        else:
            pref.is_enabled = data.is_enabled

        db.commit()
        db.refresh(pref)
        return pref

    @staticmethod
    def list_preferences(
        db: Session,
        university_id: uuid.UUID,
        user_id: int,
        params: PaginationParams,
    ) -> tuple[Sequence[NotificationPreference], int, int]:
        query = (
            select(NotificationPreference)
            .where(
                NotificationPreference.university_id == university_id,
                NotificationPreference.user_id == user_id,
            )
            .order_by(NotificationPreference.notification_type.asc())
        )
        return paginate(query, db, params)

    @staticmethod
    def delete_preference(
        db: Session,
        university_id: uuid.UUID,
        preference_id: uuid.UUID,
        user_id: int,
    ) -> None:
        pref = db.scalar(
            select(NotificationPreference).where(
                NotificationPreference.id == preference_id,
                NotificationPreference.university_id == university_id,
                NotificationPreference.user_id == user_id,
            )
        )
        if not pref:
            raise NotFoundError(f"Notification preference {preference_id} not found")
        db.delete(pref)
        db.commit()


class AlertRuleService:
    @staticmethod
    def create_rule(
        db: Session,
        university_id: uuid.UUID,
        data: AlertRuleCreate,
        user_id: int,
    ) -> AlertRule:
        if data.department_id:
            dept = db.scalar(
                select(Department).where(
                    Department.id == data.department_id,
                    Department.university_id == university_id,
                )
            )
            if not dept:
                raise ForeignKeyViolationError(f"Department {data.department_id} not found in this university")

        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        rule = AlertRule(
            university_id=university_id,
            department_id=data.department_id,
            rule_type=data.rule_type,
            threshold_value=data.threshold_value,
            configuration=data.configuration,
            is_enabled=data.is_enabled,
            created_by_id=user_id,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def get_rule(db: Session, university_id: uuid.UUID, rule_id: uuid.UUID) -> AlertRule:
        rule = db.scalar(
            select(AlertRule).where(
                AlertRule.id == rule_id,
                AlertRule.university_id == university_id,
            )
        )
        if not rule:
            raise NotFoundError(f"Alert rule {rule_id} not found in this university")
        return rule

    @staticmethod
    def list_rules(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        rule_type: Optional[str] = None,
        department_id: Optional[int] = None,
        is_enabled: Optional[bool] = None,
    ) -> tuple[Sequence[AlertRule], int, int]:
        query = select(AlertRule).where(AlertRule.university_id == university_id).order_by(AlertRule.created_at.desc())
        if rule_type:
            query = query.where(AlertRule.rule_type == rule_type)
        if department_id:
            query = query.where(AlertRule.department_id == department_id)
        if is_enabled is not None:
            query = query.where(AlertRule.is_enabled == is_enabled)
        return paginate(query, db, params)

    @staticmethod
    def update_rule(
        db: Session,
        university_id: uuid.UUID,
        rule_id: uuid.UUID,
        data: AlertRuleUpdate,
    ) -> AlertRule:
        rule = AlertRuleService.get_rule(db, university_id, rule_id)
        if data.department_id is not None and data.department_id != rule.department_id:
            dept = db.scalar(
                select(Department).where(
                    Department.id == data.department_id,
                    Department.university_id == university_id,
                )
            )
            if not dept:
                raise ForeignKeyViolationError(f"Department {data.department_id} not found in this university")
            rule.department_id = data.department_id

        if data.threshold_value is not None:
            rule.threshold_value = data.threshold_value
        if data.configuration is not None:
            rule.configuration = data.configuration
        if data.is_enabled is not None:
            rule.is_enabled = data.is_enabled

        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def delete_rule(db: Session, university_id: uuid.UUID, rule_id: uuid.UUID) -> None:
        rule = AlertRuleService.get_rule(db, university_id, rule_id)
        db.delete(rule)
        db.commit()


class AlertEventService:
    @staticmethod
    def create_event(
        db: Session,
        university_id: uuid.UUID,
        data: AlertEventCreate,
    ) -> AlertEvent:
        AlertRuleService.get_rule(db, university_id, data.rule_id)

        event = AlertEvent(
            university_id=university_id,
            rule_id=data.rule_id,
            alert_type=data.alert_type,
            target_entity_type=data.target_entity_type,
            target_entity_id=data.target_entity_id,
            severity=data.severity,
            message=data.message.strip(),
            status=data.status or "active",
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def get_event(db: Session, university_id: uuid.UUID, event_id: uuid.UUID) -> AlertEvent:
        event = db.scalar(
            select(AlertEvent).where(
                AlertEvent.id == event_id,
                AlertEvent.university_id == university_id,
            )
        )
        if not event:
            raise NotFoundError(f"Alert event {event_id} not found in this university")
        return event

    @staticmethod
    def list_events(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        rule_id: Optional[uuid.UUID] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
    ) -> tuple[Sequence[AlertEvent], int, int]:
        query = select(AlertEvent).where(AlertEvent.university_id == university_id).order_by(AlertEvent.detected_at.desc())
        if rule_id:
            query = query.where(AlertEvent.rule_id == rule_id)
        if severity:
            query = query.where(AlertEvent.severity == severity)
        if status:
            query = query.where(AlertEvent.status == status)
        return paginate(query, db, params)

    @staticmethod
    def update_event(
        db: Session,
        university_id: uuid.UUID,
        event_id: uuid.UUID,
        data: AlertEventUpdate,
    ) -> AlertEvent:
        event = AlertEventService.get_event(db, university_id, event_id)
        event.status = data.status
        if data.status == "resolved" and not event.resolved_at:
            event.resolved_at = datetime.now(timezone.utc)
        elif data.status != "resolved":
            event.resolved_at = None

        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def delete_event(db: Session, university_id: uuid.UUID, event_id: uuid.UUID) -> None:
        event = AlertEventService.get_event(db, university_id, event_id)
        db.delete(event)
        db.commit()

