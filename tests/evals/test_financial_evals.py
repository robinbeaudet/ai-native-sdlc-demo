"""Financial-precision evals: the money rules every change must keep green.

1. Amounts are stored and returned exactly (no float rounding).
2. Totals are exact, in Python and in SQL.
3. The API returns amounts as strings, never as JSON floats.
4. Sub-cent amounts are refused, not rounded.
5. The code in src/ never uses `float`.
"""

import ast
import json
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

from expense_flow.models import ExpenseCategory, ExpenseClaim

pytestmark = pytest.mark.eval

SRC = Path(__file__).parents[2] / "src"


@pytest.mark.parametrize("amount", ["0.01", "0.10", "0.30", "33.33", "999.99", "2500.00"])
async def test_amounts_round_trip_exactly(client, submit_claim, amount):
    created = await submit_claim(category="EQUIPMENT", amount=amount)
    fetched = (await client.get(f"/claims/{created['id']}")).json()
    assert fetched["amount"] == amount


async def test_totals_are_exact(session):
    """10,000 claims of EUR 0.01 add up to exactly EUR 100.00 (floats would drift)."""
    for _ in range(10_000):
        session.add(
            ExpenseClaim(
                employee_id="emp",
                category=ExpenseCategory.TRAVEL,
                amount=Decimal("0.01"),
                description="x",
            )
        )
    await session.commit()

    claims = (await session.scalars(select(ExpenseClaim))).all()
    assert sum(c.amount for c in claims) == Decimal("100.00")

    sql_total = await session.scalar(select(func.sum(ExpenseClaim.amount)))
    assert sql_total == Decimal("100.00")


async def test_amounts_are_json_strings(client, submit_claim):
    claim = await submit_claim(amount="19.90")
    response = await client.get(f"/claims/{claim['id']}")

    def fail_on_float(value):
        raise AssertionError(f"API returned a JSON float: {value}")

    body = json.loads(response.text, parse_float=fail_on_float)
    assert body["amount"] == "19.90"


@pytest.mark.parametrize("amount", ["10.001", "49.999"])
async def test_sub_cent_amounts_are_refused(client, amount):
    payload = {"employee_id": "e", "category": "TRAVEL", "amount": amount, "description": "x"}
    assert (await client.post("/claims", json=payload)).status_code == 422


def test_source_code_never_uses_float():
    offenders = []
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            uses_float = (isinstance(node, ast.Name) and node.id == "float") or (
                isinstance(node, ast.Constant) and isinstance(node.value, float)
            )
            if uses_float:
                offenders.append(f"{path.relative_to(SRC)}:{node.lineno}")
    assert offenders == [], f"float used in production code: {offenders}"
