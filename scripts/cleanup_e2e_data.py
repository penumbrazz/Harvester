"""Remove E2E test data from the Harvester database.

Deletes all sources, recipes, schedules, and audit events whose names
start with 'e2e-'. Also removes orphaned foreign-key rows that reference
the deleted entities.

Usage:
    uv run scripts/cleanup_e2e_data.py [--dry-run]
"""

import argparse
import os
import sys

import sqlalchemy as sa
from sqlalchemy import create_engine, text


def _get_db_url() -> str:
    url = os.environ.get("HARVESTER_DATABASE_URL", "")
    if not url:
        url = "postgresql+psycopg://postgres:postgres123@192.168.0.114:5432/harvester"
    # Ensure we point at the harvester database, not the admin postgres db.
    if url.endswith("/postgres"):
        url = url.rsplit("/", 1)[0] + "/harvester"
    return url


def _delete(conn, table: str, name_col: str, dry_run: bool) -> int:
    """Delete rows from *table* where *name_col* LIKE 'e2e-%'."""
    count_sql = f"SELECT count(*) FROM {table} WHERE {name_col} LIKE 'e2e-%'"
    count = conn.execute(text(count_sql)).scalar()
    if count == 0:
        print(f"  {table}: no e2e data found")
        return 0
    if dry_run:
        print(f"  {table}: would delete {count} rows (dry run)")
        return count
    conn.execute(text(f"DELETE FROM {table} WHERE {name_col} LIKE 'e2e-%'"))
    print(f"  {table}: deleted {count} rows")
    return count


def cleanup(dry_run: bool = False) -> None:
    url = _get_db_url()
    engine = create_engine(url)
    total = 0

    with engine.begin() as conn:
        print(f"Cleaning e2e test data from {url.split('@')[-1]} ...")

        # Delete in dependency order: schedules first (FK to sources & recipes),
        # then recipes, then audit_events, then sources.
        tables = [
            ("watch_schedules", "id"),  # no name column; delete by source FK
        ]

        # Schedules linked to e2e sources.
        count_sql = (
            "SELECT count(*) FROM watch_schedules ws "
            "JOIN sources s ON ws.source_id = s.id "
            "WHERE s.name LIKE 'e2e-%'"
        )
        count = conn.execute(text(count_sql)).scalar()
        if count > 0:
            if dry_run:
                print(f"  watch_schedules: would delete {count} rows (dry run)")
            else:
                conn.execute(
                    text(
                        "DELETE FROM watch_schedules WHERE source_id IN "
                        "(SELECT id FROM sources WHERE name LIKE 'e2e-%')"
                    )
                )
                print(f"  watch_schedules: deleted {count} rows")
            total += count
        else:
            print("  watch_schedules: no e2e data found")

        # Audit events for e2e entities.
        count_sql = (
            "SELECT count(*) FROM audit_events WHERE entity_id IN "
            "(SELECT id FROM sources WHERE name LIKE 'e2e-%') "
            "OR entity_id IN (SELECT id FROM recipes WHERE name LIKE 'e2e-%')"
        )
        count = conn.execute(text(count_sql)).scalar()
        if count > 0:
            if dry_run:
                print(f"  audit_events: would delete {count} rows (dry run)")
            else:
                conn.execute(
                    text(
                        "DELETE FROM audit_events WHERE entity_id IN "
                        "(SELECT id FROM sources WHERE name LIKE 'e2e-%') "
                        "OR entity_id IN "
                        "(SELECT id FROM recipes WHERE name LIKE 'e2e-%')"
                    )
                )
                print(f"  audit_events: deleted {count} rows")
            total += count
        else:
            print("  audit_events: no e2e data found")

        # Jobs linked to e2e sources (jobs.source_id is varchar, needs cast).
        count_sql = (
            "SELECT count(*) FROM jobs WHERE source_id::uuid IN "
            "(SELECT id FROM sources WHERE name LIKE 'e2e-%')"
        )
        count = conn.execute(text(count_sql)).scalar()
        if count > 0:
            if dry_run:
                print(f"  jobs: would delete {count} rows (dry run)")
            else:
                conn.execute(
                    text(
                        "DELETE FROM jobs WHERE source_id::uuid IN "
                        "(SELECT id FROM sources WHERE name LIKE 'e2e-%')"
                    )
                )
                print(f"  jobs: deleted {count} rows")
            total += count
        else:
            print("  jobs: no e2e data found")

        # Recipes.
        total += _delete(conn, "recipes", "name", dry_run)

        # Source frontiers.
        count_sql = (
            "SELECT count(*) FROM source_frontiers WHERE source_id IN "
            "(SELECT id FROM sources WHERE name LIKE 'e2e-%')"
        )
        count = conn.execute(text(count_sql)).scalar()
        if count > 0:
            if dry_run:
                print(f"  source_frontiers: would delete {count} rows (dry run)")
            else:
                conn.execute(
                    text(
                        "DELETE FROM source_frontiers WHERE source_id IN "
                        "(SELECT id FROM sources WHERE name LIKE 'e2e-%')"
                    )
                )
                print(f"  source_frontiers: deleted {count} rows")
            total += count
        else:
            print("  source_frontiers: no e2e data found")

        # Sources.
        total += _delete(conn, "sources", "name", dry_run)

    engine.dispose()

    action = "would delete" if dry_run else "deleted"
    print(f"\nTotal: {action} {total} rows")
    if dry_run:
        print("(dry run — no changes made)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove E2E test data")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be deleted"
    )
    args = parser.parse_args()
    cleanup(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
