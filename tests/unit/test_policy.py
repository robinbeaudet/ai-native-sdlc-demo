from decimal import Decimal

import pytest

from expense_flow.models import ApproverRole
from expense_flow.policy import evaluate_approval, evaluate_submission
from expense_flow.schemas import ExpenseClaimCreate

pytestmark = pytest.mark.unit


def claim(category="TRAVEL", amount="100.00", receipt_url=None):
    return ExpenseClaimCreate(
        employee_id="emp-001",
        category=category,
        amount=Decimal(amount),
        description="test",
        receipt_url=receipt_url,
    )


def codes(violations):
    return [v.code for v in violations]


@pytest.mark.parametrize(
    ("amount", "receipt_url", "expected"),
    [
        ("49.99", None, []),
        ("50.00", None, []),
        ("50.01", None, ["RECEIPT_REQUIRED"]),
        ("50.01", "https://receipts.example.com/r/1", []),
    ],
)
def test_meal_receipt_rule(amount, receipt_url, expected):
    assert codes(evaluate_submission(claim("MEALS", amount, receipt_url))) == expected


def test_receipt_rule_only_applies_to_meals():
    assert evaluate_submission(claim("LODGING", "400.00")) == []


@pytest.mark.parametrize(
    ("amount", "expected"),
    [("2500.00", []), ("2500.01", ["AMOUNT_EXCEEDS_MAXIMUM"])],
)
def test_maximum_claim_rule(amount, expected):
    assert codes(evaluate_submission(claim("EQUIPMENT", amount))) == expected


def test_a_claim_can_break_several_rules():
    assert codes(evaluate_submission(claim("MEALS", "3000.00"))) == [
        "RECEIPT_REQUIRED",
        "AMOUNT_EXCEEDS_MAXIMUM",
    ]


@pytest.mark.parametrize(
    ("amount", "role", "expected"),
    [
        ("500.00", ApproverRole.MANAGER, []),
        ("500.01", ApproverRole.MANAGER, ["VP_APPROVAL_REQUIRED"]),
        ("500.01", ApproverRole.VP, []),
    ],
)
def test_vp_approval_rule(amount, role, expected):
    assert codes(evaluate_approval(Decimal(amount), role)) == expected
