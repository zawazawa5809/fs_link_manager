"""Unit tests for LinkDatabase class"""

import unittest
import tempfile
import os
import sqlite3
from datetime import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fs_link_manager import LinkDatabase, LinkRecord


class TestLinkDatabase(unittest.TestCase):

    def setUp(self):
        """Create a temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db = LinkDatabase(self.temp_db.name)

    def tearDown(self):
        """Clean up temporary database"""
        if hasattr(self, 'db') and self.db.conn:
            self.db.conn.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
        # Clean up WAL files if they exist
        wal_file = self.temp_db.name + '-wal'
        shm_file = self.temp_db.name + '-shm'
        if os.path.exists(wal_file):
            os.unlink(wal_file)
        if os.path.exists(shm_file):
            os.unlink(shm_file)

    def test_database_initialization(self):
        """Test that database is properly initialized with schema"""
        # Check that the database file exists
        self.assertTrue(os.path.exists(self.temp_db.name))

        # Check that the links table exists
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='links'")
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'links')

    def test_add_link(self):
        """Test adding a new link to the database"""
        name = "Test Link"
        path = "C:\\test\\path"
        tags = "test,sample"

        link_id = self.db.add_link(name, path, tags)

        # Verify the link was added
        self.assertIsNotNone(link_id)
        self.assertIsInstance(link_id, int)

        # Check the database directly
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM links WHERE id = ?", (link_id,))
        row = cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[1], name)  # name
        self.assertEqual(row[2], path)  # path
        self.assertEqual(row[3], tags)  # tags
        self.assertEqual(row[4], 0)     # position (first item)

    def test_add_multiple_links_position(self):
        """Test that multiple links get correct positions"""
        links = [
            ("Link 1", "path1", "tag1"),
            ("Link 2", "path2", "tag2"),
            ("Link 3", "path3", "tag3")
        ]

        ids = []
        for name, path, tags in links:
            link_id = self.db.add_link(name, path, tags)
            ids.append(link_id)

        # Check positions
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, position FROM links ORDER BY position")
        rows = cursor.fetchall()

        self.assertEqual(len(rows), 3)
        for i, row in enumerate(rows):
            self.assertEqual(row[1], i)  # position should be 0, 1, 2

    def test_update_link(self):
        """Test updating link properties"""
        # Add a link
        link_id = self.db.add_link("Original", "C:\\original", "old")

        # Update name only
        self.db.update_link(link_id, name="Updated Name")

        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name, path, tags FROM links WHERE id = ?", (link_id,))
        row = cursor.fetchone()
        self.assertEqual(row[0], "Updated Name")
        self.assertEqual(row[1], "C:\\original")
        self.assertEqual(row[2], "old")

        # Update path only
        self.db.update_link(link_id, path="C:\\new\\path")

        cursor.execute("SELECT name, path, tags FROM links WHERE id = ?", (link_id,))
        row = cursor.fetchone()
        self.assertEqual(row[0], "Updated Name")
        self.assertEqual(row[1], "C:\\new\\path")
        self.assertEqual(row[2], "old")

        # Update tags only
        self.db.update_link(link_id, tags="new,tags")

        cursor.execute("SELECT name, path, tags FROM links WHERE id = ?", (link_id,))
        row = cursor.fetchone()
        self.assertEqual(row[0], "Updated Name")
        self.assertEqual(row[1], "C:\\new\\path")
        self.assertEqual(row[2], "new,tags")

        # Update multiple fields
        self.db.update_link(link_id, name="Final", path="C:\\final", tags="final")

        cursor.execute("SELECT name, path, tags FROM links WHERE id = ?", (link_id,))
        row = cursor.fetchone()
        self.assertEqual(row[0], "Final")
        self.assertEqual(row[1], "C:\\final")
        self.assertEqual(row[2], "final")

    def test_delete_link(self):
        """Test deleting a link"""
        # Add links
        id1 = self.db.add_link("Link 1", "path1", "")
        id2 = self.db.add_link("Link 2", "path2", "")
        id3 = self.db.add_link("Link 3", "path3", "")

        # Delete the middle one
        self.db.delete_link(id2)

        # Verify it's deleted
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM links")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)

        cursor.execute("SELECT id FROM links ORDER BY position")
        remaining_ids = [row[0] for row in cursor.fetchall()]
        self.assertEqual(remaining_ids, [id1, id3])

    def test_list_links_no_search(self):
        """Test listing all links without search filter"""
        # Add some links
        links_data = [
            ("File 1", "C:\\file1.txt", "doc"),
            ("File 2", "C:\\file2.txt", "image"),
            ("File 3", "C:\\file3.txt", "doc,important")
        ]

        for name, path, tags in links_data:
            self.db.add_link(name, path, tags)

        # List all links
        links = self.db.list_links()

        self.assertEqual(len(links), 3)
        for i, link in enumerate(links):
            self.assertIsInstance(link, LinkRecord)
            self.assertEqual(link.name, links_data[i][0])
            self.assertEqual(link.path, links_data[i][1])
            self.assertEqual(link.tags, links_data[i][2])
            self.assertEqual(link.position, i)

    def test_list_links_with_search(self):
        """Test listing links with search filter"""
        # Add some links
        self.db.add_link("Document 1", "C:\\docs\\file1.txt", "work")
        self.db.add_link("Image 1", "C:\\images\\pic1.jpg", "personal")
        self.db.add_link("Document 2", "C:\\docs\\file2.txt", "work,important")
        self.db.add_link("Spreadsheet", "C:\\data\\sheet.xlsx", "work")

        # Search by name
        links = self.db.list_links("Document")
        self.assertEqual(len(links), 2)
        for link in links:
            self.assertIn("Document", link.name)

        # Search by path
        links = self.db.list_links("docs")
        self.assertEqual(len(links), 2)
        for link in links:
            self.assertIn("docs", link.path)

        # Search by tag
        links = self.db.list_links("work")
        self.assertEqual(len(links), 3)
        for link in links:
            self.assertIn("work", link.tags)

        # Search by partial match
        links = self.db.list_links("file")
        self.assertEqual(len(links), 2)

    def test_reorder(self):
        """Test reordering links"""
        # Add links
        id1 = self.db.add_link("Link 1", "path1", "")
        id2 = self.db.add_link("Link 2", "path2", "")
        id3 = self.db.add_link("Link 3", "path3", "")

        # Reorder them
        new_order = [id3, id1, id2]
        self.db.reorder(new_order)

        # Verify the new order
        links = self.db.list_links()
        self.assertEqual(len(links), 3)
        self.assertEqual(links[0].id, id3)
        self.assertEqual(links[0].position, 0)
        self.assertEqual(links[1].id, id1)
        self.assertEqual(links[1].position, 1)
        self.assertEqual(links[2].id, id2)
        self.assertEqual(links[2].position, 2)

    def test_empty_database(self):
        """Test operations on empty database"""
        # List links from empty database
        links = self.db.list_links()
        self.assertEqual(len(links), 0)

        # Search in empty database
        links = self.db.list_links("search")
        self.assertEqual(len(links), 0)

        # Delete non-existent link (should not raise error)
        self.db.delete_link(999)

        # Update non-existent link (should not raise error)
        self.db.update_link(999, name="Test")

    def test_special_characters(self):
        """Test handling of special characters in data"""
        special_cases = [
            ("File's Name", "C:\\path with spaces\\file.txt", "tag,with,commas"),
            ('Name with "quotes"', "C:\\path\\file.txt", "tag with spaces"),
            ("日本語", "C:\\パス\\ファイル.txt", "タグ"),
            ("Emoji 😀", "C:\\emoji\\path", "emoji,😀")
        ]

        ids = []
        for name, path, tags in special_cases:
            link_id = self.db.add_link(name, path, tags)
            ids.append(link_id)

        links = self.db.list_links()
        self.assertEqual(len(links), len(special_cases))

        for i, link in enumerate(links):
            self.assertEqual(link.name, special_cases[i][0])
            self.assertEqual(link.path, special_cases[i][1])
            self.assertEqual(link.tags, special_cases[i][2])


if __name__ == '__main__':
    unittest.main()