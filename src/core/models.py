"""Data models for FS Link Manager"""

import os
from typing import List


class LinkRecord:
    """Represents a single link record"""

    def __init__(self, id_: int, name: str, path: str, tags: str, position: int, added_at: str):
        self.id = id_
        self.name = name
        self.path = path
        self.tags = tags or ""
        self.position = position
        self.added_at = added_at

    def display_text(self) -> str:
        """Get display text for the link"""
        base = self.name if self.name else os.path.basename(self.path) or self.path
        tag_part = f"  [{self.tags}]" if self.tags else ""
        return f"{base}{tag_part}\n{self.path}"

    def get_tags_list(self) -> List[str]:
        """Get tags as a list"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]