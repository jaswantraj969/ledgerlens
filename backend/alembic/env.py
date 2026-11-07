"""Migrations. The URL comes from a config attribute or LEDGERLENS_DATABASE_URL."""

import os

from alembic import context
from sqlalchemy import create_engine

from ledgerlens.db.models import Base

url = context.config.attributes.get("database_url") or os.environ["LEDGERLENS_DATABASE_URL"]

engine = create_engine(url)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
    connection.commit()
engine.dispose()
