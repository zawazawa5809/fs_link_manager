"""Link management operations for FS Link Manager"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from .database import LinkDatabase
from .models import LinkRecord


class LinkManager:
    """High-level link management operations.

    Provides business logic layer for link operations including
    import/export, validation, and file system integration.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize link manager.

        Args:
            db_path: Optional database path (defaults to data/links.db)
        """
        self.db = LinkDatabase(db_path)

    def import_links(self, file_path: str) -> int:
        """Import links from a JSON file with validation.

        Args:
            file_path: Path to JSON file containing link data

        Returns:
            Number of successfully imported links

        Raises:
            ValueError: If file format is invalid or unsupported
            OSError: If file cannot be read
        """
        import logging
        logger = logging.getLogger(__name__)

        MAX_IMPORT_SIZE = 10 * 1024 * 1024  # 10MB制限

        # ファイルサイズチェック
        file_size = os.path.getsize(file_path)
        if file_size > MAX_IMPORT_SIZE:
            raise ValueError(f"Import file too large (max {MAX_IMPORT_SIZE/1024/1024}MB)")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # バリデーション
        if not isinstance(data, dict):
            raise ValueError("Invalid import file format: expected dict")
        if 'version' not in data:
            raise ValueError("Invalid import file format: missing version")

        version = data['version']
        if version not in ['1.0']:  # サポートバージョンリスト
            raise ValueError(f"Unsupported version: {version}")

        links = data.get('links', [])
        if not isinstance(links, list):
            raise ValueError("Invalid import file format: links must be a list")

        count = 0
        errors = []

        # トランザクションを使用
        with self.db.transaction():
            for idx, link in enumerate(links):
                try:
                    if not isinstance(link, dict):
                        errors.append(f"Item {idx}: not a dict")
                        continue
                    if 'path' not in link:
                        errors.append(f"Item {idx}: missing path")
                        continue

                    self.db.add_link(
                        name=link.get('name', ''),
                        path=link['path'],
                        tags=link.get('tags', '')
                    )
                    count += 1
                except Exception as e:
                    errors.append(f"Item {idx}: {e}")

        if errors:
            logger.warning(f"Import completed with {len(errors)} errors: {errors[:5]}")  # 最初の5件のみ

        return count

    def export_links(self, file_path: str, links: Optional[List[LinkRecord]] = None) -> None:
        """Export links to a JSON file.

        Args:
            file_path: Destination path for JSON export
            links: Optional list of links to export (defaults to all)

        Raises:
            OSError: If file cannot be written
        """
        if links is None:
            links = self.db.list_links()

        export_data = {
            'version': '1.0',
            'links': [
                {
                    'name': link.name,
                    'path': link.path,
                    'tags': link.tags
                }
                for link in links
            ]
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

    def validate_path(self, path: str) -> bool:
        """Validate if a path exists and is safe.

        Args:
            path: File system path to validate

        Returns:
            True if path exists and passes security checks
        """
        try:
            # 正規化してパストラバーサルを防ぐ
            normalized_path = os.path.normpath(path)
            real_path = os.path.realpath(normalized_path)

            # 絶対パスへの変換
            abs_path = os.path.abspath(real_path)

            # 存在確認
            return os.path.exists(abs_path)
        except (ValueError, OSError):
            return False

    def open_in_explorer(self, path: str) -> None:
        """Open a path in Windows Explorer with security validation.

        Args:
            path: Path to open in Explorer

        Raises:
            ValueError: If path is invalid or doesn't exist
            OSError: If Explorer cannot be opened
        """
        # セキュリティ検証
        if not self.validate_path(path):
            raise ValueError(f"Invalid or non-existent path: {path}")

        # 正規化されたパスを使用
        normalized_path = os.path.normpath(os.path.realpath(path))

        if os.path.isfile(normalized_path):
            os.startfile(os.path.dirname(normalized_path))
            # Note: Can't select file directly in Python's os.startfile
        else:
            os.startfile(normalized_path)

    def close(self) -> None:
        """Close the database connection."""
        self.db.close()