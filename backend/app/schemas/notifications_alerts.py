"""Pydantic schemas for notifications, preferences, alert rules, and events."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# --- NOTIFICATIONS ---
class NotificationBase(BaseModel):
    recipient_id: int
    notification_type: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    message: str
    entity_type: Optional[str] = Field(None, max_length=128)
    entity_id: Optional[uuid.UUID] = None


class NotificationCreate(NotificationBase):
    pass


class NotificationRead(NotificationBase):
    id: uuid.UUID
    university_id: uuid.UUID
    created_at: datetime
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- NOTIFICATION PREFERENCES ---
class NotificationPreferenceBase(BaseModel):
    notification_type: str = Field(..., min_length=1, max_length=64)
    channel: str = Field("in_app", pattern="^in_app$")
    is_enabled: bool = True


class NotificationPreferenceCreate(NotificationPreferenceBase):
    pass


class NotificationPreferenceUpdate(BaseModel):
    is_enabled: bool


class NotificationPreferenceRead(NotificationPreferenceBase):
    id: uuid.UUID
    university_id: uuid.UUID
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- ALERT RULES ---
class AlertRuleBase(BaseModel):
    department_id: Optional[int] = None
    rule_type: str = Field(..., pattern="^(student_inactivity|overdue_milestone|duplicate_topic)$")
    threshold_value: Optional[int] = Field(None, ge=0)
    configuration: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    department_id: Optional[int] = None
    threshold_value: Optional[int] = Field(None, ge=0)
    configuration: Optional[dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class AlertRuleRead(AlertRuleBase):
    id: uuid.UUID
    university_id: uuid.UUID
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- ALERT EVENTS ---
class AlertEventBase(BaseModel):
    rule_id: uuid.UUID
    alert_type: str = Field(..., max_length=64)
    target_entity_type: str = Field(..., max_length=128)
    target_entity_id: uuid.UUID
    severity: str = Field(..., pattern="^(info|warning|critical)$")
    message: str
    status: str = Field("active", pattern="^(active|acknowledged|resolved|dismissed)$")


class AlertEventCreate(AlertEventBase):
    pass


class AlertEventUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|acknowledged|resolved|dismissed)$")


class AlertEventRead(AlertEventBase):
    id: uuid.UUID
    university_id: uuid.UUID
    detected_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

