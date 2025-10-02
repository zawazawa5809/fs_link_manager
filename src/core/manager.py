"""Link management operations for FS Link Manager"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from .database import LinkDatabase
from .models import LinkRecord


class LinkManager:
    """High-level link management operations"""

    def __init__(self, db_path: Optional[str] = None):
        self.db = LinkDatabase(db_path)

    def import_links(self, file_path: str) -> int:
        """Import links from a JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, dict) or 'version' not in data:
            raise ValueError("Invalid import file format")

        links = data.get('links', [])
        count = 0

        for link in links:
            if 'path' in link:
                self.db.add_link(
                    name=link.get('name', ''),
                    path=link['path'],
                    tags=link.get('tags', '')
                )
                count += 1

        return count

    def export_links(self, file_path: str, links: Optional[List[LinkRecord]] = None):
        """Export links to a JSON file"""
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
        """Validate if a path exists"""
        return os.path.exists(path)

    def open_in_explorer(self, path: str):
        """Open a path in Windows Explorer"""
        if os.path.exists(path):
            if os.path.isfile(path):
                os.startfile(os.path.dirname(path))
                # Note: Can't select file directly in Python's os.startfile
            else:
                os.startfile(path)

    def close(self):
        """Close the database connection"""
        self.db.close()