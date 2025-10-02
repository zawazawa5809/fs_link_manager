"""Integration tests for import/export functionality"""

import unittest
import tempfile
import os
import json
import sys
from unittest.mock import Mock, patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.main_window import MainWindow
from src.core.database import LinkDatabase
from src.core.manager import LinkManager
from PySide6.QtWidgets import QApplication, QFileDialog


class TestImportExport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for the entire test class"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Create a MainWindow with temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

        # Create MainWindow with custom database
        self.window = MainWindow()
        self.window.db = LinkDatabase(self.temp_db.name)
        self.window.manager = LinkManager(self.temp_db.name)

    def tearDown(self):
        """Clean up resources"""
        # Close window without triggering closeEvent
        if hasattr(self, 'window'):
            # Override closeEvent to prevent database operations
            self.window.closeEvent = lambda event: event.accept()
            self.window.close()

        # Close database connection
        if hasattr(self, 'window') and hasattr(self.window, 'db'):
            if hasattr(self.window.db, 'conn'):
                self.window.db.conn.close()

        if os.path.exists(self.temp_db.name):
            try:
                os.unlink(self.temp_db.name)
            except PermissionError:
                pass  # File still in use on Windows

        # Clean up WAL files
        for ext in ['-wal', '-shm']:
            wal_file = self.temp_db.name + ext
            if os.path.exists(wal_file):
                try:
                    os.unlink(wal_file)
                except PermissionError:
                    pass  # File still in use on Windows

    def test_export_empty_database(self):
        """Test exporting from empty database"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = f.name

        try:
            # Mock the file dialog to return our temp file
            with patch.object(QFileDialog, 'getSaveFileName', return_value=(export_file, 'JSON (*.json)')):
                self.window.export_to_file()

            # Check the exported file
            with open(export_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.assertEqual(data['version'], '1.0')
            self.assertEqual(data['links'], [])

        finally:
            if os.path.exists(export_file):
                os.unlink(export_file)

    def test_export_with_data(self):
        """Test exporting database with links"""
        # Add some links
        self.window.db.add_link("File 1", "C:\\file1.txt", "tag1")
        self.window.db.add_link("File 2", "C:\\file2.txt", "tag2,tag3")
        self.window.db.add_link("File 3", "C:\\file3.txt", "")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = f.name

        try:
            # Mock the file dialog
            with patch.object(QFileDialog, 'getSaveFileName', return_value=(export_file, 'JSON (*.json)')):
                self.window.export_to_file()

            # Check the exported data
            with open(export_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.assertEqual(data['version'], '1.0')
            links = data['links']
            self.assertEqual(len(links), 3)
            self.assertEqual(links[0]['name'], "File 1")
            self.assertEqual(links[0]['path'], "C:\\file1.txt")
            self.assertEqual(links[0]['tags'], "tag1")
            self.assertEqual(links[1]['name'], "File 2")
            self.assertEqual(links[1]['path'], "C:\\file2.txt")
            self.assertEqual(links[1]['tags'], "tag2,tag3")

        finally:
            if os.path.exists(export_file):
                os.unlink(export_file)

    def test_import_valid_json_list(self):
        """Test importing valid JSON with proper format"""
        import_data = {
            "version": "1.0",
            "links": [
                {"name": "Import 1", "path": "C:\\import1.txt", "tags": "imported"},
                {"name": "Import 2", "path": "C:\\import2.txt", "tags": "test,imported"},
                {"name": "", "path": "C:\\import3.txt", "tags": ""}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(import_data, f)
            import_file = f.name

        try:
            # Mock the file dialog
            with patch.object(QFileDialog, 'getOpenFileName', return_value=(import_file, 'JSON (*.json)')):
                self.window.import_from_file()

            # Check that links were imported
            links = self.window.db.list_links()
            self.assertEqual(len(links), 3)
            self.assertEqual(links[0].name, "Import 1")
            self.assertEqual(links[0].path, "C:\\import1.txt")
            self.assertEqual(links[0].tags, "imported")
            self.assertEqual(links[2].name, "")
            self.assertEqual(links[2].path, "C:\\import3.txt")

        finally:
            if os.path.exists(import_file):
                os.unlink(import_file)

    def test_import_invalid_format(self):
        """Test importing invalid format (missing version)"""
        import_data = {"name": "Single Item", "path": "C:\\single.txt", "tags": "single"}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(import_data, f)
            import_file = f.name

        try:
            # Mock the file dialog
            with patch.object(QFileDialog, 'getOpenFileName', return_value=(import_file, 'JSON (*.json)')):
                # Should raise an error
                with self.assertRaises(Exception):
                    self.window.import_from_file()

        finally:
            if os.path.exists(import_file):
                os.unlink(import_file)

    def test_import_with_missing_fields(self):
        """Test importing JSON with missing fields"""
        import_data = {
            "version": "1.0",
            "links": [
                {"path": "C:\\noname.txt"},  # Missing name and tags
                {"name": "No Path"},  # Missing path
                {"name": "Complete", "path": "C:\\complete.txt", "tags": "test"},
                {}  # Empty object
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(import_data, f)
            import_file = f.name

        try:
            # Mock the file dialog
            with patch.object(QFileDialog, 'getOpenFileName', return_value=(import_file, 'JSON (*.json)')):
                self.window.import_from_file()

            # Check that only valid items were imported
            links = self.window.db.list_links()
            self.assertEqual(len(links), 2)  # Only items with paths should be imported

            # First link (noname.txt)
            self.assertEqual(links[0].name, "")
            self.assertEqual(links[0].path, "C:\\noname.txt")

            # Second link (complete)
            self.assertEqual(links[1].name, "Complete")
            self.assertEqual(links[1].path, "C:\\complete.txt")

        finally:
            if os.path.exists(import_file):
                os.unlink(import_file)

    def test_import_invalid_json(self):
        """Test importing invalid JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("This is not valid JSON {]")
            import_file = f.name

        try:
            # Mock the file dialog
            with patch.object(QFileDialog, 'getOpenFileName', return_value=(import_file, 'JSON (*.json)')):
                # Should show an error via QMessageBox
                with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
                    self.window.import_from_file()
                    # Error should be shown
                    mock_warning.assert_called_once()

            # Check that no links were imported
            links = self.window.db.list_links()
            self.assertEqual(len(links), 0)

        finally:
            if os.path.exists(import_file):
                os.unlink(import_file)

    def test_import_wrong_type_json(self):
        """Test importing JSON with wrong type (string instead of list/dict)"""
        import_data = "This is just a string"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(import_data, f)
            import_file = f.name

        try:
            # Mock the file dialog
            with patch.object(QFileDialog, 'getOpenFileName', return_value=(import_file, 'JSON (*.json)')):
                # Should show an error via QMessageBox
                with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
                    self.window.import_from_file()
                    # Error should be shown
                    mock_warning.assert_called_once()

            # Check that no links were imported
            links = self.window.db.list_links()
            self.assertEqual(len(links), 0)

        finally:
            if os.path.exists(import_file):
                os.unlink(import_file)

    def test_import_list_with_mixed_types(self):
        """Test importing list with mixed types (dicts and non-dicts)"""
        import_data = {
            "version": "1.0",
            "links": [
                {"name": "Valid 1", "path": "C:\\valid1.txt", "tags": "test"},
                "This is a string",  # Invalid
                123,  # Invalid
                {"name": "Valid 2", "path": "C:\\valid2.txt", "tags": "test"},
                None,  # Invalid
                {"name": "Valid 3", "path": "C:\\valid3.txt", "tags": "test"}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(import_data, f)
            import_file = f.name

        try:
            # Mock the file dialog
            with patch.object(QFileDialog, 'getOpenFileName', return_value=(import_file, 'JSON (*.json)')):
                self.window.import_from_file()

            # Check that only valid items were imported
            links = self.window.db.list_links()
            self.assertEqual(len(links), 3)
            self.assertEqual(links[0].name, "Valid 1")
            self.assertEqual(links[1].name, "Valid 2")
            self.assertEqual(links[2].name, "Valid 3")

        finally:
            if os.path.exists(import_file):
                os.unlink(import_file)

    def test_import_with_special_characters(self):
        """Test importing JSON with special characters"""
        import_data = {
            "version": "1.0",
            "links": [
                {"name": "日本語ファイル", "path": "C:\\日本語\\ファイル.txt", "tags": "日本語,テスト"},
                {"name": "File with 😀", "path": "C:\\emoji\\file.txt", "tags": "emoji,😀"},
                {"name": "File's \"Special\"", "path": "C:\\special\\file & more.txt", "tags": "special,&,\""}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(import_data, f, ensure_ascii=False)
            import_file = f.name

        try:
            # Mock the file dialog
            with patch.object(QFileDialog, 'getOpenFileName', return_value=(import_file, 'JSON (*.json)')):
                self.window.import_from_file()

            # Check that special characters were preserved
            links = self.window.db.list_links()
            self.assertEqual(len(links), 3)
            self.assertEqual(links[0].name, "日本語ファイル")
            self.assertEqual(links[0].path, "C:\\日本語\\ファイル.txt")
            self.assertEqual(links[1].name, "File with 😀")
            self.assertEqual(links[2].name, "File's \"Special\"")

        finally:
            if os.path.exists(import_file):
                os.unlink(import_file)

    def test_export_import_roundtrip(self):
        """Test that export and re-import preserves data"""
        # Add original links
        original_links = [
            ("File 1", "C:\\file1.txt", "tag1"),
            ("File 2", "C:\\file2.txt", "tag2,tag3"),
            ("日本語", "C:\\日本語.txt", "タグ"),
            ("", "C:\\noname.txt", "")
        ]

        for name, path, tags in original_links:
            self.window.db.add_link(name, path, tags)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            roundtrip_file = f.name

        try:
            # Export
            with patch.object(QFileDialog, 'getSaveFileName', return_value=(roundtrip_file, 'JSON (*.json)')):
                self.window.export_to_file()

            # Clear database
            for link in self.window.db.list_links():
                self.window.db.delete_link(link.id)

            # Re-import
            with patch.object(QFileDialog, 'getOpenFileName', return_value=(roundtrip_file, 'JSON (*.json)')):
                self.window.import_from_file()

            # Check that data matches
            links = self.window.db.list_links()
            self.assertEqual(len(links), len(original_links))

            for i, link in enumerate(links):
                # Empty names are preserved
                self.assertEqual(link.name, original_links[i][0])
                self.assertEqual(link.path, original_links[i][1])
                self.assertEqual(link.tags, original_links[i][2])

        finally:
            if os.path.exists(roundtrip_file):
                os.unlink(roundtrip_file)


if __name__ == '__main__':
    unittest.main()