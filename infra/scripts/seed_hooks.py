#!/usr/bin/env python3
"""
PublishOps — Seed Hooks Library
================================
Seeds hooks_library.json into the PostgreSQL hooks table.
Idempotent: skips hooks that already exist (matched by hook_id).

Usage:
    python infra/scripts/seed_hooks.py
    DATABASE_URL=postgresql://... python infra/scripts/seed_hooks.py
"""
import json
import os
import sys
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import execute_values, Json
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)


def get_database_url() -> str:
    """Resolve the database URL from environment."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        # Fallback to individual components
        user = os.environ.get("POSTGRES_USER", "publishops")
        password = os.environ.get("POSTGRES_PASSWORD", "changeme_in_production_2024!")
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = os.environ.get("POSTGRES_PORT", "5432")
        db = os.environ.get("POSTGRES_DB", "publishops")
        url = f"postgresql://{user}:{password}@{host}:{port}/{db}"

    # Normalize async driver URLs to sync for psycopg2
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("postgresql+psycopg2://", "postgresql://")
    return url


def load_hooks(data_path: Path) -> list[dict]:
    """Load hooks from JSON file."""
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("hooks", [])


def ensure_table(conn):
    """Create the hooks table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hooks (
                id              SERIAL PRIMARY KEY,
                hook_id         VARCHAR(50) UNIQUE NOT NULL,
                text            TEXT NOT NULL,
                hook_type       VARCHAR(50) NOT NULL,
                target_emotion  VARCHAR(50) NOT NULL,
                platform_affinity JSONB NOT NULL DEFAULT '{}',
                avg_score       FLOAT NOT NULL DEFAULT 0.0,
                usage_count     INTEGER NOT NULL DEFAULT 0,
                created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_hooks_hook_type ON hooks(hook_type);
            CREATE INDEX IF NOT EXISTS idx_hooks_target_emotion ON hooks(target_emotion);
            CREATE INDEX IF NOT EXISTS idx_hooks_avg_score ON hooks(avg_score DESC);
        """)
    conn.commit()


def seed_hooks(conn, hooks: list[dict]) -> tuple[int, int]:
    """Bulk insert hooks, skipping duplicates. Returns (inserted, skipped)."""
    inserted = 0
    skipped = 0

    with conn.cursor() as cur:
        for hook in hooks:
            try:
                cur.execute(
                    """
                    INSERT INTO hooks (hook_id, text, hook_type, target_emotion, platform_affinity, avg_score, usage_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (hook_id) DO NOTHING
                    RETURNING id
                    """,
                    (
                        hook["id"],
                        hook["text"],
                        hook["hook_type"],
                        hook["target_emotion"],
                        Json(hook.get("platform_affinity", {})),
                        hook.get("avg_score", 0.0),
                        hook.get("usage_count", 0),
                    ),
                )
                result = cur.fetchone()
                if result:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  WARNING: Failed to insert hook '{hook['id']}': {e}")
                conn.rollback()
                skipped += 1
                continue

    conn.commit()
    return inserted, skipped


def main():
    # Locate hooks file
    project_root = Path(__file__).resolve().parent.parent.parent
    hooks_path = project_root / "data" / "hooks_library.json"

    if not hooks_path.exists():
        print(f"ERROR: Hooks file not found at {hooks_path}")
        sys.exit(1)

    # Load hooks
    hooks = load_hooks(hooks_path)
    print(f"Loaded {len(hooks)} hooks from {hooks_path}")

    # Connect to database
    db_url = get_database_url()
    print(f"Connecting to database...")

    try:
        conn = psycopg2.connect(db_url)
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        sys.exit(1)

    try:
        # Ensure table exists
        ensure_table(conn)
        print("Hooks table ready")

        # Seed data
        inserted, skipped = seed_hooks(conn, hooks)
        print(f"Seeding complete: {inserted} inserted, {skipped} skipped (already exist)")
    finally:
        conn.close()

    print("Done!")


if __name__ == "__main__":
    main()
