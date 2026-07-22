from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional


def sqlite_path(database_url: str) -> Path:
    if database_url.startswith("sqlite:///"):
        return Path(database_url.replace("sqlite:///", "", 1))
    return Path("data/recommendations.db")


class Database:
    def __init__(self, database_url: str):
        self.path = sqlite_path(database_url)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row

    def migrate(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS feedback (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              url TEXT NOT NULL,
              normalized_url TEXT NOT NULL,
              action TEXT NOT NULL,
              category TEXT,
              score_delta REAL NOT NULL DEFAULT 0,
              observed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS saved_candidates (
              normalized_url TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              source TEXT NOT NULL,
              score INTEGER NOT NULL,
              category TEXT NOT NULL,
              saved_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS daily_runs (
              run_date TEXT PRIMARY KEY,
              candidates INTEGER NOT NULL,
              duplicates INTEGER NOT NULL,
              evaluated INTEGER NOT NULL,
              saved INTEGER NOT NULL,
              report_path TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS favorites (
              item_id TEXT PRIMARY KEY,
              normalized_url TEXT NOT NULL,
              title TEXT NOT NULL,
              favorited_at TEXT NOT NULL,
              category TEXT NOT NULL,
              score INTEGER NOT NULL,
              daily_page TEXT NOT NULL,
              discord_status TEXT NOT NULL DEFAULT 'pending',
              discord_message_id TEXT,
              dedupe_key TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS discord_notifications (
              notification_key TEXT PRIMARY KEY,
              run_date TEXT NOT NULL,
              message_id TEXT,
              status TEXT NOT NULL,
              posted_at TEXT NOT NULL,
              page_url TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def execute(self, sql: str, params: Iterable = ()):
        cur = self.conn.execute(sql, tuple(params))
        self.conn.commit()
        return cur

    def query(self, sql: str, params: Iterable = ()):
        return list(self.conn.execute(sql, tuple(params)))

    def close(self) -> None:
        self.conn.close()
