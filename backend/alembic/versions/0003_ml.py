"""Optional registry, leased jobs and annotation-only predictions."""

from pathlib import Path

from alembic import op

revision = "0003_ml"
down_revision = "0002_reporting"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    for name in ("0003_schema.sql", "0003_integrity.sql"):
        connection.exec_driver_sql(Path(__file__).with_name(name).read_text())


def downgrade():
    raise RuntimeError("ML downgrade would destroy review history; restore a verified backup")
