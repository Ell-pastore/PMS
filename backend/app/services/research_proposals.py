"""Service layer for research proposals, revisions, participants, supervisors, and reviews."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from ..core.exceptions import (
    DuplicateResourceError,
    ForeignKeyViolationError,
    NotFoundError,
    SpecializedOperationError,
)
from ..core.pagination import PaginationParams, paginate
from ..models import (
    Department,
    ProposalParticipant,
    ProposalReview,
    ProposalRevision,
    ProposalStatusHistory,
    ProposalSupervisor,
    ResearchProposal,
    ResearchProject,
    ResearchTopic,
    StaffProfile,
    StudentProfile,
    UniversityMembership,
)
from ..schemas.research_proposals import (
    ProposalParticipantCreate,
    ProposalParticipantUpdate,
    ProposalReviewCreate,
    ProposalRevisionCreate,
    ProposalSupervisorCreate,
    ProposalSupervisorEnd,
    ResearchProposalCreate,
    ResearchProposalUpdate,
)


class ResearchProposalService:
    @staticmethod
    def create_proposal(
        db: Session,
        university_id: uuid.UUID,
        data: ResearchProposalCreate,
        user_id: int,
    ) -> ResearchProposal:
        # Validate topic and department in same university
        topic = db.scalar(
            select(ResearchTopic).where(
                ResearchTopic.id == data.topic_id,
                ResearchTopic.university_id == university_id,
            )
        )
        if not topic:
            raise ForeignKeyViolationError(f"Topic {data.topic_id} not found in this university")

        dept = db.scalar(
            select(Department).where(
                Department.id == data.department_id,
                Department.university_id == university_id,
            )
        )
        if not dept:
            raise ForeignKeyViolationError(f"Department {data.department_id} not found in this university")

        # Validate user membership
        membership = db.scalar(
            select(UniversityMembership).where(
                UniversityMembership.university_id == university_id,
                UniversityMembership.user_id == user_id,
            )
        )
        if not membership:
            raise ForeignKeyViolationError(f"User {user_id} has no membership in this university")

        proposal = ResearchProposal(
            university_id=university_id,
            topic_id=data.topic_id,
            department_id=data.department_id,
            submitting_user_id=user_id,
            title=data.title.strip(),
            abstract=data.abstract,
            research_problem=data.research_problem,
            objectives=data.objectives,
            methodology=data.methodology,
            expected_outcomes=data.expected_outcomes,
            status="draft",
        )
        db.add(proposal)
        db.flush()

        # Log initial history (single transaction with proposal creation)
        history = ProposalStatusHistory(
            university_id=university_id,
            proposal_id=proposal.id,
            previous_status=None,
            new_status="draft",
            actor_id=user_id,
            reason="Proposal created in draft state",
        )
        db.add(history)
        db.commit()
        db.refresh(proposal)

        return proposal

    @staticmethod
    def get_proposal(db: Session, university_id: uuid.UUID, proposal_id: uuid.UUID) -> ResearchProposal:
        proposal = db.scalar(
            select(ResearchProposal).where(
                ResearchProposal.id == proposal_id,
                ResearchProposal.university_id == university_id,
            )
        )
        if not proposal:
            raise NotFoundError(f"Research proposal {proposal_id} not found in this university")
        return proposal

    @staticmethod
    def list_proposals(
        db: Session,
        university_id: uuid.UUID,
        params: PaginationParams,
        department_id: Optional[int] = None,
        topic_id: Optional[uuid.UUID] = None,
        submitting_user_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[Sequence[ResearchProposal], int, int]:
        query = select(ResearchProposal).where(ResearchProposal.university_id == university_id).order_by(ResearchProposal.created_at.desc())
        if department_id:
            query = query.where(ResearchProposal.department_id == department_id)
        if topic_id:
            query = query.where(ResearchProposal.topic_id == topic_id)
        if submitting_user_id:
            query = query.where(ResearchProposal.submitting_user_id == submitting_user_id)
        if status:
            query = query.where(ResearchProposal.status == status)
        if search:
            query = query.where(ResearchProposal.title.ilike(f"%{search.strip()}%"))
        return paginate(query, db, params)

    @staticmethod
    def update_proposal(
        db: Session,
        university_id: uuid.UUID,
        proposal_id: uuid.UUID,
        data: ResearchProposalUpdate,
    ) -> ResearchProposal:
        proposal = ResearchProposalService.get_proposal(db, university_id, proposal_id)
        if proposal.status not in ("draft", "revision_requested"):
            raise SpecializedOperationError(
                f"Cannot directly edit proposal in status '{proposal.status}'. Submit a formal revision instead."
            )

        if data.department_id is not None and data.department_id != proposal.department_id:
            dept = db.scalar(
                select(Department).where(
                    Department.id == data.department_id,
                    Department.university_id == university_id,
                )
            )
            if not dept:
                raise ForeignKeyViolationError(f"Department {data.department_id} not found in this university")
            proposal.department_id = data.department_id

        if data.title is not None:
            proposal.title = data.title.strip()
        if data.abstract is not None:
            proposal.abstract = data.abstract
        if data.research_problem is not None:
            proposal.research_problem = data.research_problem
        if data.objectives is not None:
            proposal.objectives = data.objectives
        if data.methodology is not None:
            proposal.methodology = data.methodology
        if data.expected_outcomes is not None:
            proposal.expected_outcomes = data.expected_outcomes

        db.commit()
        db.refresh(proposal)
        return proposal

    @staticmethod
    def delete_proposal(db: Session, university_id: uuid.UUID, proposal_id: uuid.UUID) -> None:
        proposal = ResearchProposalService.get_proposal(db, university_id, proposal_id)
        if proposal.status != "draft":
            raise SpecializedOperationError(f"Cannot delete proposal in status '{proposal.status}'. Only draft proposals can be deleted.")

        # Guard against deleting a proposal that still has user-created data or
        # has been promoted to a project (RESTRICT foreign keys would otherwise
        # surface as a raw integrity error).
        blockers: list[str] = []
        if db.scalar(select(func.count()).select_from(ResearchProject).where(ResearchProject.proposal_id == proposal.id)):
            blockers.append("a linked research project")
        if db.scalar(select(func.count()).select_from(ProposalRevision).where(ProposalRevision.proposal_id == proposal.id)):
            blockers.append("revisions")
        if db.scalar(select(func.count()).select_from(ProposalParticipant).where(ProposalParticipant.proposal_id == proposal.id)):
            blockers.append("participants")
        if db.scalar(select(func.count()).select_from(ProposalSupervisor).where(ProposalSupervisor.proposal_id == proposal.id)):
            blockers.append("supervisors")
        if db.scalar(select(func.count()).select_from(ProposalReview).where(ProposalReview.proposal_id == proposal.id)):
            blockers.append("reviews")
        if blockers:
            raise SpecializedOperationError(
                f"Cannot delete proposal with existing {', '.join(blockers)}. Remove them first."
            )

        # Cascade the proposal's own status history rows (written automatically
        # at creation), then delete the proposal in a single transaction.
        db.execute(delete(ProposalStatusHistory).where(ProposalStatusHistory.proposal_id == proposal.id))
        db.delete(proposal)
        db.commit()

    @staticmethod
    def submit_proposal(
        db: Session,
        university_id: uuid.UUID,
        proposal_id: uuid.UUID,
        user_id: int,
    ) -> ResearchProposal:
        proposal = ResearchProposalService.get_proposal(db, university_id, proposal_id)
        if proposal.status not in ("draft", "revision_requested"):
            raise SpecializedOperationError(f"Cannot submit proposal currently in '{proposal.status}' state.")

        prev_status = proposal.status
        now = datetime.now(timezone.utc)
        proposal.status = "submitted"
        proposal.submitted_at = now

        history = ProposalStatusHistory(
            university_id=university_id,
            proposal_id=proposal.id,
            previous_status=prev_status,
            new_status="submitted",
            actor_id=user_id,
            reason="Proposal submitted for review",
        )
        db.add(history)
        db.commit()
        db.refresh(proposal)
        return proposal

    @staticmethod
    def transition_status(
        db: Session,
        university_id: uuid.UUID,
        proposal_id: uuid.UUID,
        new_status: str,
        actor_id: int,
        reason: Optional[str] = None,
    ) -> ResearchProposal:
        proposal = ResearchProposalService.get_proposal(db, university_id, proposal_id)
        valid_statuses = ("draft", "submitted", "under_review", "revision_requested", "approved", "rejected", "withdrawn")
        if new_status not in valid_statuses:
            raise SpecializedOperationError(f"Status '{new_status}' is invalid. Allowed: {valid_statuses}")

        prev_status = proposal.status
        proposal.status = new_status
        if new_status == "submitted" and not proposal.submitted_at:
            proposal.submitted_at = datetime.now(timezone.utc)

        history = ProposalStatusHistory(
            university_id=university_id,
            proposal_id=proposal.id,
            previous_status=prev_status,
            new_status=new_status,
            actor_id=actor_id,
            reason=reason,
        )
        db.add(history)
        db.commit()
        db.refresh(proposal)
        return proposal


class ProposalParticipantService:
    @staticmethod
    def add_participant(
        db: Session,
        university_id: uuid.UUID,
        proposal_id: uuid.UUID,
        data: ProposalParticipantCreate,
    ) -> ProposalParticipant:
        ResearchProposalService.get_proposal(db, university_id, proposal_id)

        # Validate student profile
        student = db.scalar(
            select(StudentProfile).where(
                StudentProfile.id == data.student_id,
                StudentProfile.university_id == university_id,
            )
        )
        if not student:
            raise ForeignKeyViolationError(f"Student {data.student_id} not found in this university")

        # Unique participant per proposal
        existing = db.scalar(
            select(ProposalParticipant).where(
                ProposalParticipant.proposal_id == proposal_id,
                ProposalParticipant.student_id == data.student_id,
            )
        )
        if existing:
            raise DuplicateResourceError(f"Student {data.student_id} already participating in proposal")

        # Unique lead check
        if data.is_lead:
            existing_lead = db.scalar(
                select(ProposalParticipant).where(
                    ProposalParticipant.proposal_id == proposal_id,
                    ProposalParticipant.is_lead.is_(True),
                )
            )
            if existing_lead:
                raise DuplicateResourceError("A lead participant is already designated for this proposal")

        part = ProposalParticipant(
            university_id=university_id,
            proposal_id=proposal_id,
            student_id=data.student_id,
            participation_role=data.participation_role,
            is_lead=data.is_lead,
        )
        db.add(part)
        db.commit()
        db.refresh(part)
        return part

    @staticmethod
    def remove_participant(
        db: Session,
        university_id: uuid.UUID,
        proposal_id: uuid.UUID,
        participant_id: uuid.UUID,
    ) -> None:
        part = db.scalar(
            select(ProposalParticipant).where(
                ProposalParticipant.id == participant_id,
                ProposalParticipant.proposal_id == proposal_id,
                ProposalParticipant.university_id == university_id,
            )
        )
        if not part:
            raise NotFoundError(f"Participant {participant_id} not found on this proposal")
        db.delete(part)
        db.commit()

    @staticmethod
    def list_participants(
        db: Session,
        university_id: uuid.UUID,
        proposal_id: uuid.UUID,
    ) -> Sequence[ProposalParticipant]:
        ResearchProposalService.get_proposal(db, university_id, proposal_id)
        return db.scalars(
            select(ProposalParticipant).where(
                ProposalParticipant.proposal_id == proposal_id,
                ProposalParticipant.university_id == university_id,
            )
        ).all()


class ProposalSupervisorService:
    @staticmethod
    def assign_supervisor(
        db: Session,
        university_id: uuid.UUID,
        proposal_id: uuid.UUID,
        data: ProposalSupervisorCreate,
        assigner_id: int,
    ) -> ProposalSupervisor:
        ResearchProposalService.get_proposal(db, university_id, proposal_id)

        staff = db.scalar(
            select(StaffProfile).where(
                StaffProfile.id == data.staff_id,
                StaffProfile.university_id == university_id,
            )
        )
        if not staff:
            raise ForeignKeyViolationError(f"Staff {data.staff_id} not found in this university")

        # Check active assignment for this staff
        existing = db.scalar(
            select(ProposalSupervisor).where(
                ProposalSupervisor.proposal_id == proposal_id,
                ProposalSupervisor.staff_id == data.staff_id,
                ProposalSupervisor.ended_at.is_(None),
            )
        )
        if existing:
            raise DuplicateResourceError(f"Staff {data.staff_id} is already actively supervising this proposal")

        # If primary, check no other active primary
        if data.assignment_role == "primary":
            primary = db.scalar(
                select(ProposalSupervisor).where(
                    ProposalSupervisor.proposal_id == proposal_id,
                    ProposalSupervisor.assignment_role == "primary",
                    ProposalSupervisor.ended_at.is_(None),
                )
            )
            if primary:
                raise DuplicateResourceError("Proposal already has an active primary supervisor")

        sup = ProposalSupervisor(
            university_id=university_id,
            proposal_id=proposal_id,
            staff_id=data.staff_id,
            assigned_by_id=assigner_id,
            assignment_role=data.assignment_role,
        )
        db.add(sup)
        db.commit()
        db.refresh(sup)
        return sup

    @staticmethod
    def end_supervisor(
        db: Session,
        university_id: uuid.UUID,
        proposal_id: uuid.UUID,
        supervisor_id: uuid.UUID,
        data: ProposalSupervisorEnd,
    ) -> ProposalSupervisor:
        sup = db.scalar(
            select(ProposalSupervisor).where(
                ProposalSupervisor.id == supervisor_id,
                ProposalSupervisor.proposal_id == proposal_id,
                ProposalSupervisor.university_id == university_id,
            )
        )
        if not sup:
            raise NotFoundError(f"Supervisor {supervisor_id} not found on this proposal")

        sup.ended_at = data.ended_at or datetime.now(timezone.utc)
        db.commit()
        db.refresh(sup)
        return sup

    @staticmethod
    def list_supervisors(
        db: Session,
        university_id: uuid.UUID,
        proposal_id: uuid.UUID,
        active_only: bool = True,
    ) -> Sequence[ProposalSupervisor]:
        ResearchProposalService.get_proposal(db, university_id, proposal_id)
        query = select(ProposalSupervisor).where(
            ProposalSupervisor.proposal_id == proposal_id,
            ProposalSupervisor.university_id == university_id,
        )
        if active_only:
            query = query.where(ProposalSupervisor.ended_at.is_(None))
        return db.scalars(query).all()


class ProposalRevisionService:
    @staticmethod
    def create_revision(
        db: Session,
        university_id: uuid.UUID,
        proposal_id: uuid.UUID,
        data: ProposalRevisionCreate,
        user_id: int,
    ) -> ProposalRevision:
        proposal = ResearchProposalService.get_proposal(db, university_id, proposal_id)

        # Get next revision number
        max_rev = db.scalar(
            select(func.coalesce(func.max(ProposalRevision.revision_number), 0)).where(
                ProposalRevision.proposal_id == proposal_id
            )
        )
        next_rev = (max_rev or 0) + 1

        rev = ProposalRevision(
            university_id=university_id,
            proposal_id=proposal_id,
            revision_number=next_rev,
            title=data.title.strip(),
            abstract=data.abstract,
            research_problem=data.research_problem,
            objectives=data.objectives,
            methodology=data.methodology,
            expected_outcomes=data.expected_outcomes,
            submitted_by_id=user_id,
        )
        db.add(rev)

        # Update proposal's active content to latest revision
        proposal.title = data.title.strip()
        if data.abstract is not None:
            proposal.abstract = data.abstract
        if data.research_problem is not None:
            proposal.research_problem = data.research_problem
        if data.objectives is not None:
            proposal.objectives = data.objectives
        if data.methodology is not None:
            proposal.methodology = data.methodology
        if data.expected_outcomes is not None:
            proposal.expected_outcomes = data.expected_outcomes

        db.commit()
        db.refresh(rev)
        return rev

    @staticmethod
    def list_revisions(
        db: Session,
        university_id: uuid.UUID,
        proposal_id: uuid.UUID,
    ) -> Sequence[ProposalRevision]:
        ResearchProposalService.get_proposal(db, university_id, proposal_id)
        return db.scalars(
            select(ProposalRevision)
            .where(
                ProposalRevision.proposal_id == proposal_id,
                ProposalRevision.university_id == university_id,
            )
            .order_by(ProposalRevision.revision_number.desc())
        ).all()


class ProposalReviewService:
    @staticmethod
    def create_review(
        db: Session,
        university_id: uuid.UUID,
        proposal_id: uuid.UUID,
        data: ProposalReviewCreate,
        reviewer_id: int,
    ) -> ProposalReview:
        proposal = ResearchProposalService.get_proposal(db, university_id, proposal_id)

        review = ProposalReview(
            university_id=university_id,
            proposal_id=proposal_id,
            reviewer_id=reviewer_id,
            decision=data.decision,
            comments=data.comments,
        )
        db.add(review)

        # If decision is decisive, advance status
        status_map = {
            "approved": "approved",
            "rejected": "rejected",
            "revision_requested": "revision_requested",
        }
        if data.decision in status_map:
            prev_status = proposal.status
            proposal.status = status_map[data.decision]
            history = ProposalStatusHistory(
                university_id=university_id,
                proposal_id=proposal.id,
                previous_status=prev_status,
                new_status=proposal.status,
                actor_id=reviewer_id,
                reason=f"Review decision: {data.decision}",
            )
            db.add(history)

        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    def list_reviews(
        db: Session,
        university_id: uuid.UUID,
        proposal_id: uuid.UUID,
    ) -> Sequence[ProposalReview]:
        ResearchProposalService.get_proposal(db, university_id, proposal_id)
        return db.scalars(
            select(ProposalReview)
            .where(
                ProposalReview.proposal_id == proposal_id,
                ProposalReview.university_id == university_id,
            )
            .order_by(ProposalReview.reviewed_at.desc())
        ).all()

