from expense_flow.policy import PolicyViolation


class ExpenseFlowError(Exception):
    """Base class for domain errors. `status_code` is the HTTP status returned to clients."""

    status_code = 400


class ClaimNotFoundError(ExpenseFlowError):
    status_code = 404

    def __init__(self, claim_id: int) -> None:
        super().__init__(f"Expense claim {claim_id} not found")


class InvalidStateTransitionError(ExpenseFlowError):
    status_code = 409

    def __init__(self, claim_id: int, status: str) -> None:
        super().__init__(f"Claim {claim_id} is already {status}")


class PolicyViolationError(ExpenseFlowError):
    status_code = 422

    def __init__(self, violations: list[PolicyViolation]) -> None:
        self.violations = violations
        super().__init__("Expense policy violation")
