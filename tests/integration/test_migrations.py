"""Alembic migration tests.

The other tests build their database from the models, so this file is what guarantees
the migrations stay in sync with models.py: change a model without adding a migration
and `test_migrations_match_the_models` fails.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

pytestmark = pytest.mark.integration

ALEMBIC_INI = Path(__file__).parents[2] / "alembic.ini"


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "migrations.db"


@pytest.fixture
def alembic_config(db_path):
    config = Config(ALEMBIC_INI)
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")
    return config


def table_names(db_path):
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        return set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


def test_migrations_match_the_models(alembic_config):
    command.upgrade(alembic_config, "head")
    command.check(alembic_config)  # raises if models.py has changes with no migration


def test_upgrade_downgrade_upgrade(alembic_config, db_path):
    command.upgrade(alembic_config, "head")
    assert table_names(db_path) == {"expense_claims"}

    command.downgrade(alembic_config, "base")
    assert table_names(db_path) == set()

    command.upgrade(alembic_config, "head")
    assert table_names(db_path) == {"expense_claims"}


BASELINE = "e44d115a61f1"


def test_cost_center_migration_keeps_existing_claims(alembic_config, db_path):
    """Spec 002: claims saved before the migration survive it with cost_center = NULL,
    and are still there after a downgrade."""
    command.upgrade(alembic_config, BASELINE)
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO expense_claims (employee_id, category, amount, currency,"
                    " description, status, submitted_at) VALUES ('emp-001', 'TRAVEL',"
                    " 25000, 'EUR', 'Old claim', 'SUBMITTED', '2026-11-01 09:00:00')"
                )
            )

        command.upgrade(alembic_config, "head")
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT amount, description, cost_center FROM expense_claims")
            ).one()
        assert tuple(row) == (25000, "Old claim", None)

        command.downgrade(alembic_config, BASELINE)
        columns = {c["name"] for c in inspect(engine).get_columns("expense_claims")}
        assert "cost_center" not in columns
        with engine.connect() as conn:
            description = conn.execute(text("SELECT description FROM expense_claims")).scalar_one()
        assert description == "Old claim"
    finally:
        engine.dispose()
