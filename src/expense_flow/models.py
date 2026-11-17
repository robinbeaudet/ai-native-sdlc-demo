"""SQLAlchemy database models. Changing a table requires an Alembic migration (see CLAUDE.md)."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from expense_flow.money import Money


class ExpenseCategory(StrEnum):
    MEALS = "MEALS"
    TRAVEL = "TRAVEL"
    LODGING = "LODGING"
    EQUIPMENT = "EQUIPMENT"
    OTHER = "OTHER"


class ClaimStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ApproverRole(StrEnum):
    MANAGER = "MANAGER"
    VP = "VP"


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ExpenseClaim(Base):
    __tablename__ = "expense_claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[ExpenseCategory]
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    description: Mapped[str] = mapped_column(String(500))
    receipt_url: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[ClaimStatus] = mapped_column(default=ClaimStatus.SUBMITTED, index=True)
    submitted_at: Mapped[datetime] = mapped_column(default=utc_now)
    decided_at: Mapped[datetime | None]
    approver_id: Mapped[str | None] = mapped_column(String(64))
    approver_role: Mapped[ApproverRole | None]
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
