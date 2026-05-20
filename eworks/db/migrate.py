"""Minimal migration runner for Eworks OS.

Discovers all migration files in eworks/db/migrations/ matching the pattern
NNN_*.py, tracks which ones have been applied in a `schema_migrations` table,
and runs any that are pending — in numeric order.

Usage:
    python eworks/db/migrate.py             # run all pending migrations
    python eworks/db/migrate.py --rollback 004   # roll back a specific migration
"""
from __future__ import annotations

import importlib.util
import os
import sqlite3
import sys
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).parent / "migrations"
DEFAULT_DB_PATH = os.environ.get("DB_PATH", "data/eworks.db")


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT UNIQUE NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )"""
    )
    conn.commit()


def _applied_versions(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {r[0] for r in rows}


def _mark_applied(conn: sqlite3.Connection, version: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)", (version,)
    )
    conn.commit()


def _mark_rolled_back(conn: sqlite3.Connection, version: str) -> None:
    conn.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
    conn.commit()


def _load_migration(path: Path):
    """Dynamically load a migration module from its file path."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _discover_migrations() -> list[tuple[str, Path]]:
    """Return (version, path) pairs sorted numerically."""
    files = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.py"))
    return [(f.stem.split("_")[0], f) for f in files]


def run_pending(db_path: str = DEFAULT_DB_PATH) -> None:
    """Apply all migrations not yet recorded in schema_migrations."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    _ensure_migrations_table(conn)
    applied = _applied_versions(conn)

    pending = [
        (ver, path)
        for ver, path in _discover_migrations()
        if ver not in applied
    ]

    if not pending:
        print("No pending migrations.")
        return

    for ver, path in pending:
        print(f"Applying migration {ver} ({path.name}) …")
        mod = _load_migration(path)
        mod.up(conn)
        _mark_applied(conn, ver)
        print(f"  ✓ {ver} done")

    conn.close()


def rollback(version: str, db_path: str = DEFAULT_DB_PATH) -> None:
    """Roll back a specific migration by version string (e.g. '004')."""
    conn = sqlite3.connect(db_path)
    _ensure_migrations_table(conn)
    applied = _applied_versions(conn)

    if version not in applied:
        print(f"Migration {version} is not currently applied — nothing to roll back.")
        conn.close()
        return

    matches = [
        (ver, path)
        for ver, path in _discover_migrations()
        if ver == version
    ]
    if not matches:
        print(f"No migration file found for version {version}.")
        conn.close()
        return

    _, path = matches[0]
    print(f"Rolling back migration {version} ({path.name}) …")
    mod = _load_migration(path)
    mod.down(conn)
    _mark_rolled_back(conn, version)
    print(f"  ✓ {version} rolled back")
    conn.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--rollback" in args:
        idx = args.index("--rollback")
        try:
            ver = args[idx + 1]
        except IndexError:
            print("Usage: migrate.py --rollback <version>")
            sys.exit(1)
        rollback(ver)
    else:
        run_pending()
