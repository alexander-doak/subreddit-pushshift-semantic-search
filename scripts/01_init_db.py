"""Initialize the reddit_vectors database schema."""

import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import database


def main():
    sql_file = config.SQL_DIR / "create_tables.sql"

    if not sql_file.exists():
        print(f"ERROR: SQL file not found at {sql_file}")
        sys.exit(1)

    sql = sql_file.read_text(encoding="utf-8")

    print("Running create_tables.sql ...")
    with database.get_cursor() as cur:
        cur.execute(sql)

    # Verify the table exists
    with database.get_cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'subreddits'
            ORDER BY ordinal_position;
        """)
        columns = cur.fetchall()

    if not columns:
        print("ERROR: Table 'subreddits' was not created.")
        sys.exit(1)

    print(f"Table 'subreddits' created with {len(columns)} columns:")
    for col in columns:
        print(f"  {col['column_name']:25s} {col['data_type']}")

    print("\nDatabase initialization complete.")


if __name__ == "__main__":
    main()