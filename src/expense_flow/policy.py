"""
| Code                    | Rule                                                    |
|-------------------------|---------------------------------------------------------|
| RECEIPT_REQUIRED        | MEALS claims over EUR 50.00 need a receipt_url          |
| AMOUNT_EXCEEDS_MAXIMUM  | A single claim cannot exceed EUR 2,500.00               |
| VP_APPROVAL_REQUIRED    | Claims over EUR 500.00 can only be approved by a VP     |
| COST_CENTER_REQUIRED    | Claims over EUR 100.00 need a cost_center               |
| COST_CENTER_INVALID     | A cost_center, when given, must be CC- + 4 digits       |
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from expense_flow.models import ApproverRole, ExpenseCategory
from expense_flow.schemas import ExpenseClaimCreate

MEAL_RECEIPT_THRESHOLD = Decimal("50.00")
VP_APPROVAL_THRESHOLD = Decimal("500.00")
MAX_CLAIM_AMOUNT = Decimal("2500.00")
COST_CENTER_THRESHOLD = Decimal("100.00")
COST_CENTER_PATTERN = re.compile(r"CC-[0-9]{4}")  # case-sensitive, ASCII digits, no spaces


@dataclass(frozen=True)
class PolicyViolation:
    code: str
    message: str


def evaluate_submission(claim: ExpenseClaimCreate) -> list[PolicyViolation]:
    """Return the rules a new claim breaks (an empty list means it is compliant)."""
    violations: list[PolicyViolation] = []
    if (
        claim.category == ExpenseCategory.MEALS
        and claim.amount > MEAL_RECEIPT_THRESHOLD
        and not claim.receipt_url
    ):
        violations.append(
            PolicyViolation(
                "RECEIPT_REQUIRED",
                f"Meal claims over EUR {MEAL_RECEIPT_THRESHOLD} require a receipt_url",
            )
        )
    if claim.amount > MAX_CLAIM_AMOUNT:
        violations.append(
            PolicyViolation(
                "AMOUNT_EXCEEDS_MAXIMUM",
                f"A single claim cannot exceed EUR {MAX_CLAIM_AMOUNT}",
            )
        )
    if claim.cost_center is not None:
        if not COST_CENTER_PATTERN.fullmatch(claim.cost_center):
            violations.append(
                PolicyViolation(
                    "COST_CENTER_INVALID",
                    "A cost_center must be CC- followed by 4 digits, e.g. CC-1234",
                )
            )
    elif claim.amount > COST_CENTER_THRESHOLD:
        violations.append(
            PolicyViolation(
                "COST_CENTER_REQUIRED",
                f"Claims over EUR {COST_CENTER_THRESHOLD} require a cost_center",
            )
        )
    return violations


def evaluate_approval(amount: Decimal, approver_role: ApproverRole) -> list[PolicyViolation]:
    """Return the rules broken if someone with `approver_role` approves `amount`."""
    if amount > VP_APPROVAL_THRESHOLD and approver_role != ApproverRole.VP:
        return [
            PolicyViolation(
                "VP_APPROVAL_REQUIRED",
                f"Claims over EUR {VP_APPROVAL_THRESHOLD} must be approved by a VP",
            )
        ]
    return []
