"""
FS Link Manager - Themed Version
Professional theme system implementation based on QPalette
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Tuple, Any
from enum import Enum

from PySide6.QtCore import (
    Qt, QMimeData, QSize, Signal, Slot, QRect, QRectF,
    QPoint, QPointF, QModelIndex, QAbstractListModel
)
from PySide6.QtGui import (
    QAction, QIcon, QFont, QPainter, QPalette, QColor,
    QPen, QBrush, QPixmap, QImage, QPainterPath,
    QLinearGradient, QImageReader
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem, QLabel, QFileDialog,
    QMessageBox, QMenu, QPushButton, QStyle, QToolBar, QStatusBar,
    QInputDialog, QDialog, QTextEdit, QDialogButtonBox, QSplitter,
    QTableWidget, QTableWidgetItem, QFormLayout,
    QGroupBox, QTabWidget, QListView, QStyledItemDelegate,
    QGraphicsDropShadowEffect, QFrame, QButtonGroup,
    QRadioButton, QComboBox, QCheckBox, QSizePolicy
)

# Import custom modules
from theme_manager import ThemeManager, ThemedWidget
from widget_factory import WidgetFactory

# Configure logging
import logging
import sqlite3
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fs_link_manager_themed.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "links.db")


class ViewMode(Enum):
    """View modes for the link list"""
    LIST = "list"
    GRID = "grid"


# Database classes
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

    def get_tags_list(self) -> List[str]:
        """タグをリスト形式で取得"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]


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


