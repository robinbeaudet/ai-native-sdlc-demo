"""Pydantic request and response bodies for the HTTP API."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from expense_flow.models import ApproverRole, ClaimStatus, ExpenseCategory


class ExpenseClaimCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=64)
    category: ExpenseCategory
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str = Field(min_length=1, max_length=500)
    receipt_url: str | None = Field(default=None, max_length=2048)
    # The format (CC-1234) is a policy rule, checked in policy.py so it gets a violation code.
    cost_center: str | None = Field(default=None, max_length=64)

    @field_validator("cost_center")
    @classmethod
    def blank_cost_center_is_none(cls, value: str | None) -> str | None:
        """An empty or whitespace-only cost center counts as no cost center."""
        if value is not None and not value.strip():
            return None
        return value


class ExpenseClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: str
    category: ExpenseCategory
    amount: Decimal
    currency: str
    description: str
    receipt_url: str | None
    cost_center: str | None
    status: ClaimStatus
    submitted_at: datetime
    decided_at: datetime | None
    approver_id: str | None
    approver_role: ApproverRole | None
    rejection_reason: str | None


class ApprovalRequest(BaseModel):
    approver_id: str = Field(min_length=1, max_length=64)
    approver_role: ApproverRole


class RejectionRequest(ApprovalRequest):
    reason: str = Field(min_length=1, max_length=500)
