"""Persistent memory — SQLite-backed session store and fact memory."""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional


class Memory:
    """SQLite-backed memory system."""
    
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
    
    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
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
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                situation TEXT NOT NULL,
                action_taken TEXT,
                outcome TEXT,
                lesson TEXT,
                applied BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        self._conn.commit()
    
    def save_message(self, session_id: str, role: str, content: str) -> int:
        """Save a message and return its ID."""
        cur = self._conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )
        self._conn.commit()
        
        msg_id = cur.lastrowid
        self._conn.execute(
            "INSERT INTO messages_fts (rowid, content) VALUES (?, ?)",
            (msg_id, content)
        )
        self._conn.commit()
        return msg_id
    
    def search_sessions(self, query: str, limit: int = 5) -> list:
        """Search past sessions using FTS5."""
        rows = self._conn.execute("""
            SELECT s.id, s.title, s.created_at, m.content,
                   snippet(messages_fts, 1, '<mark>', '</mark>', '...', 32) as snippet
            FROM messages_fts f
            JOIN messages m ON f.rowid = m.id
            JOIN sessions s ON m.session_id = s.id
            WHERE messages_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit)).fetchall()
        return [dict(r) for r in rows]
    
    def save_fact(self, key: str, value: str, category: str = "general") -> None:
        """Save a durable fact."""
        self._conn.execute("""
            INSERT INTO facts (key, value, category)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET 
                value = excluded.value,
                category = excluded.category,
                updated_at = datetime('now')
        """, (key, value, category))
        self._conn.commit()
    
    def get_facts(self, category: str = None) -> list:
        """Retrieve saved facts."""
        if category:
            rows = self._conn.execute(
                "SELECT * FROM facts WHERE category = ? ORDER BY updated_at DESC",
                (category,)
            )
        else:
            rows = self._conn.execute(
                "SELECT * FROM facts ORDER BY updated_at DESC"
            )
        return [dict(r) for r in rows.fetchall()]
    
    def save_experience(self, situation: str, action: str,
                        outcome: str, lesson: str) -> None:
        """Log an experience for self-improvement."""
        self._conn.execute("""
            INSERT INTO experiences (situation, action_taken, outcome, lesson)
            VALUES (?, ?, ?, ?)
        """, (situation, action, outcome, lesson))
        self._conn.commit()
    
    def get_lessons(self) -> list:
        """Get all learned lessons for self-improvement."""
        rows = self._conn.execute(
            "SELECT id, lesson, outcome FROM experiences WHERE applied = 0 ORDER BY created_at DESC"
        )
        return [dict(r) for r in rows.fetchall()]
    
    def mark_lesson_applied(self, lesson_id: int) -> None:
        """Mark a lesson as applied to the system prompt."""
        self._conn.execute(
            "UPDATE experiences SET applied = 1 WHERE id = ?",
            (lesson_id,)
        )
        self._conn.commit()
    
    def close(self) -> None:
        self._conn.close()