class ThemedCardDelegate(QStyledItemDelegate):
    """Theme-aware card view delegate"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = ThemeManager()
        self.card_width = 200
        self.card_height = 220
        self.padding = 16
        self.icon_size = 64

    def paint(self, painter: QPainter, option, index):
        """Paint the card item using theme colors"""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # Get item data
        record = index.data(Qt.UserRole + 1)
        if not record:
            painter.restore()
            return

        rect = option.rect
        is_selected = option.state & QStyle.State_Selected
        is_hover = option.state & QStyle.State_MouseOver

        # Card background
        card_rect = rect.adjusted(8, 8, -8, -8)

        # Draw shadow
        if not is_selected:
            shadow_rect = card_rect.adjusted(2, 2, 2, 2)
            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(QRectF(shadow_rect), 12, 12)
            painter.fillPath(shadow_path, QColor(0, 0, 0, 30))

        # Draw card background using palette colors
        card_path = QPainterPath()
        card_path.addRoundedRect(QRectF(card_rect), 10, 10)

        # Use palette colors
        palette = QApplication.palette()
        if is_selected:
            bg_color = palette.color(QPalette.Highlight)
            painter.setPen(QPen(palette.color(QPalette.Highlight).darker(110), 2))
        elif is_hover:
            bg_color = palette.color(QPalette.AlternateBase)
            painter.setPen(QPen(palette.color(QPalette.Mid), 1))
        else:
            bg_color = palette.color(QPalette.Base)
            painter.setPen(QPen(palette.color(QPalette.Mid), 1))

        painter.fillPath(card_path, bg_color)
        painter.drawPath(card_path)

        # Content area
        content_rect = card_rect.adjusted(12, 12, -12, -12)

        # File icon (simplified for theme version)
        icon_rect = QRect(
            content_rect.x() + (content_rect.width() - self.icon_size) // 2,
            content_rect.y() + 10,
            self.icon_size,
            self.icon_size
        )

        # Draw file type icon
        if os.path.isdir(record.path):
            emoji = "📁"
            icon_color = self.theme_manager.get_color('primary')
        else:
            ext = os.path.splitext(record.path)[1].lower()
            emoji = "📄"
            icon_color = palette.color(QPalette.ButtonText)

        # Draw icon background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(icon_color.lighter(180)))
        painter.drawEllipse(icon_rect.adjusted(8, 8, -8, -8))

        # Draw emoji
        font = painter.font()
        font.setPointSize(24)
        painter.setFont(font)
        painter.setPen(palette.color(QPalette.HighlightedText if is_selected else QPalette.WindowText))
        painter.drawText(icon_rect, Qt.AlignCenter, emoji)

        # Draw title
        title_rect = QRect(
            content_rect.x(),
            icon_rect.bottom() + 12,
            content_rect.width(),
            30
        )

        title_font = painter.font()
        title_font.setPointSize(10)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(palette.color(QPalette.HighlightedText if is_selected else QPalette.WindowText))

        title = record.name or os.path.basename(record.path)
        elided_title = painter.fontMetrics().elidedText(title, Qt.ElideRight, title_rect.width())
        painter.drawText(title_rect, Qt.AlignHCenter | Qt.AlignTop, elided_title)

        # Draw path
        path_rect = QRect(
            content_rect.x(),
            title_rect.bottom() + 4,
            content_rect.width(),
            20
        )

        path_font = painter.font()
        path_font.setPointSize(8)
        painter.setFont(path_font)
        painter.setPen(palette.color(QPalette.Mid))

        elided_path = painter.fontMetrics().elidedText(record.path, Qt.ElideMiddle, path_rect.width())
        painter.drawText(path_rect, Qt.AlignHCenter | Qt.AlignTop, elided_path)

        painter.restore()

    def sizeHint(self, option, index):
        """Return the size hint for the card"""
        return QSize(self.card_width, self.card_height)


class ThemedListDelegate(QStyledItemDelegate):
    """Theme-aware list view delegate"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = ThemeManager()
        self.icon_size = 48
        self.item_height = 72
        self.padding = 12

    def paint(self, painter: QPainter, option, index):
        """Paint the list item using theme colors"""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Get item data
        record = index.data(Qt.UserRole + 1)
        if not record:
            painter.restore()
            return

        rect = option.rect
        is_selected = option.state & QStyle.State_Selected
        is_hover = option.state & QStyle.State_MouseOver

        palette = QApplication.palette()

        # Draw background
        if is_selected:
            painter.fillRect(rect, palette.color(QPalette.Highlight).lighter(150))
            painter.setPen(QPen(palette.color(QPalette.Highlight), 1))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
        elif is_hover:
            painter.fillRect(rect, palette.color(QPalette.AlternateBase))

        # Icon area
        icon_rect = QRect(
            rect.x() + self.padding,
            rect.y() + (rect.height() - self.icon_size) // 2,
            self.icon_size,
            self.icon_size
        )

        # Draw file type icon
        if os.path.isdir(record.path):
            emoji = "📁"
            icon_color = self.theme_manager.get_color('primary')
        else:
            emoji = "📄"
            icon_color = palette.color(QPalette.ButtonText)

        # Draw icon background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(icon_color.lighter(180)))
        icon_bg_rect = icon_rect.adjusted(4, 4, -4, -4)
        painter.drawRoundedRect(icon_bg_rect, 6, 6)

        # Draw emoji
        font = painter.font()
        font.setPointSize(18)
        painter.setFont(font)
        painter.setPen(palette.color(QPalette.HighlightedText if is_selected else QPalette.WindowText))
        painter.drawText(icon_bg_rect, Qt.AlignCenter, emoji)

        # Text area
        text_rect = QRect(
            icon_rect.right() + self.padding,
            rect.y() + self.padding,
            rect.width() - icon_rect.right() - self.padding * 2,
            rect.height() - self.padding * 2
        )

        # Draw title
        title_font = painter.font()
        title_font.setPointSize(10)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(palette.color(QPalette.HighlightedText if is_selected else QPalette.WindowText))

        title = record.name or os.path.basename(record.path)
        title_rect = QRect(text_rect.x(), text_rect.y(), text_rect.width(), 20)
        elided_title = painter.fontMetrics().elidedText(title, Qt.ElideRight, title_rect.width())
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_title)

        # Draw path
        path_font = painter.font()
        path_font.setPointSize(8)
        painter.setFont(path_font)
        painter.setPen(palette.color(QPalette.Mid))

        path_rect = QRect(text_rect.x(), title_rect.bottom() + 2, text_rect.width(), 16)
        elided_path = painter.fontMetrics().elidedText(record.path, Qt.ElideMiddle, path_rect.width())
        painter.drawText(path_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_path)

        painter.restore()

    def sizeHint(self, option, index):
        """Return the size hint for the list item"""
        return QSize(option.rect.width(), self.item_height)


