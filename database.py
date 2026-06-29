"""Database connection and utilities for Reddit Vector Search."""

from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
import config


def get_connection():
    """Create a new database connection with pgvector type registered."""
    conn = psycopg2.connect(
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        database=config.POSTGRES_DB,
        user=config.POSTGRES_USER,
        password=config.POSTGRES_PASSWORD,
    )
    register_vector(conn)
    return conn


@contextmanager
def get_cursor(dict_cursor=True):
    """Context manager for database cursor.

    Args:
        dict_cursor: If True, returns rows as dictionaries.

    Yields:
        cursor: Database cursor
    """
    conn = get_connection()
    cursor_factory = RealDictCursor if dict_cursor else None
    cursor = conn.cursor(cursor_factory=cursor_factory)
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def test_connection():
    """Test database connection and return server info."""
    with get_cursor() as cur:
        cur.execute("SELECT version();")
        version = cur.fetchone()
        cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
        pgvector = cur.fetchone()
        return {
            "postgres_version": version["version"] if version else None,
            "pgvector_version": pgvector["extversion"] if pgvector else None,
        }


if __name__ == "__main__":
    try:
        info = test_connection()
        print("Database connection successful!")
        print(f"PostgreSQL: {info['postgres_version']}")
        print(f"pgvector:   {info['pgvector_version']}")
    except Exception as e:
        print(f"Connection failed: {e}")