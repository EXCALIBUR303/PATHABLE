"""Reset only disposable browser-test rate buckets between independent test cases."""

import json
import re
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import get_settings

state = json.loads((ROOT / ".local/e2e-state.json").read_text())
name = state["database"]
settings = get_settings()
if not re.fullmatch(r"pathable_e2e_[0-9a-f]{12}", name) or name == settings.postgres_db:
    raise SystemExit("Refusing to modify a non-disposable browser database")
kwargs = settings.database_url(owner=True, database=name).translate_connect_args(
    username="user", database="dbname"
)
with psycopg.connect(**kwargs) as connection:
    connection.execute("TRUNCATE rate_limit_buckets")
