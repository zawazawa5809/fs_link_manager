"""Database operations for FS Link Manager"""

import os
import sqlite3
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from .models import LinkRecord


class LinkDatabase:
    """Handles all database operations for links"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to data/ directory
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "links.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema"""
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                tags TEXT,
                position INTEGER NOT NULL,
                added_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def add_link(self, name: str, path: str, tags: str = "") -> int:
        """Add a new link to the database"""
        cur = self.conn.cursor()
        cur.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM links;")
        next_pos = cur.fetchone()[0]
        added_at = datetime.now().isoformat(timespec="seconds")
        cur.execute(
            "INSERT INTO links(name, path, tags, position, added_at) VALUES (?, ?, ?, ?, ?);",
            (name, path, tags, next_pos, added_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_link(self, id_: int, *, name: Optional[str] = None,
                   path: Optional[str] = None, tags: Optional[str] = None):
        """Update an existing link"""
        sets = []
        vals = []
        if name is not None:
            sets.append("name = ?")
            vals.append(name)
        if path is not None:
            sets.append("path = ?")
            vals.append(path)
        if tags is not None:
            sets.append("tags = ?")
            vals.append(tags)
        if not sets:
            return
        vals.append(id_)
        self.conn.execute(f"UPDATE links SET {', '.join(sets)} WHERE id = ?;", vals)
        self.conn.commit()

    def delete_link(self, id_: int):
        """Delete a link from the database"""
        self.conn.execute("DELETE FROM links WHERE id = ?;", (id_,))
        self.conn.commit()

    def list_links(self, search: str = "") -> List[LinkRecord]:
        """List all links, optionally filtered by search term"""
        search = (search or "").strip()
        if search:
            like = f"%{search}%"
            rows = self.conn.execute(
                "SELECT id, name, path, tags, position, added_at FROM links "
                "WHERE name LIKE ? OR path LIKE ? OR tags LIKE ? "
                "ORDER BY position ASC;",
                (like, like, like),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT id, name, path, tags, position, added_at FROM links ORDER BY position ASC;"
            ).fetchall()
        return [LinkRecord(*r) for r in rows]

    def reorder(self, ordered_ids: List[int]):
        """Reorder links by reassigning positions"""
        for pos, id_ in enumerate(ordered_ids):
            self.conn.execute("UPDATE links SET position = ? WHERE id = ?;", (pos, id_))
        self.conn.commit()

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()