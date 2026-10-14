"""Immutable reporting/evidence/restriction/lease schema and integrity rules."""

from pathlib import Path

from alembic import op

revision = "0002_reporting"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    for name in ("0002_schema.sql", "0002_integrity.sql"):
        connection.exec_driver_sql(Path(__file__).with_name(name).read_text())
    # Existing campuses receive a reset at the new revision; no data is reset.
    connection.exec_driver_sql("""
        WITH changed AS (
          UPDATE graph_state SET version=version+1, updated_at=clock_timestamp()
          RETURNING campus_id, version
        ) INSERT INTO graph_events(campus_id,graph_version,event_type,changed_edge_ids,reason)
          SELECT campus_id,version,'graph.reset','{}'::uuid[],'reporting_enabled' FROM changed
    """)


def downgrade():
    raise RuntimeError("Reporting downgrade would destroy records; restore a verified backup")
