"""Central PMS SQLAlchemy model registry and public exports."""

from .alert import AlertEvent, AlertRule, DuplicateTopicCandidate
from .approval import (
    ApprovalAction,
    ApprovalInstance,
    ApprovalWorkflow,
    ApprovalWorkflowVersion,
    ApprovalWorkflowStep,
)
from .audit_log import AuditLog
from .base import Base, TimestampMixin
from .Department import Department
from .Faculty import Faculty
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
from .role import Permission, Role, RolePermission, UserRole
from .seed import INITIAL_ROLE_CODES, seed_initial_roles
from .settings import (
    DepartmentLeadership,
    DepartmentSettings,
    SystemSetting,
    UniversitySettings,
)
from .staff_profile import StaffProfile
from .stored_file import DocumentAttachment, StoredFile
from .student_profile import StudentProfile
from .university import University, UniversityMembership
from .User import AccountStatus, AccountVerification, User

__all__ = [
    "AccountStatus",
    "AccountVerification",
    "AlertEvent",
    "AlertRule",
    "ApprovalAction",
    "ApprovalInstance",
    "ApprovalWorkflow",
    "ApprovalWorkflowVersion",
    "ApprovalWorkflowStep",
    "AuditLog",
    "Base",
    "Department",
    "DepartmentLeadership",
    "DepartmentSettings",
    "DocumentAttachment",
    "DuplicateTopicCandidate",
    "Faculty",
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
    "INITIAL_ROLE_CODES",
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
    "Role",
    "RolePermission",
    "StaffProfile",
    "StoredFile",
    "StudentActivity",
    "StudentProfile",
    "SystemSetting",
    "TimestampMixin",
    "University",
    "UniversityMembership",
    "UniversitySettings",
    "User",
    "UserRole",
    "seed_initial_roles",
]
