#!/usr/bin/env python3
"""
PublishOps — Seed Platform Rules
==================================
Seeds platform_rules.json into the PostgreSQL platform_rules table.
Idempotent: updates rules if they already exist (upsert by platform_id).

Usage:
    python infra/scripts/seed_platform_rules.py
    DATABASE_URL=postgresql://... python infra/scripts/seed_platform_rules.py
"""
import json
import os
import sys
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import Json
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)


def get_database_url() -> str:
    """Resolve the database URL from environment."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        user = os.environ.get("POSTGRES_USER", "publishops")
        password = os.environ.get("POSTGRES_PASSWORD", "changeme_in_production_2024!")
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = os.environ.get("POSTGRES_PORT", "5432")
        db = os.environ.get("POSTGRES_DB", "publishops")
        url = f"postgresql://{user}:{password}@{host}:{port}/{db}"

    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("postgresql+psycopg2://", "postgresql://")
    return url


def load_platform_rules(data_path: Path) -> dict:
    """Load platform rules from JSON file."""
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("platforms", {})


def ensure_table(conn):
    """Create the platform_rules table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS platform_rules (
                id                  SERIAL PRIMARY KEY,
                platform_id         VARCHAR(50) UNIQUE NOT NULL,
                display_name        VARCHAR(100) NOT NULL,
                content_types       JSONB NOT NULL DEFAULT '[]',
                algorithm_signals   JSONB NOT NULL DEFAULT '[]',
                posting_rules       JSONB NOT NULL DEFAULT '{}',
                created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_platform_rules_platform_id ON platform_rules(platform_id);
        """)
    conn.commit()


def seed_platform_rules(conn, platforms: dict) -> tuple[int, int]:
    """Upsert platform rules. Returns (inserted, updated)."""
    inserted = 0
    updated = 0

    with conn.cursor() as cur:
        for platform_id, platform_data in platforms.items():
            try:
                cur.execute(
                    """
                    INSERT INTO platform_rules (
                        platform_id, display_name, content_types,
                        algorithm_signals, posting_rules, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (platform_id) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        content_types = EXCLUDED.content_types,
                        algorithm_signals = EXCLUDED.algorithm_signals,
                        posting_rules = EXCLUDED.posting_rules,
                        updated_at = NOW()
                    RETURNING (xmax = 0) AS is_insert
                    """,
                    (
                        platform_id,
                        platform_data.get("display_name", platform_id),
                        Json(platform_data.get("content_types", [])),
                        Json(platform_data.get("algorithm_signals", [])),
                        Json(platform_data.get("posting_rules", {})),
                    ),
                )
                result = cur.fetchone()
                if result and result[0]:
                    inserted += 1
                else:
                    updated += 1
            except Exception as e:
                print(f"  WARNING: Failed to upsert platform '{platform_id}': {e}")
                conn.rollback()
                continue

    conn.commit()
    return inserted, updated


def main():
    # Locate platform rules file
    project_root = Path(__file__).resolve().parent.parent.parent
    rules_path = project_root / "data" / "platform_rules.json"

    if not rules_path.exists():
        print(f"ERROR: Platform rules file not found at {rules_path}")
        sys.exit(1)

    # Load rules
    platforms = load_platform_rules(rules_path)
    print(f"Loaded rules for {len(platforms)} platforms from {rules_path}")

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
        print("Platform rules table ready")

        # Seed data
        inserted, updated = seed_platform_rules(conn, platforms)
        print(f"Seeding complete: {inserted} inserted, {updated} updated")
    finally:
        conn.close()

    print("Done!")


if __name__ == "__main__":
    main()
