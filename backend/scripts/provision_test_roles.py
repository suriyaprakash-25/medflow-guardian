"""Provision the Supabase-compatible browser roles used by integration tests."""

from __future__ import annotations

import os

import psycopg2


def main() -> int:
    database_url = os.environ["DATABASE_URL"]
    connection = psycopg2.connect(database_url)
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'anon') "
            "THEN CREATE ROLE anon NOLOGIN; END IF; END $$;"
        )
        cursor.execute(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticated') "
            "THEN CREATE ROLE authenticated NOLOGIN; END IF; END $$;"
        )
        cursor.execute("GRANT USAGE ON SCHEMA public TO anon, authenticated")
        cursor.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO anon, authenticated"
        )
        cursor.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT USAGE, SELECT ON SEQUENCES TO anon, authenticated"
        )
    connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