class ThemedLinkList(QListView):
    """Theme-aware link list view"""

    linkDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListView.SingleSelection)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListView.InternalMove)
        self.setAlternatingRowColors(False)
        self.setUniformItemSizes(False)

        # View modes
        self._view_mode = ViewMode.LIST
        self._list_delegate = ThemedListDelegate(self)
        self._card_delegate = ThemedCardDelegate(self)

        # Set initial delegate
        self.setItemDelegate(self._list_delegate)

    def set_view_mode(self, mode: ViewMode):
        """Change the view mode"""
        self._view_mode = mode

        if mode == ViewMode.GRID:
            self.setViewMode(QListView.IconMode)
            self.setItemDelegate(self._card_delegate)
            self.setGridSize(QSize(self._card_delegate.card_width, self._card_delegate.card_height))
            self.setFlow(QListView.LeftToRight)
            self.setWrapping(True)
            self.setResizeMode(QListView.Adjust)
            self.setSpacing(8)
            self.setMovement(QListView.Static)
        else:
            self.setViewMode(QListView.ListMode)
            self.setItemDelegate(self._list_delegate)
            self.setGridSize(QSize())
            self.setFlow(QListView.TopToBottom)
            self.setWrapping(False)
            self.setResizeMode(QListView.Fixed)
            self.setSpacing(2)
            self.setMovement(QListView.Free)

        self.viewport().update()

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
        # External drop
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

        super().dropEvent(event)


