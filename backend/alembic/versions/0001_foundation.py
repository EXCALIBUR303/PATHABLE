"""Immutable foundation schema including PostGIS integrity triggers."""

from pathlib import Path

from alembic import op

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    connection = op.get_bind()
    for name in ("0001_schema.sql", "0001_integrity.sql"):
        connection.exec_driver_sql(Path(__file__).with_name(name).read_text())


def downgrade():
    # Never destroy application data through a casual downgrade.
    raise RuntimeError("Foundation downgrade is destructive; restore a verified backup instead")
