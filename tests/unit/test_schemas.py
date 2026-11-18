from decimal import Decimal

import pytest
from pydantic import ValidationError

from expense_flow.money import Money
from expense_flow.schemas import ExpenseClaimCreate

pytestmark = pytest.mark.unit

VALID = {
    "employee_id": "emp-001",
    "category": "MEALS",
    "amount": "42.50",
    "description": "Team lunch",
}


def test_amount_is_parsed_as_decimal():
    assert ExpenseClaimCreate.model_validate(VALID).amount == Decimal("42.50")


def test_cost_center_is_optional():
    assert ExpenseClaimCreate.model_validate(VALID).cost_center is None
    with_cc = ExpenseClaimCreate.model_validate({**VALID, "cost_center": "CC-1234"})
    assert with_cc.cost_center == "CC-1234"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("amount", "0"),
        ("amount", "-1.00"),
        ("amount", "10.001"),  # sub-cent precision
        ("category", "CRYPTO"),
        ("employee_id", ""),
        ("description", ""),
    ],
)
def test_invalid_payloads_are_rejected(field, value):
    with pytest.raises(ValidationError):
        ExpenseClaimCreate.model_validate({**VALID, field: value})


def test_money_is_stored_as_integer_cents():
    money = Money()
    assert money.process_bind_param(Decimal("1234.56"), None) == 123456
    assert money.process_result_value(123456, None) == Decimal("1234.56")
    assert str(money.process_result_value(7550, None)) == "75.50"
