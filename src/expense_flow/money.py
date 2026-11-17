from decimal import Decimal

from sqlalchemy import Dialect, Integer
from sqlalchemy.types import TypeDecorator


class Money(TypeDecorator[Decimal]):
    """A Decimal euro amount, stored in the database as integer cents.

    SQLite has no decimal column type, so a plain NUMERIC column would be stored as a
    float. Storing cents keeps every amount exact: Decimal("75.50") <-> 7550.
    """

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: Decimal | None, dialect: Dialect) -> int | None:
        return None if value is None else int(value * 100)

    def process_result_value(self, value: int | None, dialect: Dialect) -> Decimal | None:
        return None if value is None else Decimal(value).scaleb(-2)  # 7550 -> 75.50
