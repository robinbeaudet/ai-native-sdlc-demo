from decimal import Decimal

import pytest

from expense_flow.models import ApproverRole
from expense_flow.policy import evaluate_approval, evaluate_submission
from expense_flow.schemas import ExpenseClaimCreate

pytestmark = pytest.mark.unit


def claim(category="TRAVEL", amount="100.00", receipt_url=None, cost_center=None):
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
    # A valid cost center keeps this test about the receipt rule only (spec 002).
    assert evaluate_submission(claim("LODGING", "400.00", cost_center="CC-1234")) == []


@pytest.mark.parametrize(
    ("amount", "expected"),
    [("2500.00", []), ("2500.01", ["AMOUNT_EXCEEDS_MAXIMUM"])],
)
def test_maximum_claim_rule(amount, expected):
    # A valid cost center keeps this test about the maximum rule only (spec 002).
    assert codes(evaluate_submission(claim("EQUIPMENT", amount, cost_center="CC-1234"))) == (
        expected
    )


def test_a_claim_can_break_several_rules():
    # Spec 002: a claim over EUR 100.00 without a cost center also breaks that rule.
    assert codes(evaluate_submission(claim("MEALS", "3000.00"))) == [
        "RECEIPT_REQUIRED",
        "AMOUNT_EXCEEDS_MAXIMUM",
        "COST_CENTER_REQUIRED",
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
def test_cost_center_required_over_threshold(amount, cost_center, expected):
    assert codes(evaluate_submission(claim("TRAVEL", amount, cost_center=cost_center))) == (
        expected
    )


INVALID_COST_CENTERS = ["cc-1234", "CC-123", "CC-12345", "1234", "", "   ", " CC-1234", "CC-1234 "]
INVALID_COST_CENTERS += ["CC-12", "CC1234", "CC-12a4", "CC-١٢٣٤"]  # Arabic-Indic digits


@pytest.mark.parametrize("amount", ["50.00", "100.00", "100.01"])
@pytest.mark.parametrize("cost_center", INVALID_COST_CENTERS)
def test_malformed_cost_center_is_refused_at_any_amount(amount, cost_center):
    assert codes(evaluate_submission(claim("TRAVEL", amount, cost_center=cost_center))) == [
        "COST_CENTER_INVALID"
    ]


@pytest.mark.parametrize("amount", ["50.00", "100.01"])
@pytest.mark.parametrize("cost_center", ["CC-0000", "CC-1234", "CC-9999"])
def test_well_formed_cost_center_is_accepted(amount, cost_center):
    assert evaluate_submission(claim("TRAVEL", amount, cost_center=cost_center)) == []


def test_missing_receipt_and_cost_center_are_reported_together():
    assert codes(evaluate_submission(claim("MEALS", "120.00"))) == [
        "RECEIPT_REQUIRED",
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
