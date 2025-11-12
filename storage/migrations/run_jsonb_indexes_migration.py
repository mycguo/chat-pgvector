#!/usr/bin/env python3
"""
Run migration to add JSONB path indexes for structured queries.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storage.pg_connection import get_connection


def run_migration():
    """Run the JSONB indexes migration."""
    migration_file = Path(__file__).parent / "002_add_jsonb_indexes.sql"
    
    if not migration_file.exists():
        print(f"Error: Migration file not found: {migration_file}")
        return False
    
    print("Running JSONB indexes migration...")
    print(f"Reading migration from: {migration_file}")
    
    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(migration_sql)
            conn.commit()
        
        print("✅ Successfully added JSONB indexes!")
        return True
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)

