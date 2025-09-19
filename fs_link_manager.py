
"""
FS Link Manager - Drag & Drop file server link organizer
Author: ChatGPT
Requirements: Python 3.9+ and PySide6
Platform: Windows (Explorer integration)
"""

import os
import sys
import sqlite3
import subprocess
import logging
from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import Qt, QMimeData, QSize, Signal, Slot
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem, QLabel, QFileDialog,
    QMessageBox, QMenu, QPushButton, QStyle, QToolBar, QStatusBar,
    QInputDialog, QDialog, QTextEdit, QDialogButtonBox, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QFormLayout,
    QGroupBox, QTabWidget, QToolButton
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fs_link_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "links.db")


class LinkRecord:
    def __init__(self, id_: int, name: str, path: str, tags: str, position: int, added_at: str):
        self.id = id_
        self.name = name
        self.path = path
        self.tags = tags or ""
        self.position = position
        self.added_at = added_at

    def display_text(self) -> str:
        base = self.name if self.name else os.path.basename(self.path) or self.path
        tag_part = f"  [{self.tags}]" if self.tags else ""
        return f"{base}{tag_part}\n{self.path}"


class LinkDatabase:
    def __init__(self, db_path: str = DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self._init_schema()

    def _init_schema(self):
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

    def update_link(self, id_: int, *, name: Optional[str] = None, path: Optional[str] = None, tags: Optional[str] = None):
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
        self.conn.execute("DELETE FROM links WHERE id = ?;", (id_,))
        self.conn.commit()

    def list_links(self, search: str = "") -> List[LinkRecord]:
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
        # Reassign positions to match list order
        for pos, id_ in enumerate(ordered_ids):
            self.conn.execute("UPDATE links SET position = ? WHERE id = ?;", (pos, id_))
        self.conn.commit()


class LinkAddDialog(QDialog):
    """Dialog for adding links with individual form fields"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("リンクを追加")
        self.setModal(True)
        self.resize(800, 600)

        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Tab widget for different input methods
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Form input tab
        self.form_widget = self.create_form_tab()
        self.tab_widget.addTab(self.form_widget, "フォーム入力")

        # Table input tab
        self.table_widget = self.create_table_tab()
        self.tab_widget.addTab(self.table_widget, "複数リンク")

        # Advanced JSON tab
        self.json_widget = self.create_json_tab()
        self.tab_widget.addTab(self.json_widget, "アドバンス（JSON）")

        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def create_form_tab(self):
        """Create form-based input tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Form group box
        form_group = QGroupBox("リンク情報")
        form_layout = QFormLayout()
        form_group.setLayout(form_layout)

        # Path field with browse button
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("必須: C:\\folder\\file.txt")
        path_layout.addWidget(self.path_edit)

        browse_btn = QPushButton("参照...")
        browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(browse_btn)

        form_layout.addRow("パス (必須):", path_layout)

        # Name field
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("オプション: 自動でファイル名が使われます")
        form_layout.addRow("表示名:", self.name_edit)

        # Tags field
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("オプション: タグ1,タグ2,タグ3")
        form_layout.addRow("タグ:", self.tags_edit)

        layout.addWidget(form_group)

        # Preview
        preview_group = QGroupBox("プレビュー")
        preview_layout = QVBoxLayout()
        preview_group.setLayout(preview_layout)

        self.preview_label = QLabel("入力内容のプレビューがここに表示されます")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("padding: 10px; background-color: #f0f0f0;")
        preview_layout.addWidget(self.preview_label)

        layout.addWidget(preview_group)

        # Connect updates
        self.path_edit.textChanged.connect(self.update_preview)
        self.name_edit.textChanged.connect(self.update_preview)
        self.tags_edit.textChanged.connect(self.update_preview)

        layout.addStretch()
        return widget

    def create_table_tab(self):
        """Create table-based input tab for multiple links"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Instructions
        instructions = QLabel(
            "複数のリンクを表形式で入力できます。\n"
            "ドラッグ＆ドロップでファイルを追加することもできます。"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["パス (必須)", "表示名", "タグ"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAcceptDrops(True)

        # Initial empty rows
        self.add_table_row()

        layout.addWidget(self.table)

        # Table control buttons
        btn_layout = QHBoxLayout()

        add_row_btn = QPushButton("行を追加")
        add_row_btn.clicked.connect(self.add_table_row)
        btn_layout.addWidget(add_row_btn)

        remove_row_btn = QPushButton("選択行を削除")
        remove_row_btn.clicked.connect(self.remove_table_row)
        btn_layout.addWidget(remove_row_btn)

        clear_btn = QPushButton("すべてクリア")
        clear_btn.clicked.connect(self.clear_table)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return widget

    def create_json_tab(self):
        """Create JSON editor tab (advanced)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Warning
        warning = QLabel(
            "⚠️ アドバンスモード: JSON形式を直接編集できます。\n"
            "構文エラーに注意してください。"
        )
        warning.setStyleSheet("color: orange; font-weight: bold;")
        layout.addWidget(warning)

        # JSON editor
        self.json_editor = QTextEdit()
        self.json_editor.setFont(QFont("Consolas", 10))
        self.json_editor.setPlaceholderText(
            '[\n'
            '  {\n'
            '    "name": "ファイル名",\n'
            '    "path": "C:\\\\path\\\\file.txt",\n'
            '    "tags": "タグ1,タグ2"\n'
            '  }\n'
            ']'
        )
        layout.addWidget(self.json_editor)

        # Template buttons
        template_layout = QHBoxLayout()

        single_template_btn = QPushButton("単一テンプレート")
        single_template_btn.clicked.connect(self.insert_single_json_template)
        template_layout.addWidget(single_template_btn)

        multi_template_btn = QPushButton("複数テンプレート")
        multi_template_btn.clicked.connect(self.insert_multi_json_template)
        template_layout.addWidget(multi_template_btn)

        format_btn = QPushButton("JSON整形")
        format_btn.clicked.connect(self.format_json)
        template_layout.addWidget(format_btn)

        template_layout.addStretch()
        layout.addLayout(template_layout)

        return widget

    def browse_path(self):
        """Open file/folder browser"""
        dlg = QFileDialog(self, "リンク対象を選択")
        dlg.setFileMode(QFileDialog.AnyFile)
        if dlg.exec():
            paths = dlg.selectedFiles()
            if paths:
                self.path_edit.setText(paths[0])

    def update_preview(self):
        """Update preview based on form input"""
        path = self.path_edit.text()
        name = self.name_edit.text() or os.path.basename(path) if path else ""
        tags = self.tags_edit.text()

        if not path:
            self.preview_label.setText("パスを入力してください")
            self.preview_label.setStyleSheet("padding: 10px; background-color: #fff0f0;")
        else:
            preview = f"表示名: {name}\nパス: {path}"
            if tags:
                preview += f"\nタグ: {tags}"
            self.preview_label.setText(preview)
            self.preview_label.setStyleSheet("padding: 10px; background-color: #f0fff0;")

    def add_table_row(self):
        """Add a new row to the table"""
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)

    def remove_table_row(self):
        """Remove selected row from table"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def clear_table(self):
        """Clear all table rows"""
        self.table.setRowCount(0)
        self.add_table_row()

    def insert_single_json_template(self):
        """Insert single link JSON template"""
        template = '{\n  "name": "ファイル名",\n  "path": "C:\\\\path\\\\file.txt",\n  "tags": "タグ1,タグ2"\n}'
        self.json_editor.setPlainText(template)

    def insert_multi_json_template(self):
        """Insert multiple links JSON template"""
        template = '[\n  {\n    "name": "ファイル1",\n    "path": "C:\\\\path\\\\file1.txt",\n    "tags": "タグ1"\n  },\n  {\n    "name": "ファイル2",\n    "path": "C:\\\\path\\\\file2.txt",\n    "tags": "タグ2"\n  }\n]'
        self.json_editor.setPlainText(template)

    def format_json(self):
        """Format JSON text"""
        try:
            import json
            text = self.json_editor.toPlainText()
            if text:
                data = json.loads(text)
                formatted = json.dumps(data, ensure_ascii=False, indent=2)
                self.json_editor.setPlainText(formatted)
        except:
            pass

    def validate_and_accept(self):
        """Validate input and accept dialog"""
        current_tab = self.tab_widget.currentIndex()

        if current_tab == 0:  # Form tab
            if not self.path_edit.text():
                QMessageBox.warning(self, "入力エラー", "パスは必須項目です")
                return
        elif current_tab == 1:  # Table tab
            has_valid = False
            for row in range(self.table.rowCount()):
                path_item = self.table.item(row, 0)
                if path_item and path_item.text():
                    has_valid = True
                    break
            if not has_valid:
                QMessageBox.warning(self, "入力エラー", "少なくとも1つのパスを入力してください")
                return
        elif current_tab == 2:  # JSON tab
            try:
                import json
                text = self.json_editor.toPlainText()
                if text:
                    json.loads(text)
            except:
                QMessageBox.warning(self, "JSONエラー", "JSON形式が正しくありません")
                return

        self.accept()

    def get_links_data(self):
        """Get the entered links data"""
        current_tab = self.tab_widget.currentIndex()
        links = []

        if current_tab == 0:  # Form tab
            path = self.path_edit.text()
            if path:
                links.append({
                    "path": path,
                    "name": self.name_edit.text(),
                    "tags": self.tags_edit.text()
                })
        elif current_tab == 1:  # Table tab
            for row in range(self.table.rowCount()):
                path_item = self.table.item(row, 0)
                name_item = self.table.item(row, 1)
                tags_item = self.table.item(row, 2)

                if path_item and path_item.text():
                    links.append({
                        "path": path_item.text(),
                        "name": name_item.text() if name_item else "",
                        "tags": tags_item.text() if tags_item else ""
                    })
        elif current_tab == 2:  # JSON tab
            try:
                import json
                text = self.json_editor.toPlainText()
                if text:
                    data = json.loads(text)
                    if isinstance(data, dict):
                        links = [data]
                    else:
                        links = data
            except:
                pass

        return links


class JsonEditorDialog(QDialog):
    """JSON editor dialog for creating and editing link data"""

    def __init__(self, parent=None, initial_data=None):
        super().__init__(parent)
        self.setWindowTitle("JSONリンクエディタ")
        self.resize(900, 600)

        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Instructions
        instructions = QLabel(
            "JSON形式でリンクデータを編集できます。\n"
            "必須フィールド: path (ファイルやフォルダのパス)\n"
            "オプション: name (表示名), tags (カンマ区切りタグ)"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Splitter for editor and preview
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left side - JSON editor
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_label = QLabel("JSONエディタ:")
        editor_layout.addWidget(editor_label)

        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 10))
        self.editor.textChanged.connect(self.validate_json)
        editor_layout.addWidget(self.editor)

        splitter.addWidget(editor_widget)

        # Right side - Preview and validation
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_label = QLabel("プレビュー・検証結果:")
        preview_layout.addWidget(preview_label)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas", 9))
        preview_layout.addWidget(self.preview)

        splitter.addWidget(preview_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # Buttons row
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        # Template buttons
        template_single_btn = QPushButton("単一リンクのテンプレート")
        template_single_btn.clicked.connect(self.insert_single_template)
        button_layout.addWidget(template_single_btn)

        template_multi_btn = QPushButton("複数リンクのテンプレート")
        template_multi_btn.clicked.connect(self.insert_multi_template)
        button_layout.addWidget(template_multi_btn)

        format_btn = QPushButton("JSONを整形")
        format_btn.clicked.connect(self.format_json)
        button_layout.addWidget(format_btn)

        button_layout.addStretch()

        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        # Set initial data
        if initial_data:
            self.editor.setPlainText(initial_data)
        else:
            self.insert_multi_template()

        self.validate_json()

    def insert_single_template(self):
        """Insert single link template"""
        template = """{
  "name": "ファイル名",
  "path": "C:\\\\パス\\\\ファイル.txt",
  "tags": "タグ1,タグ2"
}"""
        self.editor.setPlainText(template)

    def insert_multi_template(self):
        """Insert multiple links template"""
        template = """[
  {
    "name": "ドキュメント",
    "path": "C:\\\\Documents\\\\file.docx",
    "tags": "仕様書,重要"
  },
  {
    "name": "プロジェクトフォルダ",
    "path": "C:\\\\Projects\\\\MyProject",
    "tags": "開発"
  },
  {
    "name": "ネットワーク共有",
    "path": "\\\\\\\\server\\\\share\\\\folder",
    "tags": "共有,ネットワーク"
  }
]"""
        self.editor.setPlainText(template)

    def format_json(self):
        """Format JSON text"""
        try:
            import json
            text = self.editor.toPlainText()
            data = json.loads(text)
            formatted = json.dumps(data, ensure_ascii=False, indent=2)
            self.editor.setPlainText(formatted)
            self.preview.setStyleSheet("color: green;")
            self.preview.setPlainText("✓ JSON形式が正しく、整形されました")
        except json.JSONDecodeError as e:
            self.preview.setStyleSheet("color: red;")
            self.preview.setPlainText(f"✗ JSON形式エラー: {e}")
        except Exception as e:
            self.preview.setStyleSheet("color: red;")
            self.preview.setPlainText(f"✗ エラー: {e}")

    def validate_json(self):
        """Validate JSON and show preview"""
        try:
            import json
            text = self.editor.toPlainText()
            if not text.strip():
                self.preview.setStyleSheet("color: gray;")
                self.preview.setPlainText("JSONデータを入力してください")
                self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
                return

            data = json.loads(text)

            # Validate structure
            validation_msgs = []
            valid_count = 0
            invalid_count = 0

            # Handle both single object and list
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                raise ValueError("JSONはオブジェクトまたは配列である必要があります")

            for i, item in enumerate(data, 1):
                if not isinstance(item, dict):
                    validation_msgs.append(f"✗ アイテム {i}: 辞書型である必要があります")
                    invalid_count += 1
                    continue

                if "path" not in item or not item.get("path"):
                    validation_msgs.append(f"✗ アイテム {i}: 'path'フィールドが必須です")
                    invalid_count += 1
                else:
                    name = item.get("name", os.path.basename(item["path"]))
                    path = item["path"]
                    tags = item.get("tags", "")
                    validation_msgs.append(
                        f"✓ アイテム {i}: {name}\n"
                        f"   パス: {path}\n"
                        f"   タグ: {tags if tags else '(なし)'}"
                    )
                    valid_count += 1

            # Show validation results
            result = f"検証結果: {valid_count}件有効, {invalid_count}件無効\n\n"
            result += "\n".join(validation_msgs)

            if invalid_count == 0 and valid_count > 0:
                self.preview.setStyleSheet("color: green;")
                self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
            else:
                self.preview.setStyleSheet("color: orange;")
                self.button_box.button(QDialogButtonBox.Ok).setEnabled(valid_count > 0)

            self.preview.setPlainText(result)

        except json.JSONDecodeError as e:
            self.preview.setStyleSheet("color: red;")
            self.preview.setPlainText(
                f"✗ JSON形式エラー:\n"
                f"行 {e.lineno}, 位置 {e.colno}: {e.msg}"
            )
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        except Exception as e:
            self.preview.setStyleSheet("color: red;")
            self.preview.setPlainText(f"✗ エラー: {e}")
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

    def get_json_text(self):
        """Get the JSON text from editor"""
        return self.editor.toPlainText()


class LinkList(QListWidget):
    """A list that supports internal move and external drops of files/folders/paths."""

    linkDropped = Signal(list)  # list of (name, path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setAlternatingRowColors(True)
        self.setIconSize(QSize(20, 20))
        self.setUniformItemSizes(False)
        self.setWordWrap(True)

    def mimeTypes(self):
        return ["text/uri-list", "text/plain"]

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        # External drop (files/folders/UNC text)
        if event.mimeData().hasUrls():
            pairs = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    name = os.path.basename(path) or path
                    pairs.append((name, path))
            if pairs:
                self.linkDropped.emit(pairs)
                event.acceptProposedAction()
                return
        if event.mimeData().hasText():
            text = event.mimeData().text().strip()
            if text:
                # Allow newline-separated paths
                pairs = []
                for line in text.splitlines():
                    p = line.strip().strip('"')
                    if p:
                        name = os.path.basename(p) or p
                        pairs.append((name, p))
                if pairs:
                    self.linkDropped.emit(pairs)
                    event.acceptProposedAction()
                    return
        # Internal move (reordering)
        super().dropEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FS Link Manager")
        self.resize(780, 520)
        self.db = LinkDatabase()

        # Toolbar
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Set toolbar style
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        # File Operations Group
        add_act = QAction(self.style().standardIcon(QStyle.SP_FileDialogNewFolder), "追加", self)
        add_act.setToolTip("ファイルまたはフォルダを選択して追加")
        add_act.setStatusTip("ファイルまたはフォルダを選択してリンクリストに追加します")
        add_act.triggered.connect(self.add_link_dialog)
        toolbar.addAction(add_act)

        multi_add_act = QAction(self.style().standardIcon(QStyle.SP_FileDialogListView), "複数追加", self)
        multi_add_act.setToolTip("複数のリンクを一括追加")
        multi_add_act.setStatusTip("フォームを使って複数のリンクを効率的に追加します")
        multi_add_act.triggered.connect(self.open_link_add_dialog)
        toolbar.addAction(multi_add_act)

        import_act = QAction(self.style().standardIcon(QStyle.SP_ArrowDown), "インポート", self)
        import_act.setToolTip("JSONファイルからインポート")
        import_act.setStatusTip("JSONファイルからリンクデータをインポートします")
        import_act.triggered.connect(self.import_from_file)
        toolbar.addAction(import_act)

        export_act = QAction(self.style().standardIcon(QStyle.SP_ArrowUp), "エクスポート", self)
        export_act.setToolTip("JSONファイルにエクスポート")
        export_act.setStatusTip("現在のリンクデータをJSONファイルにエクスポートします")
        export_act.triggered.connect(self.export_to_file)
        toolbar.addAction(export_act)

        toolbar.addSeparator()

        # Item Operations Group
        open_act = QAction(self.style().standardIcon(QStyle.SP_DirOpenIcon), "開く", self)
        open_act.setToolTip("選択したアイテムをエクスプローラで開く")
        open_act.setStatusTip("選択したリンクをWindowsエクスプローラで開きます")
        open_act.triggered.connect(self.open_selected)
        toolbar.addAction(open_act)

        edit_act = QAction(self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "編集", self)
        edit_act.setToolTip("選択したアイテムを編集")
        edit_act.setStatusTip("選択したリンクの名前とタグを編集します")
        edit_act.triggered.connect(self.edit_selected)
        toolbar.addAction(edit_act)

        copy_act = QAction(self.style().standardIcon(QStyle.SP_FileDialogContentsView), "コピー", self)
        copy_act.setToolTip("パスをクリップボードにコピー")
        copy_act.setStatusTip("選択したリンクのパスをクリップボードにコピーします")
        copy_act.triggered.connect(self.copy_selected_path)
        toolbar.addAction(copy_act)

        delete_act = QAction(self.style().standardIcon(QStyle.SP_TrashIcon), "削除", self)
        delete_act.setToolTip("選択したアイテムを削除")
        delete_act.setStatusTip("選択したリンクをリストから削除します")
        delete_act.triggered.connect(self.delete_selected)
        toolbar.addAction(delete_act)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)

        # Search bar
        self.search = QLineEdit()
        self.search.setPlaceholderText("検索（名前 / パス / タグ）")
        self.search.textChanged.connect(self.reload_list)
        v.addWidget(self.search)

        # List
        self.listw = LinkList()
        self.listw.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.listw.linkDropped.connect(self.on_links_dropped)
        self.listw.setContextMenuPolicy(Qt.CustomContextMenu)
        self.listw.customContextMenuRequested.connect(self.open_context_menu)
        v.addWidget(self.listw, 1)

        # Status bar
        self.setStatusBar(QStatusBar())

        self.reload_list()

    def icon_for_path(self, path: str) -> QIcon:
        if os.path.isdir(path):
            return self.style().standardIcon(QStyle.SP_DirIcon)
        else:
            return self.style().standardIcon(QStyle.SP_FileIcon)

    def make_item(self, rec: LinkRecord) -> QListWidgetItem:
        item = QListWidgetItem(rec.display_text())
        item.setData(Qt.UserRole, rec.id)
        item.setToolTip(rec.path)
        item.setIcon(self.icon_for_path(rec.path))
        # Slightly taller items for two lines
        item.setSizeHint(QSize(item.sizeHint().width(), 40))
        return item

    def reload_list(self):
        self.listw.clear()
        query = self.search.text()
        for rec in self.db.list_links(query):
            self.listw.addItem(self.make_item(rec))
        self.statusBar().showMessage(f"{self.listw.count()} 件")

    @Slot(list)
    def on_links_dropped(self, pairs: List[tuple]):
        for name, path in pairs:
            self.db.add_link(name=name, path=path, tags="")
        self.reload_list()
        self.statusBar().showMessage(f"{len(pairs)} 件追加")

    def current_record_id(self) -> Optional[int]:
        item = self.listw.currentItem()
        if not item:
            return None
        return int(item.data(Qt.UserRole))

    def get_record(self, id_: int) -> Optional[LinkRecord]:
        recs = {r.id: r for r in self.db.list_links(self.search.text())}
        return recs.get(id_)

    def open_in_explorer(self, path: str):
        if not path:
            return
        if os.path.isdir(path):
            # Open folder directly
            subprocess.Popen(["explorer", path])
        else:
            # If the path exists and is a file, select it; otherwise try to open parent
            if os.path.exists(path):
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            else:
                parent = os.path.dirname(path) or path
                subprocess.Popen(["explorer", parent])

    def on_item_double_clicked(self, item: QListWidgetItem):
        id_ = int(item.data(Qt.UserRole))
        rec = self.get_record(id_)
        if rec:
            self.open_in_explorer(rec.path)

    def add_link_dialog(self):
        # Simple add via file/folder picker
        dlg = QFileDialog(self, "リンク対象を選択")
        dlg.setFileMode(QFileDialog.ExistingFiles)
        if dlg.exec():
            paths = dlg.selectedFiles()
            for p in paths:
                name = os.path.basename(p) or p
                self.db.add_link(name=name, path=p, tags="")
            self.reload_list()

    def copy_selected_path(self):
        id_ = self.current_record_id()
        if id_ is None:
            return
        rec = self.get_record(id_)
        if not rec:
            return
        QApplication.clipboard().setText(rec.path)
        self.statusBar().showMessage("パスをコピーしました")

    def delete_selected(self):
        id_ = self.current_record_id()
        if id_ is None:
            return
        self.db.delete_link(id_)
        self.reload_list()

    def edit_selected(self):
        id_ = self.current_record_id()
        if id_ is None:
            return
        rec = self.get_record(id_)
        if not rec:
            return
        # Inline edit for name and tags
        name, ok1 = QInputDialog.getText(self, "名前を編集", "表示名:", text=rec.name)
        if not ok1:
            return
        tags, ok2 = QInputDialog.getText(self, "タグを編集", "カンマ区切りタグ:", text=rec.tags)
        if not ok2:
            return
        self.db.update_link(rec.id, name=name, tags=tags)
        self.reload_list()

    def open_selected(self):
        id_ = self.current_record_id()
        if id_ is None:
            return
        rec = self.get_record(id_)
        if rec:
            self.open_in_explorer(rec.path)

    def open_context_menu(self, pos):
        item = self.listw.itemAt(pos)
        menu = QMenu(self)
        if item:
            open_act = QAction("エクスプローラで開く", self)
            open_act.triggered.connect(self.open_selected)
            menu.addAction(open_act)

            copy_act = QAction("パスをコピー", self)
            copy_act.triggered.connect(self.copy_selected_path)
            menu.addAction(copy_act)

            rename_act = QAction("名前/タグを編集", self)
            rename_act.triggered.connect(self.edit_selected)
            menu.addAction(rename_act)

            del_act = QAction("削除", self)
            del_act.triggered.connect(self.delete_selected)
            menu.addAction(del_act)
        else:
            add_act = QAction("ファイル/フォルダを追加…", self)
            add_act.triggered.connect(self.add_link_dialog)
            menu.addAction(add_act)
        menu.exec(self.listw.mapToGlobal(pos))

    def export_to_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "エクスポート", "links.json", "JSON (*.json)")
        if not path:
            return
        records = self.db.list_links(self.search.text())
        data = [
            {"name": r.name, "path": r.path, "tags": r.tags, "position": r.position, "added_at": r.added_at}
            for r in records
        ]
        try:
            import json
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.statusBar().showMessage("エクスポートしました")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"エクスポートに失敗しました: {e}")

    def import_from_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "インポート", "", "JSON (*.json)")
        if not path:
            return

        logger.info(f"Importing from file: {path}")

        try:
            import json
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Log the type and structure of loaded data
            logger.debug(f"Loaded JSON data type: {type(data)}")
            logger.debug(f"Data content (first 500 chars): {str(data)[:500]}")

            # Validate that data is a list
            if not isinstance(data, list):
                logger.error(f"Expected list, got {type(data).__name__}")
                if isinstance(data, dict):
                    logger.info("Converting single dictionary to list")
                    data = [data]
                else:
                    raise ValueError(f"Invalid JSON format: expected list of objects, got {type(data).__name__}")

            logger.info(f"Processing {len(data)} items from import file")

            imported_count = 0
            for index, item in enumerate(data):
                logger.debug(f"Processing item {index + 1}/{len(data)}: type={type(item)}")

                # Validate that item is a dictionary
                if not isinstance(item, dict):
                    logger.warning(f"Skipping item {index + 1}: expected dict, got {type(item).__name__}: {item}")
                    continue

                logger.debug(f"Item {index + 1} keys: {item.keys() if isinstance(item, dict) else 'N/A'}")

                name = item.get("name") or os.path.basename(item.get("path", ""))
                p = item.get("path", "")
                tags = item.get("tags", "")

                if not p:
                    logger.warning(f"Skipping item {index + 1}: no path specified")
                    continue

                logger.debug(f"Adding link: name='{name}', path='{p}', tags='{tags}'")
                self.db.add_link(name=name, path=p, tags=tags)
                imported_count += 1

            self.reload_list()
            success_msg = f"インポートしました ({imported_count}/{len(data)} 件)"
            logger.info(success_msg)
            self.statusBar().showMessage(success_msg)

        except json.JSONDecodeError as e:
            error_msg = f"JSONファイルの形式が不正です: {e}"
            logger.error(error_msg)
            QMessageBox.critical(self, "エラー", error_msg)
        except Exception as e:
            error_msg = f"インポートに失敗しました: {e}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "エラー", error_msg)

    def open_link_add_dialog(self):
        """Open the new link add dialog with form fields"""
        dialog = LinkAddDialog(self)
        if dialog.exec():
            links_data = dialog.get_links_data()
            added_count = 0

            for link in links_data:
                if link.get("path"):
                    name = link.get("name") or os.path.basename(link.get("path", ""))
                    path = link.get("path", "")
                    tags = link.get("tags", "")
                    self.db.add_link(name=name, path=path, tags=tags)
                    added_count += 1

            if added_count > 0:
                self.reload_list()
                self.statusBar().showMessage(f"{added_count} 件のリンクを追加しました")

    def open_json_editor(self):
        """Open JSON editor dialog"""
        # Get current links as JSON for editing
        current_links = self.db.list_links()
        current_json = []
        for link in current_links:
            current_json.append({
                "name": link.name,
                "path": link.path,
                "tags": link.tags
            })

        import json
        initial_data = json.dumps(current_json, ensure_ascii=False, indent=2) if current_json else None

        dialog = JsonEditorDialog(self, initial_data)
        if dialog.exec():
            # Import the edited JSON
            json_text = dialog.get_json_text()
            try:
                data = json.loads(json_text)

                # Handle both single object and list
                if isinstance(data, dict):
                    data = [data]

                imported_count = 0
                for item in data:
                    if isinstance(item, dict) and item.get("path"):
                        name = item.get("name") or os.path.basename(item.get("path", ""))
                        path = item.get("path", "")
                        tags = item.get("tags", "")
                        self.db.add_link(name=name, path=path, tags=tags)
                        imported_count += 1

                self.reload_list()
                self.statusBar().showMessage(f"JSONエディタから {imported_count} 件追加")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"JSONの処理に失敗しました: {e}")

    def closeEvent(self, event):
        # Persist new order on close
        ids = []
        for i in range(self.listw.count()):
            item = self.listw.item(i)
            ids.append(int(item.data(Qt.UserRole)))
        self.db.reorder(ids)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FS Link Manager")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
