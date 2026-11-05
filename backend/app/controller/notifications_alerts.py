"""Controllers for notifications, preferences, alert rules, and events."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from ..core.dependencies import TenantContext
from ..core.pagination import PaginatedResponse, PaginationParams
from ..schemas.notifications_alerts import (
    AlertEventCreate,
    AlertEventRead,
    AlertEventUpdate,
    AlertRuleCreate,
    AlertRuleRead,
    AlertRuleUpdate,
    NotificationCreate,
    NotificationPreferenceCreate,
    NotificationPreferenceRead,
    NotificationRead,
)
from ..services.notifications_alerts import (
    AlertEventService,
    AlertRuleService,
    NotificationPreferenceService,
    NotificationService,
)


class NotificationController:
    @staticmethod
    def create_notification(
        db: Session,
        tenant: TenantContext,
        data: NotificationCreate,
    ) -> NotificationRead:
        notif = NotificationService.create_notification(db, tenant.university_id, data)
        return NotificationRead.model_validate(notif)

    @staticmethod
    def get_notification(
        db: Session,
        tenant: TenantContext,
        notification_id: uuid.UUID,
    ) -> NotificationRead:
        notif = NotificationService.get_notification(db, tenant.university_id, notification_id, tenant.user.id)
        return NotificationRead.model_validate(notif)

    @staticmethod
    def list_my_notifications(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        unread_only: bool = False,
        search: Optional[str] = None,
    ) -> PaginatedResponse[NotificationRead]:
        items, total, total_pages = NotificationService.list_my_notifications(
            db, tenant.university_id, tenant.user.id, params, unread_only=unread_only, search=search
        )
        return PaginatedResponse(
            items=[NotificationRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def mark_as_read(
        db: Session,
        tenant: TenantContext,
        notification_id: uuid.UUID,
    ) -> NotificationRead:
        notif = NotificationService.mark_as_read(db, tenant.university_id, notification_id, tenant.user.id)
        return NotificationRead.model_validate(notif)

    @staticmethod
    def dismiss(
        db: Session,
        tenant: TenantContext,
        notification_id: uuid.UUID,
    ) -> NotificationRead:
        notif = NotificationService.dismiss(db, tenant.university_id, notification_id, tenant.user.id)
        return NotificationRead.model_validate(notif)

    @staticmethod
    def delete_notification(
        db: Session,
        tenant: TenantContext,
        notification_id: uuid.UUID,
    ) -> dict[str, str]:
        NotificationService.delete_notification(db, tenant.university_id, notification_id, tenant.user.id)
        return {"status": "success", "message": f"Notification {notification_id} deleted"}


class NotificationPreferenceController:
    @staticmethod
    def upsert_preference(
        db: Session,
        tenant: TenantContext,
        data: NotificationPreferenceCreate,
    ) -> NotificationPreferenceRead:
        pref = NotificationPreferenceService.upsert_preference(
            db, tenant.university_id, tenant.user.id, data
        )
        return NotificationPreferenceRead.model_validate(pref)

    @staticmethod
    def list_preferences(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
    ) -> PaginatedResponse[NotificationPreferenceRead]:
        items, total, total_pages = NotificationPreferenceService.list_preferences(
            db, tenant.university_id, tenant.user.id, params
        )
        return PaginatedResponse(
            items=[NotificationPreferenceRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def delete_preference(
        db: Session,
        tenant: TenantContext,
        preference_id: uuid.UUID,
    ) -> dict[str, str]:
        NotificationPreferenceService.delete_preference(
            db, tenant.university_id, preference_id, tenant.user.id
        )
        return {"status": "success", "message": f"Preference {preference_id} deleted"}


class AlertRuleController:
    @staticmethod
    def create_rule(
        db: Session,
        tenant: TenantContext,
        data: AlertRuleCreate,
    ) -> AlertRuleRead:
        rule = AlertRuleService.create_rule(db, tenant.university_id, data, tenant.user.id)
        return AlertRuleRead.model_validate(rule)

    @staticmethod
    def get_rule(
        db: Session,
        tenant: TenantContext,
        rule_id: uuid.UUID,
    ) -> AlertRuleRead:
        rule = AlertRuleService.get_rule(db, tenant.university_id, rule_id)
        return AlertRuleRead.model_validate(rule)

    @staticmethod
    def list_rules(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        rule_type: Optional[str] = None,
        department_id: Optional[int] = None,
        is_enabled: Optional[bool] = None,
    ) -> PaginatedResponse[AlertRuleRead]:
        items, total, total_pages = AlertRuleService.list_rules(
            db,
            tenant.university_id,
            params,
            rule_type=rule_type,
            department_id=department_id,
            is_enabled=is_enabled,
        )
        return PaginatedResponse(
            items=[AlertRuleRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_rule(
        db: Session,
        tenant: TenantContext,
        rule_id: uuid.UUID,
        data: AlertRuleUpdate,
    ) -> AlertRuleRead:
        rule = AlertRuleService.update_rule(db, tenant.university_id, rule_id, data)
        return AlertRuleRead.model_validate(rule)

    @staticmethod
    def delete_rule(
        db: Session,
        tenant: TenantContext,
        rule_id: uuid.UUID,
    ) -> dict[str, str]:
        AlertRuleService.delete_rule(db, tenant.university_id, rule_id)
        return {"status": "success", "message": f"Alert rule {rule_id} deleted"}


class AlertEventController:
    @staticmethod
    def create_event(
        db: Session,
        tenant: TenantContext,
        data: AlertEventCreate,
    ) -> AlertEventRead:
        event = AlertEventService.create_event(db, tenant.university_id, data)
        return AlertEventRead.model_validate(event)

    @staticmethod
    def get_event(
        db: Session,
        tenant: TenantContext,
        event_id: uuid.UUID,
    ) -> AlertEventRead:
        event = AlertEventService.get_event(db, tenant.university_id, event_id)
        return AlertEventRead.model_validate(event)

    @staticmethod
    def list_events(
        db: Session,
        tenant: TenantContext,
        params: PaginationParams,
        rule_id: Optional[uuid.UUID] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[AlertEventRead]:
        items, total, total_pages = AlertEventService.list_events(
            db,
            tenant.university_id,
            params,
            rule_id=rule_id,
            severity=severity,
            status=status,
        )
        return PaginatedResponse(
            items=[AlertEventRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def update_event(
        db: Session,
        tenant: TenantContext,
        event_id: uuid.UUID,
        data: AlertEventUpdate,
    ) -> AlertEventRead:
        event = AlertEventService.update_event(db, tenant.university_id, event_id, data)
        return AlertEventRead.model_validate(event)

    @staticmethod
    def delete_event(
        db: Session,
        tenant: TenantContext,
        event_id: uuid.UUID,
    ) -> dict[str, str]:
        AlertEventService.delete_event(db, tenant.university_id, event_id)
        return {"status": "success", "message": f"Alert event {event_id} deleted"}

