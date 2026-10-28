"""Compatibility exports for the domain-organized PMS model modules.

New code should import from the relevant domain module. This shim preserves the
historical backend.app.models.additional import path without defining any
duplicate ORM classes.
"""

from .alert import AlertEvent, AlertRule, DuplicateTopicCandidate
from .approval import (
    ApprovalAction,
    ApprovalInstance,
    ApprovalWorkflow,
    ApprovalWorkflowVersion,
    ApprovalWorkflowStep,
)
from .audit_log import AuditLog
from .grant_application import (
    GrantApplication,
    GrantApplicationParticipant,
    GrantApplicationReview,
    GrantApplicationStatusHistory,
)
from .grant_award import (
    GrantAward,
    GrantExpenditure,
    GrantProgressReport,
    GrantProjectAllocation,
)
from .grant_opportunity import FundingOpportunity, GrantOpportunity
from .milestone import MilestoneTemplate, ProjectMilestone
from .notification import Notification, NotificationPreference
from .progress_report import (
    ProjectComment,
    ProgressReport,
    ProgressReportReview,
    StudentActivity,
)
from .publication import (
    Publication,
    PublicationAuthor,
    PublicationProject,
    PublicationReview,
)
from .research_project import (
    ProjectParticipant,
    ProjectStatusHistory,
    ProjectSupervisor,
    ResearchProject,
)
from .research_proposal import (
    ProposalParticipant,
    ProposalRevision,
    ProposalReview,
    ProposalStatusHistory,
    ProposalSupervisor,
    ResearchProposal,
)
from .research_topic import ResearchTopic
from .retention_policy import RetentionPolicy
from .role import Permission, RolePermission
from .settings import (
    DepartmentLeadership,
    DepartmentSettings,
    SystemSetting,
    UniversitySettings,
)
from .stored_file import DocumentAttachment, StoredFile
from .university import University, UniversityMembership
from .User import AccountVerification

__all__ = [
    "AccountVerification",
    "AlertEvent",
    "AlertRule",
    "ApprovalAction",
    "ApprovalInstance",
    "ApprovalWorkflow",
    "ApprovalWorkflowVersion",
    "ApprovalWorkflowStep",
    "AuditLog",
    "DepartmentLeadership",
    "DepartmentSettings",
    "DocumentAttachment",
    "DuplicateTopicCandidate",
    "FundingOpportunity",
    "GrantApplication",
    "GrantApplicationParticipant",
    "GrantApplicationReview",
    "GrantApplicationStatusHistory",
    "GrantAward",
    "GrantExpenditure",
    "GrantOpportunity",
    "GrantProgressReport",
    "GrantProjectAllocation",
    "MilestoneTemplate",
    "Notification",
    "NotificationPreference",
    "Permission",
    "ProjectComment",
    "ProjectMilestone",
    "ProjectParticipant",
    "ProjectStatusHistory",
    "ProjectSupervisor",
    "ProposalParticipant",
    "ProposalRevision",
    "ProposalReview",
    "ProposalStatusHistory",
    "ProposalSupervisor",
    "Publication",
    "PublicationAuthor",
    "PublicationProject",
    "PublicationReview",
    "ProgressReport",
    "ProgressReportReview",
    "ResearchProject",
    "ResearchProposal",
    "ResearchTopic",
    "RetentionPolicy",
    "RolePermission",
    "StoredFile",
    "StudentActivity",
    "SystemSetting",
    "University",
    "UniversityMembership",
    "UniversitySettings",
]
