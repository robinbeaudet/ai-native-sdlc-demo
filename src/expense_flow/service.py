from sqlalchemy.ext.asyncio import AsyncSession

from expense_flow.exceptions import (
    ClaimNotFoundError,
    InvalidStateTransitionError,
    PolicyViolationError,
)
from expense_flow.models import ClaimStatus, ExpenseClaim, utc_now
from expense_flow.policy import evaluate_approval, evaluate_submission
from expense_flow.schemas import ApprovalRequest, ExpenseClaimCreate, RejectionRequest


class ExpenseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def submit(self, payload: ExpenseClaimCreate) -> ExpenseClaim:
        violations = evaluate_submission(payload)
        if violations:
            raise PolicyViolationError(violations)
        return await self._save(ExpenseClaim(**payload.model_dump()))

    async def get(self, claim_id: int) -> ExpenseClaim:
        claim = await self.session.get(ExpenseClaim, claim_id)
        if claim is None:
            raise ClaimNotFoundError(claim_id)
        return claim

    async def approve(self, claim_id: int, decision: ApprovalRequest) -> ExpenseClaim:
        claim = await self._get_submitted(claim_id)
        violations = evaluate_approval(claim.amount, decision.approver_role)
        if violations:
            raise PolicyViolationError(violations)
        claim.status = ClaimStatus.APPROVED
        claim.approver_id = decision.approver_id
        claim.approver_role = decision.approver_role
        claim.decided_at = utc_now()
        return await self._save(claim)

    async def reject(self, claim_id: int, decision: RejectionRequest) -> ExpenseClaim:
        claim = await self._get_submitted(claim_id)
        claim.status = ClaimStatus.REJECTED
        claim.approver_id = decision.approver_id
        claim.approver_role = decision.approver_role
        claim.rejection_reason = decision.reason
        claim.decided_at = utc_now()
        return await self._save(claim)

    async def _get_submitted(self, claim_id: int) -> ExpenseClaim:
        """Only SUBMITTED claims can be approved or rejected."""
        claim = await self.get(claim_id)
        if claim.status != ClaimStatus.SUBMITTED:
            raise InvalidStateTransitionError(claim_id, claim.status)
        return claim

    async def _save(self, claim: ExpenseClaim) -> ExpenseClaim:
        self.session.add(claim)
        await self.session.commit()
        await self.session.refresh(claim)
        return claim
