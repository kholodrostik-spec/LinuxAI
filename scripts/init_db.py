"""
scripts/init_db.py
Creates all tables and indexes from database/schema.sql.
Safe to run multiple times — all CREATE statements use IF NOT EXISTS.
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.db import get_connection

SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"


def main() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema)
        conn.commit()

    print("Database initialized successfully.")


if __name__ == "__main__":
    main()
