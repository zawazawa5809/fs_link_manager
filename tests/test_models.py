"""Unit tests for LinkRecord class"""

import unittest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.models import LinkRecord


class TestLinkRecord(unittest.TestCase):

    def test_initialization(self):
        """Test LinkRecord initialization with all parameters"""
        record = LinkRecord(
            id_=1,
            name="Test File",
            path="C:\\test\\file.txt",
            tags="tag1,tag2",
            position=0,
            added_at="2025-01-19T10:00:00"
        )

        self.assertEqual(record.id, 1)
        self.assertEqual(record.name, "Test File")
        self.assertEqual(record.path, "C:\\test\\file.txt")
        self.assertEqual(record.tags, "tag1,tag2")
        self.assertEqual(record.position, 0)
        self.assertEqual(record.added_at, "2025-01-19T10:00:00")

    def test_initialization_with_none_tags(self):
        """Test LinkRecord initialization with None tags"""
        record = LinkRecord(
            id_=1,
            name="Test",
            path="C:\\test",
            tags=None,
            position=0,
            added_at="2025-01-19T10:00:00"
        )

        self.assertEqual(record.tags, "")

    def test_display_text_with_name_and_tags(self):
        """Test display_text with name and tags"""
        record = LinkRecord(
            id_=1,
            name="My Document",
            path="C:\\documents\\file.docx",
            tags="work,important",
            position=0,
            added_at="2025-01-19T10:00:00"
        )

        expected = "My Document  [work,important]\nC:\\documents\\file.docx"
        self.assertEqual(record.display_text(), expected)

    def test_display_text_without_name(self):
        """Test display_text without name (uses basename of path)"""
        record = LinkRecord(
            id_=1,
            name="",
            path="C:\\documents\\file.docx",
            tags="",
            position=0,
            added_at="2025-01-19T10:00:00"
        )

        expected = "file.docx\nC:\\documents\\file.docx"
        self.assertEqual(record.display_text(), expected)

    def test_display_text_without_tags(self):
        """Test display_text without tags"""
        record = LinkRecord(
            id_=1,
            name="My File",
            path="C:\\test\\file.txt",
            tags="",
            position=0,
            added_at="2025-01-19T10:00:00"
        )

        expected = "My File\nC:\\test\\file.txt"
        self.assertEqual(record.display_text(), expected)

    def test_display_text_with_root_path(self):
        """Test display_text with root path (no basename)"""
        record = LinkRecord(
            id_=1,
            name="",
            path="C:\\",
            tags="",
            position=0,
            added_at="2025-01-19T10:00:00"
        )

        expected = "C:\\\nC:\\"
        self.assertEqual(record.display_text(), expected)

    def test_display_text_with_unc_path(self):
        """Test display_text with UNC path"""
        record = LinkRecord(
            id_=1,
            name="Network Share",
            path="\\\\server\\share\\folder",
            tags="network",
            position=0,
            added_at="2025-01-19T10:00:00"
        )

        expected = "Network Share  [network]\n\\\\server\\share\\folder"
        self.assertEqual(record.display_text(), expected)

    def test_display_text_with_unicode(self):
        """Test display_text with Unicode characters"""
        record = LinkRecord(
            id_=1,
            name="日本語ファイル",
            path="C:\\ドキュメント\\ファイル.txt",
            tags="日本語,テスト",
            position=0,
            added_at="2025-01-19T10:00:00"
        )

        expected = "日本語ファイル  [日本語,テスト]\nC:\\ドキュメント\\ファイル.txt"
        self.assertEqual(record.display_text(), expected)

    def test_display_text_with_emoji(self):
        """Test display_text with emoji"""
        record = LinkRecord(
            id_=1,
            name="Important File 🔥",
            path="C:\\files\\important.txt",
            tags="urgent,🚨",
            position=0,
            added_at="2025-01-19T10:00:00"
        )

        expected = "Important File 🔥  [urgent,🚨]\nC:\\files\\important.txt"
        self.assertEqual(record.display_text(), expected)

    def test_display_text_with_special_characters(self):
        """Test display_text with special characters"""
        record = LinkRecord(
            id_=1,
            name='File with "quotes" and & symbols',
            path="C:\\path with spaces\\file's name.txt",
            tags="tag,with,commas",
            position=0,
            added_at="2025-01-19T10:00:00"
        )

        expected = 'File with "quotes" and & symbols  [tag,with,commas]\nC:\\path with spaces\\file\'s name.txt'
        self.assertEqual(record.display_text(), expected)

    def test_display_text_with_long_name(self):
        """Test display_text with very long name"""
        long_name = "A" * 200
        record = LinkRecord(
            id_=1,
            name=long_name,
            path="C:\\test\\file.txt",
            tags="long",
            position=0,
            added_at="2025-01-19T10:00:00"
        )

        expected = f"{long_name}  [long]\nC:\\test\\file.txt"
        self.assertEqual(record.display_text(), expected)

    def test_display_text_empty_name_and_path_only_drive(self):
        """Test display_text when name is empty and path is only a drive letter"""
        record = LinkRecord(
            id_=1,
            name="",
            path="D:",
            tags="",
            position=0,
            added_at="2025-01-19T10:00:00"
        )

        # When basename is empty, it falls back to the path itself
        expected = "D:\nD:"
        self.assertEqual(record.display_text(), expected)


if __name__ == '__main__':
    unittest.main()