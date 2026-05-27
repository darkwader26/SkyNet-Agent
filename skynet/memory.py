"""Persistent memory — SQLite-backed with FTS5 search and experience storage."""

import sqlite3
import json
import os
import uuid
from datetime import datetime
from typing import Optional, List


class Memory:
    """Agent's long-term memory. Stores sessions, messages, facts, and experiences."""

    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT DEFAULT 'Untitled',
                model TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
            USING fts5(content, content=messages, content_rowid=id);

            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                importance INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                situation TEXT NOT NULL,
                action_taken TEXT,
                outcome TEXT,
                success INTEGER DEFAULT 0,
                lesson TEXT,
                lesson_quality INTEGER DEFAULT 0,
                applied INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS cron_jobs (
                id TEXT PRIMARY KEY,
                name TEXT,
                schedule TEXT NOT NULL,
                prompt TEXT,
                last_run TEXT,
                next_run TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        self._conn.commit()

    # ── Sessions ────────────────────────────────────────────────────────

    def create_session(self, session_id: str = None, model: str = None) -> str:
        sid = session_id or str(uuid.uuid4())[:12]
        self._conn.execute(
            "INSERT OR IGNORE INTO sessions (id, model) VALUES (?, ?)",
            (sid, model),
        )
        self._conn.commit()
        return sid

    def save_message(self, session_id: str, role: str, content: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        self._conn.commit()
        msg_id = cur.lastrowid
        self._conn.execute(
            "INSERT INTO messages_fts (rowid, content) VALUES (?, ?)",
            (msg_id, content),
        )
        self._conn.commit()
        self._conn.execute(
            "UPDATE sessions SET updated_at = datetime('now') WHERE id = ?",
            (session_id,),
        )
        self._conn.commit()
        return msg_id

    def get_session(self, session_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_history(self, session_id: str, limit: int = 100) -> List[dict]:
        rows = self._conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_sessions(self, limit: int = 10) -> List[dict]:
        rows = self._conn.execute(
            "SELECT id, title, model, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def search_sessions(self, query: str, limit: int = 5) -> List[dict]:
        rows = self._conn.execute(
            """SELECT s.id, s.title, s.created_at, m.content,
                      snippet(messages_fts, 1, '<mark>', '</mark>', '...', 32) as snippet
               FROM messages_fts f
               JOIN messages m ON f.rowid = m.id
               JOIN sessions s ON m.session_id = s.id
               WHERE messages_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (query, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_session_title(self, session_id: str, title: str) -> None:
        self._conn.execute(
            "UPDATE sessions SET title = ?, updated_at = datetime('now') WHERE id = ?",
            (title, session_id),
        )
        self._conn.commit()

    # ── Facts ───────────────────────────────────────────────────────────

    def save_fact(self, key: str, value: str, category: str = "general",
                  importance: int = 1) -> None:
        self._conn.execute(
            """INSERT INTO facts (key, value, category, importance)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET
                   value = excluded.value,
                   category = excluded.category,
                   importance = excluded.importance,
                   updated_at = datetime('now')""",
            (key, value, category, importance),
        )
        self._conn.commit()

    def get_facts(self, category: str = None) -> List[dict]:
        if category:
            rows = self._conn.execute(
                "SELECT * FROM facts WHERE category = ? ORDER BY importance DESC, updated_at DESC",
                (category,),
            )
        else:
            rows = self._conn.execute(
                "SELECT * FROM facts ORDER BY importance DESC, updated_at DESC"
            )
        return [dict(r) for r in rows.fetchall()]

    def delete_fact(self, key: str) -> None:
        self._conn.execute("DELETE FROM facts WHERE key = ?", (key,))
        self._conn.commit()

    # ── Experiences & Self-Improvement ──────────────────────────────────

    def save_experience(self, situation: str, action: str, outcome: str,
                        success: bool, session_id: str = None,
                        lesson: str = None) -> int:
        cur = self._conn.execute(
            """INSERT INTO experiences (session_id, situation, action_taken,
               outcome, success, lesson)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, situation, action, outcome, int(success), lesson),
        )
        self._conn.commit()
        return cur.lastrowid

    def update_experience(self, exp_id: int, lesson: str, quality: int = 1) -> None:
        self._conn.execute(
            "UPDATE experiences SET lesson = ?, lesson_quality = ? WHERE id = ?",
            (lesson, quality, exp_id),
        )
        self._conn.commit()

    def get_pending_lessons(self) -> List[dict]:
        rows = self._conn.execute(
            """SELECT id, situation, action_taken, outcome, lesson, lesson_quality
               FROM experiences
               WHERE applied = 0 AND lesson IS NOT NULL AND lesson != ''
               ORDER BY lesson_quality DESC, created_at DESC
               LIMIT 20""",
        ).fetchall()
        return [dict(r) for r in rows]

    def get_failed_experiences(self, limit: int = 10) -> List[dict]:
        rows = self._conn.execute(
            """SELECT id, situation, action_taken, outcome
               FROM experiences
               WHERE success = 0 AND (lesson IS NULL OR lesson = '')
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_lesson_applied(self, exp_id: int) -> None:
        self._conn.execute(
            "UPDATE experiences SET applied = 1 WHERE id = ?", (exp_id,)
        )
        self._conn.commit()

    # ── Cron ────────────────────────────────────────────────────────────

    def save_cron(self, job_id: str, name: str, schedule: str,
                  prompt: str, next_run: str) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO cron_jobs
               (id, name, schedule, prompt, next_run)
               VALUES (?, ?, ?, ?, ?)""",
            (job_id, name, schedule, prompt, next_run),
        )
        self._conn.commit()

    def get_due_cron(self) -> List[dict]:
        rows = self._conn.execute(
            "SELECT * FROM cron_jobs WHERE enabled = 1 AND next_run <= datetime('now')",
        ).fetchall()
        return [dict(r) for r in rows]

    def update_cron_run(self, job_id: str, last_run: str, next_run: str) -> None:
        self._conn.execute(
            "UPDATE cron_jobs SET last_run = ?, next_run = ? WHERE id = ?",
            (last_run, next_run, job_id),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
