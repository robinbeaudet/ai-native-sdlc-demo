"""
| Code                    | Rule                                                    |
|-------------------------|---------------------------------------------------------|
| RECEIPT_REQUIRED        | MEALS claims over EUR 50.00 need a receipt_url          |
| AMOUNT_EXCEEDS_MAXIMUM  | A single claim cannot exceed EUR 2,500.00               |
| VP_APPROVAL_REQUIRED    | Claims over EUR 500.00 can only be approved by a VP     |
"""

from dataclasses import dataclass
from decimal import Decimal

from expense_flow.models import ApproverRole, ExpenseCategory
from expense_flow.schemas import ExpenseClaimCreate

MEAL_RECEIPT_THRESHOLD = Decimal("50.00")
VP_APPROVAL_THRESHOLD = Decimal("500.00")
MAX_CLAIM_AMOUNT = Decimal("2500.00")


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