class ThemedMainWindow(QMainWindow):
    """Main window with professional theme system"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FS Link Manager - Themed Edition")
        self.resize(1100, 750)

        # Initialize theme manager
        self.theme_manager = ThemeManager(QApplication.instance())

        # Initialize database
        self.db = LinkDatabase()

        # Create UI
        self._create_ui()

        # Load initial data
        self.reload_list()

        # Connect theme change signal
        self.theme_manager.theme_changed.connect(self.on_theme_changed)

    def _create_ui(self):
        """Create the user interface"""
        # Toolbar
        self._create_toolbar()

        # Central widget
        self._create_central_widget()

        # Status bar
        self._create_status_bar()

    def _create_toolbar(self):
        """Create toolbar with theme selector"""
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # View mode selector
        view_widget = QWidget()
        view_layout = QHBoxLayout(view_widget)
        view_layout.setContentsMargins(4, 0, 4, 0)
        view_layout.setSpacing(4)

        view_label = WidgetFactory.create_label("表示:", "default")
        view_layout.addWidget(view_label)

        self.view_combo = WidgetFactory.create_combo_box(
            ["リスト", "グリッド"]
        )
        self.view_combo.currentIndexChanged.connect(self._on_view_mode_changed)
        view_layout.addWidget(self.view_combo)

        toolbar.addWidget(view_widget)
        toolbar.addSeparator()

        # File operations
        add_act = QAction(self.style().standardIcon(QStyle.SP_FileDialogNewFolder), "追加", self)
        add_act.setToolTip("ファイルまたはフォルダを追加")
        add_act.triggered.connect(self.add_link_dialog)
        toolbar.addAction(add_act)

        import_act = QAction(self.style().standardIcon(QStyle.SP_ArrowDown), "インポート", self)
        import_act.triggered.connect(self.import_from_file)
        toolbar.addAction(import_act)

        export_act = QAction(self.style().standardIcon(QStyle.SP_ArrowUp), "エクスポート", self)
        export_act.triggered.connect(self.export_to_file)
        toolbar.addAction(export_act)

        toolbar.addSeparator()

        # Item operations
        open_act = QAction(self.style().standardIcon(QStyle.SP_DirOpenIcon), "開く", self)
        open_act.triggered.connect(self.open_selected)
        toolbar.addAction(open_act)

        edit_act = QAction(self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "編集", self)
        edit_act.triggered.connect(self.edit_selected)
        toolbar.addAction(edit_act)

        delete_act = QAction(self.style().standardIcon(QStyle.SP_TrashIcon), "削除", self)
        delete_act.triggered.connect(self.delete_selected)
        toolbar.addAction(delete_act)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        # Theme selector
        theme_widget = QWidget()
        theme_layout = QHBoxLayout(theme_widget)
        theme_layout.setContentsMargins(4, 0, 4, 0)

        theme_label = WidgetFactory.create_label("テーマ:", "default")
        theme_layout.addWidget(theme_label)

        # Get available themes
        available_themes = self.theme_manager.get_available_themes()
        theme_names_map = {
            'dark_professional': 'ダーク',
            'light_professional': 'ライト',
            'dark_high_contrast': 'ハイコントラスト'
        }

        theme_display_names = []
        self.theme_keys = []
        for theme_key in available_themes:
            display_name = theme_names_map.get(theme_key, theme_key)
            theme_display_names.append(display_name)
            self.theme_keys.append(theme_key)

        self.theme_combo = WidgetFactory.create_combo_box(theme_display_names)
        current_theme = self.theme_manager.get_current_theme()
        if current_theme in self.theme_keys:
            self.theme_combo.setCurrentIndex(self.theme_keys.index(current_theme))
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self.theme_combo)

        toolbar.addWidget(theme_widget)

    def _create_central_widget(self):
        """Create central widget"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Search bar
        self.search = WidgetFactory.create_input_field("検索（名前 / パス / タグ）", "search")
        self.search.textChanged.connect(self.reload_list)
        layout.addWidget(self.search)

        # List view
        self.list_view = ThemedLinkList()
        self.list_view.linkDropped.connect(self.on_links_dropped)
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self.open_context_menu)
        self.list_view.doubleClicked.connect(self.on_item_double_clicked)

        # Apply shadow effect
        WidgetFactory.apply_shadow_effect(self.list_view)

        layout.addWidget(self.list_view, 1)

    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _on_view_mode_changed(self, index):
        """Handle view mode change"""
        modes = [ViewMode.LIST, ViewMode.GRID]
        self.list_view.set_view_mode(modes[index])
        self.reload_list()

    def _on_theme_changed(self, index):
        """Handle theme selection change"""
        if index >= 0 and index < len(self.theme_keys):
            theme_key = self.theme_keys[index]
            self.theme_manager.apply_theme(theme_key)

    def on_theme_changed(self, theme_name: str):
        """Handle theme change signal"""
        self.status_bar.showMessage(f"テーマを変更しました: {theme_name}", 2000)

    def reload_list(self):
        """Reload the list with data"""
        # Simple list model
        class LinkListModel(QAbstractListModel):
            def __init__(self, records):
                super().__init__()
                self.records = records

            def rowCount(self, parent=QModelIndex()):
                return len(self.records)

            def data(self, index, role=Qt.DisplayRole):
                if not index.isValid():
                    return None

                record = self.records[index.row()]

                if role == Qt.DisplayRole:
                    return record.display_text()
                elif role == Qt.UserRole:
                    return record.id
                elif role == Qt.UserRole + 1:
                    return record

                return None

        # Get filtered records
        query = self.search.text()
        records = self.db.list_links(query)

        # Set model
        model = LinkListModel(records)
        self.list_view.setModel(model)

        # Update status
        self.status_bar.showMessage(f"{len(records)} 件のアイテム")

    def current_record_id(self) -> Optional[int]:
        """Get current selected record ID"""
        index = self.list_view.currentIndex()
        if not index.isValid():
            return None
        return index.data(Qt.UserRole)

    def get_record(self, id_: int) -> Optional[LinkRecord]:
        """Get record by ID"""
        recs = {r.id: r for r in self.db.list_links(self.search.text())}
        return recs.get(id_)

    @Slot(list)
    def on_links_dropped(self, pairs: List[tuple]):
        """Handle dropped links"""
        for name, path in pairs:
            # Auto-generate tags
            tags = []
            ext = os.path.splitext(path)[1].lower()
            if ext:
                tags.append(ext[1:].upper())
            if os.path.isdir(path):
                tags.append("フォルダ")

            self.db.add_link(
                name=name,
                path=path,
                tags=", ".join(tags) if tags else ""
            )

        self.reload_list()
        self.status_bar.showMessage(f"{len(pairs)} 件のアイテムを追加しました", 3000)

    def on_item_double_clicked(self, index):
        """Handle double click on item"""
        if not index.isValid():
            return

        record = index.data(Qt.UserRole + 1)
        if record:
            self.open_in_explorer(record.path)

    def open_in_explorer(self, path: str):
        """Open path in Windows Explorer"""
        if not path:
            return
        import subprocess
        if os.path.isdir(path):
            subprocess.Popen(f'explorer "{os.path.normpath(path)}"', shell=True)
        else:
            if os.path.exists(path):
                subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"', shell=True)
            else:
                parent = os.path.dirname(path) or path
                subprocess.Popen(f'explorer "{os.path.normpath(parent)}"', shell=True)

    def add_link_dialog(self):
        """Show dialog to add links"""
        dlg = QFileDialog(self, "リンク対象を選択")
        dlg.setFileMode(QFileDialog.ExistingFiles)
        if dlg.exec():
            paths = dlg.selectedFiles()
            pairs = [(os.path.basename(p) or p, p) for p in paths]
            self.on_links_dropped(pairs)

    def edit_selected(self):
        """Edit selected item"""
        id_ = self.current_record_id()
        if id_ is None:
            return
        rec = self.get_record(id_)
        if not rec:
            return

        name, ok1 = QInputDialog.getText(self, "名前を編集", "表示名:", text=rec.name)
        if not ok1:
            return
        tags, ok2 = QInputDialog.getText(self, "タグを編集", "カンマ区切りタグ:", text=rec.tags)
        if not ok2:
            return

        self.db.update_link(rec.id, name=name, tags=tags)
        self.reload_list()

    def delete_selected(self):
        """Delete selected item"""
        id_ = self.current_record_id()
        if id_ is None:
            return

        reply = QMessageBox.question(
            self, "確認", "選択したアイテムを削除しますか？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_link(id_)
            self.reload_list()
            self.status_bar.showMessage("アイテムを削除しました", 2000)

    def open_selected(self):
        """Open selected item"""
        id_ = self.current_record_id()
        if id_ is None:
            return
        rec = self.get_record(id_)
        if rec:
            self.open_in_explorer(rec.path)

    def open_context_menu(self, pos):
        """Show context menu"""
        index = self.list_view.indexAt(pos)
        menu = QMenu(self)

        if index.isValid():
            open_act = QAction("エクスプローラで開く", self)
            open_act.triggered.connect(self.open_selected)
            menu.addAction(open_act)

            menu.addSeparator()

            edit_act = QAction("名前/タグを編集", self)
            edit_act.triggered.connect(self.edit_selected)
            menu.addAction(edit_act)

            del_act = QAction("削除", self)
            del_act.triggered.connect(self.delete_selected)
            menu.addAction(del_act)
        else:
            add_act = QAction("ファイル/フォルダを追加…", self)
            add_act.triggered.connect(self.add_link_dialog)
            menu.addAction(add_act)

        menu.exec(self.list_view.mapToGlobal(pos))

    def export_to_file(self):
        """Export to JSON file"""
        path, _ = QFileDialog.getSaveFileName(self, "エクスポート", "links.json", "JSON (*.json)")
        if not path:
            return

        records = self.db.list_links()
        data = [
            {"name": r.name, "path": r.path, "tags": r.tags}
            for r in records
        ]

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.status_bar.showMessage("エクスポートしました", 2000)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"エクスポートに失敗: {e}")

    def import_from_file(self):
        """Import from JSON file"""
        path, _ = QFileDialog.getOpenFileName(self, "インポート", "", "JSON (*.json)")
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                data = [data]

            count = 0
            for item in data:
                if isinstance(item, dict) and item.get("path"):
                    name = item.get("name") or os.path.basename(item["path"])
                    self.db.add_link(
                        name=name,
                        path=item["path"],
                        tags=item.get("tags", "")
                    )
                    count += 1

            self.reload_list()
            self.status_bar.showMessage(f"{count} 件をインポートしました", 2000)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"インポートに失敗: {e}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FS Link Manager Themed")

    # Set application font
    font = app.font()
    font.setFamily("Segoe UI, Yu Gothic UI, Meiryo, sans-serif")
    app.setFont(font)

    # Initialize theme manager (will apply default theme)
    theme_manager = ThemeManager(app)

    # Create and show main window
    win = ThemedMainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()