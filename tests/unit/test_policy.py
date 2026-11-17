from decimal import Decimal

import pytest

from expense_flow.models import ApproverRole, ExpenseCategory
from expense_flow.policy import evaluate_approval, evaluate_submission
from expense_flow.schemas import ExpenseClaimCreate

pytestmark = pytest.mark.unit


def claim(category="TRAVEL", amount="100.00", receipt_url=None, cost_center="CC-1234"):
    return ExpenseClaimCreate(
        employee_id="emp-001",
        category=category,
        amount=Decimal(amount),
        description="test",
        receipt_url=receipt_url,
        cost_center=cost_center,
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
    ("amount", "cost_center", "expected"),
    [
        ("99.99", None, []),
        ("100.00", None, []),
        ("100.01", None, ["COST_CENTER_REQUIRED"]),
        ("100.01", "CC-1234", []),
    ],
)
def test_cost_center_threshold(amount, cost_center, expected):
    assert codes(evaluate_submission(claim(amount=amount, cost_center=cost_center))) == expected


@pytest.mark.parametrize("cost_center", ["CC-0000", "CC-1234", "CC-9999"])
def test_valid_cost_centers(cost_center):
    assert evaluate_submission(claim(amount="100.01", cost_center=cost_center)) == []


@pytest.mark.parametrize(
    "cost_center",
    [
        "cc-1234",
        "CC-123",
        "CC-12345",
        "CC1234",
        " CC-1234",
        "CC-1234 ",
        "CC-12a4",
        "CC-\u0661\u0662\u0663\u0664",  # Arabic-Indic digits
        "ABC",
    ],
)
@pytest.mark.parametrize("amount", ["50.00", "100.01"])
def test_invalid_cost_centers(amount, cost_center):
    assert codes(evaluate_submission(claim(amount=amount, cost_center=cost_center))) == [
        "INVALID_COST_CENTER"
    ]


@pytest.mark.parametrize("category", list(ExpenseCategory))
def test_cost_center_rule_applies_to_every_category(category):
    receipt = "https://receipts.example.com/r/1"
    assert codes(evaluate_submission(claim(category, "100.01", receipt, None))) == [
        "COST_CENTER_REQUIRED"
    ]


def test_cost_center_violations_are_reported_with_other_rules():
    assert codes(evaluate_submission(claim("MEALS", "60.00", None, "ABC"))) == [
        "RECEIPT_REQUIRED",
        "INVALID_COST_CENTER",
    ]
    assert codes(evaluate_submission(claim("EQUIPMENT", "3000.00", None, None))) == [
        "AMOUNT_EXCEEDS_MAXIMUM",
        "COST_CENTER_REQUIRED",
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
