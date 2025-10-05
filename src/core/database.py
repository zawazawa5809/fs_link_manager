"""Database operations for FS Link Manager"""

import sqlite3
from datetime import datetime
from typing import List, Optional, Generator, Any
from pathlib import Path
from contextlib import contextmanager

from .models import LinkRecord
from .query_builder import SearchQueryBuilder


class LinkDatabase:
    """Handles all database operations for links"""

    def __init__(self, db_path: Optional[str] = None, read_only: bool = False) -> None:
        """Initialize database connection.

        Args:
            db_path: Path to database file (defaults to data/links.db)
            read_only: Whether to open in read-only mode

        Raises:
            RuntimeError: If database initialization fails
        """
        if db_path is None:
            # Default to data/ directory
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "links.db")

        self.db_path = db_path
        self.read_only = read_only
        self.conn = None

        try:
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
        except sqlite3.Error as e:
            # エラー時に接続をクリーンアップ
            if self.conn:
                self.conn.close()
                self.conn = None
            raise RuntimeError(f"Database initialization failed: {e}") from e

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
                added_at TEXT NOT NULL,
                custom_icon TEXT
            );
            """
        )
        self.conn.commit()
        
        # マイグレーション: 既存テーブルにcustom_iconカラムを追加
        try:
            self.conn.execute("SELECT custom_icon FROM links LIMIT 1;")
        except sqlite3.OperationalError:
            # カラムが存在しない場合は追加
            self.conn.execute("ALTER TABLE links ADD COLUMN custom_icon TEXT;")
            self.conn.commit()

    def add_link(self, name: str, path: str, tags: str = "", custom_icon: str = "") -> int:
        """Add a new link to the database"""
        cur = self.conn.cursor()
        cur.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM links;")
        next_pos = cur.fetchone()[0]
        added_at = datetime.now().isoformat(timespec="seconds")
        cur.execute(
            "INSERT INTO links(name, path, tags, position, added_at, custom_icon) VALUES (?, ?, ?, ?, ?, ?);",
            (name, path, tags, next_pos, added_at, custom_icon),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_link(self, id_: int, *, name: Optional[str] = None,
                   path: Optional[str] = None, tags: Optional[str] = None,
                   custom_icon: Optional[str] = None):
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
        if custom_icon is not None:
            sets.append("custom_icon = ?")
            vals.append(custom_icon)
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

    def get_link_by_id(self, id_: int) -> Optional[LinkRecord]:
        """Get a single link by ID (optimized for O(1) access)"""
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT id, name, path, tags, position, added_at, custom_icon FROM links WHERE id = ?",
            (id_,)
        ).fetchone()
        return LinkRecord(*row) if row else None

    def reorder(self, ordered_ids: List[int]):
        """Reorder links by reassigning positions (with transaction)"""
        with self.transaction():
            for pos, id_ in enumerate(ordered_ids):
                self.conn.execute("UPDATE links SET position = ? WHERE id = ?;", (pos, id_))

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Transaction management context manager.

        Yields:
            Database connection for transaction operations

        Raises:
            RuntimeError: If database is read-only

        Example:
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

    def close(self) -> None:
        """Close database connection safely."""
        if self.conn:
            try:
                self.conn.close()
            except sqlite3.Error:
                pass  # Ignore errors during close
            finally:
                self.conn = None

    def __enter__(self) -> 'LinkDatabase':
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit with automatic cleanup."""
        self.close()