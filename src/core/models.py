"""Data models for FS Link Manager"""

import os
from typing import List
from dataclasses import dataclass


@dataclass
class LinkRecord:
    """Represents a single link record.

    Attributes:
        id: Unique identifier for the link
        name: Display name of the link
        path: File system path to the linked resource
        tags: Comma-separated tag string
        position: Display order position
        added_at: ISO 8601 timestamp of creation
    """
    id: int
    name: str
    path: str
    tags: str
    position: int
    added_at: str

    def __post_init__(self):
        """Normalize tags to ensure consistency."""
        self.tags = self.tags or ""

    def display_text(self) -> str:
        """Get display text for the link.

        Returns:
            Formatted string with name/path and optional tags
        """
        base = self.name if self.name else os.path.basename(self.path) or self.path
        tag_part = f"  [{self.tags}]" if self.tags else ""
        return f"{base}{tag_part}\n{self.path}"

    def get_tags_list(self) -> List[str]:
        """Get tags as a list.

        Returns:
            List of individual tag strings (trimmed)
        """
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]