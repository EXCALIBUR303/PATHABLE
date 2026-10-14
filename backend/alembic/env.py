from sqlalchemy import create_engine

from alembic import context
from app.core.config import get_settings
from app.models import ml, reporting  # noqa: F401
from app.models.entities import Base

engine = create_engine(get_settings().database_url(owner=True), hide_parameters=True)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
