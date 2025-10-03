"""Database operations for FS Link Manager"""

import sqlite3
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from contextlib import contextmanager

from .models import LinkRecord
from .query_builder import SearchQueryBuilder


class LinkDatabase:
    """Handles all database operations for links"""

    def __init__(self, db_path: Optional[str] = None, read_only: bool = False):
        if db_path is None:
            # Default to data/ directory
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "links.db")

        self.db_path = db_path
        self.read_only = read_only

        # 接続オプション
        uri = f"file:{db_path}?mode={'ro' if read_only else 'rwc'}"
        self.conn = sqlite3.connect(uri, uri=True, check_same_thread=False)

        if not read_only:
            # 書き込み可能な場合のみPRAGMA設定
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.execute("PRAGMA foreign_keys=ON;")
            # トランザクションタイムアウト設定
            self.conn.execute("PRAGMA busy_timeout=5000;")  # 5秒
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
        # クエリビルダーを使用して検索
        builder = SearchQueryBuilder()
        builder.simple_search(search)

        query, params = builder.build()
        rows = self.conn.execute(query, params).fetchall()
        return [LinkRecord(*r) for r in rows]

    def search_links(self, builder: SearchQueryBuilder) -> List[LinkRecord]:
        """クエリビルダーを使用した高度な検索"""
        query, params = builder.build()
        rows = self.conn.execute(query, params).fetchall()
        return [LinkRecord(*r) for r in rows]

    def reorder(self, ordered_ids: List[int]):
        """Reorder links by reassigning positions"""
        for pos, id_ in enumerate(ordered_ids):
            self.conn.execute("UPDATE links SET position = ? WHERE id = ?;", (pos, id_))
        self.conn.commit()

    @contextmanager
    def transaction(self):
        """トランザクション管理コンテキストマネージャー

        使用例:
            with db.transaction():
                db.add_link(...)
                db.update_link(...)
        """
        if self.read_only:
            raise RuntimeError("Cannot start transaction on read-only database")

        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()