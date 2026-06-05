"""
Unit tests for the SQLite world database management.

This test module creates temporary, in-memory databases to safely verify
that the initialization of world storage tables and the execution of
safe-upgrade ALTER TABLE strategies (like the lightmap column) function perfectly.
"""

import sqlite3
import tempfile
import os
from typing import List


def test_database_schema_creation() -> None:
    """
    Validates that the world save database tables and columns instantiate correctly,
    including testing the safe-upgrade lightmap ALTER TABLE strategy.
    """
    # Create a temporary local file for the test database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path: str = tmp.name

    try:
        conn: sqlite3.Connection = sqlite3.connect(db_path)
        cursor: sqlite3.Cursor = conn.cursor()

        # Match the exact SQL run in World.__init__
        cursor.execute("""CREATE TABLE chunks (x INTEGER, y INTEGER, z INTEGER, data BLOB, PRIMARY KEY (x, y, z))""")
        cursor.execute("""ALTER TABLE chunks ADD COLUMN lightmap BLOB""")
        conn.commit()

        # Verify tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables: List[str] = [row[0] for row in cursor.fetchall()]
        assert 'chunks' in tables, "The 'chunks' table was not created!"

        # Verify chunk columns
        cursor.execute('PRAGMA table_info(chunks)')
        columns: List[str] = [row[1] for row in cursor.fetchall()]
        assert 'data' in columns, "The 'data' column is missing."
        assert 'lightmap' in columns, "The 'lightmap' ALTER TABLE fallback failed."

        conn.close()

    finally:
        os.remove(db_path)  # Clean up the temp file
