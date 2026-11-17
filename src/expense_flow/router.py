from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from expense_flow.database import get_session
from expense_flow.models import ExpenseClaim
from expense_flow.schemas import (
    ApprovalRequest,
    ExpenseClaimCreate,
    ExpenseClaimRead,
    RejectionRequest,
)
from expense_flow.service import ExpenseService


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> ExpenseService:
    return ExpenseService(session)


ServiceDep = Annotated[ExpenseService, Depends(get_service)]

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post("", response_model=ExpenseClaimRead, status_code=status.HTTP_201_CREATED)
async def submit_claim(payload: ExpenseClaimCreate, service: ServiceDep) -> ExpenseClaim:
    """Submit a new claim. Policy violations return 422 with a `violations` list."""
    return await service.submit(payload)


@router.get("/{claim_id}", response_model=ExpenseClaimRead)
async def get_claim(claim_id: int, service: ServiceDep) -> ExpenseClaim:
    """Fetch a single claim by id."""
    return await service.get(claim_id)


@router.post("/{claim_id}/approve", response_model=ExpenseClaimRead)
async def approve_claim(
    claim_id: int, decision: ApprovalRequest, service: ServiceDep
) -> ExpenseClaim:
    """Approve a SUBMITTED claim (claims over EUR 500.00 require a VP)."""
    return await service.approve(claim_id, decision)


@router.post("/{claim_id}/reject", response_model=ExpenseClaimRead)
async def reject_claim(
    claim_id: int, decision: RejectionRequest, service: ServiceDep
) -> ExpenseClaim:
    """Reject a SUBMITTED claim with a reason."""
    return await service.reject(claim_id, decision)
