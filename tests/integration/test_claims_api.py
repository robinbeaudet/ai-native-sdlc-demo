from decimal import Decimal

import pytest

from expense_flow.models import ExpenseCategory, ExpenseClaim

pytestmark = pytest.mark.integration

MANAGER = {"approver_id": "mgr-001", "approver_role": "MANAGER"}
VP = {"approver_id": "vp-001", "approver_role": "VP"}


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_submit_claim_returns_created_claim(submit_claim):
    claim = await submit_claim(amount="120.00")
    assert claim["id"] > 0
    assert claim["status"] == "SUBMITTED"
    assert claim["amount"] == "120.00"
    assert claim["currency"] == "EUR"
    assert claim["decided_at"] is None


async def test_get_claim_round_trips(client, submit_claim):
    created = await submit_claim()
    response = await client.get(f"/claims/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


async def test_unknown_claim_returns_404(client):
    assert (await client.get("/claims/999")).status_code == 404
    assert (await client.post("/claims/999/approve", json=MANAGER)).status_code == 404


async def test_meal_over_threshold_without_receipt_is_rejected(client):
    response = await client.post(
        "/claims",
        json={
            "employee_id": "emp-001",
            "category": "MEALS",
            "amount": "50.01",
            "description": "Client dinner",
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert [v["code"] for v in body["violations"]] == ["RECEIPT_REQUIRED"]


async def test_meal_over_threshold_with_receipt_is_accepted(submit_claim):
    claim = await submit_claim(
        category="MEALS", amount="80.00", receipt_url="https://receipts.example.com/r/42"
    )
    assert claim["receipt_url"] == "https://receipts.example.com/r/42"


async def test_claim_over_maximum_is_rejected(client):
    response = await client.post(
        "/claims",
        json={
            "employee_id": "emp-001",
            "category": "EQUIPMENT",
            "amount": "2500.01",
            "description": "Workstation",
            "cost_center": "CC-1234",
        },
    )
    assert response.status_code == 422
    assert [v["code"] for v in response.json()["violations"]] == ["AMOUNT_EXCEEDS_MAXIMUM"]


CLAIM = {"employee_id": "emp-001", "category": "TRAVEL", "description": "Taxi"}


async def test_claim_over_100_without_cost_center_is_rejected(client):
    response = await client.post("/claims", json={**CLAIM, "amount": "100.01"})
    assert response.status_code == 422
    assert [v["code"] for v in response.json()["violations"]] == ["COST_CENTER_REQUIRED"]


async def test_claim_of_exactly_100_needs_no_cost_center(client):
    response = await client.post("/claims", json={**CLAIM, "amount": "100.00"})
    assert response.status_code == 201
    assert response.json()["cost_center"] is None


async def test_cost_center_round_trips(client):
    response = await client.post(
        "/claims", json={**CLAIM, "amount": "100.01", "cost_center": "CC-1234"}
    )
    assert response.status_code == 201
    fetched = await client.get(f"/claims/{response.json()['id']}")
    assert fetched.json()["cost_center"] == "CC-1234"


async def test_invalid_cost_center_is_rejected(client):
    response = await client.post(
        "/claims", json={**CLAIM, "amount": "100.01", "cost_center": "cc-1234"}
    )
    assert response.status_code == 422
    assert [v["code"] for v in response.json()["violations"]] == ["INVALID_COST_CENTER"]


async def test_existing_claim_without_cost_center_can_be_approved(client, session):
    """A claim created before spec 002 has no cost center and can still be decided."""
    existing = ExpenseClaim(
        employee_id="emp-001",
        category=ExpenseCategory.TRAVEL,
        amount=Decimal("300.00"),
        description="Created before cost centers existed",
    )
    session.add(existing)
    await session.commit()

    response = await client.post(f"/claims/{existing.id}/approve", json=VP)
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
    assert response.json()["cost_center"] is None


async def test_schema_violation_returns_422(client):
    response = await client.post("/claims", json={"employee_id": "emp-001"})
    assert response.status_code == 422


async def test_manager_approves_small_claim(client, submit_claim):
    claim = await submit_claim(amount="500.00")
    response = await client.post(f"/claims/{claim['id']}/approve", json=MANAGER)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["approver_id"] == "mgr-001"
    assert body["approver_role"] == "MANAGER"
    assert body["decided_at"] is not None


async def test_manager_cannot_approve_claim_over_vp_threshold(client, submit_claim):
    claim = await submit_claim(amount="500.01")
    response = await client.post(f"/claims/{claim['id']}/approve", json=MANAGER)
    assert response.status_code == 422
    assert [v["code"] for v in response.json()["violations"]] == ["VP_APPROVAL_REQUIRED"]

    unchanged = (await client.get(f"/claims/{claim['id']}")).json()
    assert unchanged["status"] == "SUBMITTED"

    approved = await client.post(f"/claims/{claim['id']}/approve", json=VP)
    assert approved.status_code == 200
    assert approved.json()["approver_role"] == "VP"


async def test_reject_claim_records_reason(client, submit_claim):
    claim = await submit_claim()
    response = await client.post(
        f"/claims/{claim['id']}/reject", json={**MANAGER, "reason": "Duplicate submission"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REJECTED"
    assert body["rejection_reason"] == "Duplicate submission"


async def test_reject_requires_reason(client, submit_claim):
    claim = await submit_claim()
    response = await client.post(f"/claims/{claim['id']}/reject", json=MANAGER)
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("first", "second"),
    [("approve", "approve"), ("approve", "reject"), ("reject", "approve"), ("reject", "reject")],
)
async def test_decided_claims_cannot_be_decided_again(client, submit_claim, first, second):
    claim = await submit_claim()
    decision = {**VP, "reason": "Not reimbursable"}
    assert (await client.post(f"/claims/{claim['id']}/{first}", json=decision)).status_code == 200
    response = await client.post(f"/claims/{claim['id']}/{second}", json=decision)
    assert response.status_code == 409


async def test_openapi_schema_is_published(client):
    schema = (await client.get("/openapi.json")).json()
    assert {"/claims", "/claims/{claim_id}", "/claims/{claim_id}/approve"} <= set(schema["paths"])
