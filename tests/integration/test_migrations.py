"""Alembic migration tests.

The other tests build their database from the models, so this file is what guarantees
the migrations stay in sync with models.py: change a model without adding a migration
and `test_migrations_match_the_models` fails.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

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
