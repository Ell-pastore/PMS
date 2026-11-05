"""FastAPI routes for notifications, preferences, alert rules, and events."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..controller.notifications_alerts import (
    AlertEventController,
    AlertRuleController,
    NotificationPreferenceController,
    NotificationController,
)
from ..core.dependencies import TenantContext, get_db, get_tenant_context
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

notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])
preferences_router = APIRouter(prefix="/notification-preferences", tags=["Notification Preferences"])
alert_rules_router = APIRouter(prefix="/alert-rules", tags=["Alert Rules"])
alert_events_router = APIRouter(prefix="/alert-events", tags=["Alert Events"])


# --- NOTIFICATIONS ---
@notifications_router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def create_notification(
    data: NotificationCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return NotificationController.create_notification(db, tenant, data)


@notifications_router.get("", response_model=PaginatedResponse[NotificationRead])
def list_my_notifications(
    params: PaginationParams = Depends(),
    unread_only: bool = Query(False),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return NotificationController.list_my_notifications(
        db, tenant, params, unread_only=unread_only, search=search
    )


@notifications_router.get("/{notification_id}", response_model=NotificationRead)
def get_notification(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return NotificationController.get_notification(db, tenant, notification_id)


@notifications_router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_as_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return NotificationController.mark_as_read(db, tenant, notification_id)


@notifications_router.post("/{notification_id}/dismiss", response_model=NotificationRead)
def dismiss_notification(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return NotificationController.dismiss(db, tenant, notification_id)


@notifications_router.delete("/{notification_id}", status_code=status.HTTP_200_OK)
def delete_notification(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return NotificationController.delete_notification(db, tenant, notification_id)


# --- NOTIFICATION PREFERENCES ---
@preferences_router.post("", response_model=NotificationPreferenceRead, status_code=status.HTTP_201_CREATED)
def upsert_preference(
    data: NotificationPreferenceCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return NotificationPreferenceController.upsert_preference(db, tenant, data)


@preferences_router.get("", response_model=PaginatedResponse[NotificationPreferenceRead])
def list_preferences(
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return NotificationPreferenceController.list_preferences(db, tenant, params)


@preferences_router.delete("/{preference_id}", status_code=status.HTTP_200_OK)
def delete_preference(
    preference_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return NotificationPreferenceController.delete_preference(db, tenant, preference_id)


# --- ALERT RULES ---
@alert_rules_router.post("", response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED)
def create_alert_rule(
    data: AlertRuleCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return AlertRuleController.create_rule(db, tenant, data)


@alert_rules_router.get("", response_model=PaginatedResponse[AlertRuleRead])
def list_alert_rules(
    params: PaginationParams = Depends(),
    rule_type: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    is_enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return AlertRuleController.list_rules(
        db,
        tenant,
        params,
        rule_type=rule_type,
        department_id=department_id,
        is_enabled=is_enabled,
    )


@alert_rules_router.get("/{rule_id}", response_model=AlertRuleRead)
def get_alert_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return AlertRuleController.get_rule(db, tenant, rule_id)


@alert_rules_router.patch("/{rule_id}", response_model=AlertRuleRead)
@alert_rules_router.put("/{rule_id}", response_model=AlertRuleRead)
def update_alert_rule(
    rule_id: uuid.UUID,
    data: AlertRuleUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return AlertRuleController.update_rule(db, tenant, rule_id, data)


@alert_rules_router.delete("/{rule_id}", status_code=status.HTTP_200_OK)
def delete_alert_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return AlertRuleController.delete_rule(db, tenant, rule_id)


# --- ALERT EVENTS ---
@alert_events_router.post("", response_model=AlertEventRead, status_code=status.HTTP_201_CREATED)
def create_alert_event(
    data: AlertEventCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return AlertEventController.create_event(db, tenant, data)


@alert_events_router.get("", response_model=PaginatedResponse[AlertEventRead])
def list_alert_events(
    params: PaginationParams = Depends(),
    rule_id: Optional[uuid.UUID] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return AlertEventController.list_events(
        db,
        tenant,
        params,
        rule_id=rule_id,
        severity=severity,
        status=status,
    )


@alert_events_router.get("/{event_id}", response_model=AlertEventRead)
def get_alert_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return AlertEventController.get_event(db, tenant, event_id)


@alert_events_router.patch("/{event_id}", response_model=AlertEventRead)
@alert_events_router.put("/{event_id}", response_model=AlertEventRead)
def update_alert_event(
    event_id: uuid.UUID,
    data: AlertEventUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return AlertEventController.update_event(db, tenant, event_id, data)


@alert_events_router.delete("/{event_id}", status_code=status.HTTP_200_OK)
def delete_alert_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    return AlertEventController.delete_event(db, tenant, event_id)

