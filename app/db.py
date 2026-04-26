import psycopg
from app.config import DATABASE_URL


def get_connection() -> psycopg.Connection:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set in .env")
    return psycopg.connect(DATABASE_URL)
