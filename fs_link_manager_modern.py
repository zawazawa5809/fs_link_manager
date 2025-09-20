"""
FS Link Manager Modern - Modern UI version with card view
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
from typing import List, Optional, Dict, Tuple, Any
from enum import Enum
import json

from PySide6.QtCore import (
    Qt, QMimeData, QSize, Signal, Slot, QRect, QRectF,
    QPoint, QPointF, QPropertyAnimation, QEasingCurve,
    QEvent, QTimer
)
from PySide6.QtGui import (
    QAction, QIcon, QFont, QPainter, QPalette, QColor,
    QPen, QBrush, QPixmap, QImage, QPainterPath,
    QLinearGradient, QRadialGradient, QFontMetrics,
    QImageReader
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem, QLabel, QFileDialog,
    QMessageBox, QMenu, QPushButton, QStyle, QToolBar, QStatusBar,
    QInputDialog, QDialog, QTextEdit, QDialogButtonBox, QSplitter,
    QTableWidget, QTableWidgetItem, QFormLayout,
    QGroupBox, QTabWidget, QListView, QStyledItemDelegate,
    QGraphicsDropShadowEffect, QFrame, QButtonGroup,
    QRadioButton, QComboBox, QCheckBox
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fs_link_manager_modern.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "links.db")


class ViewMode(Enum):
    """View modes for the link list"""
    LIST = "list"
    GRID = "grid"
    COMPACT = "compact"


class Theme(Enum):
    """Application themes"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class LinkRecord:
    """Data model for a file/folder link"""
    def __init__(self, id_: int, name: str, path: str, tags: str, position: int, added_at: str):
        self.id = id_
        self.name = name
        self.path = path
        self.tags = tags or ""
        self.position = position
        self.added_at = added_at
        self._cached_icon = None
        self._cached_thumbnail = None

    def display_text(self) -> str:
        base = self.name if self.name else os.path.basename(self.path) or self.path
        tag_part = f"  [{self.tags}]" if self.tags else ""
        return f"{base}{tag_part}\n{self.path}"

    def get_tags_list(self) -> List[str]:
        """Get tags as a list"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

    def get_file_info(self) -> Dict[str, Any]:
        """Get detailed file information"""
        info = {
            'exists': os.path.exists(self.path),
            'is_dir': os.path.isdir(self.path) if os.path.exists(self.path) else False,
            'size': 0,
            'modified': None,
            'extension': os.path.splitext(self.path)[1].lower()
        }

        if info['exists']:
            try:
                if not info['is_dir']:
                    info['size'] = os.path.getsize(self.path)
                info['modified'] = datetime.fromtimestamp(os.path.getmtime(self.path))
            except:
                pass

        return info


class LinkDatabase:
    """Database manager for links"""
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
        for pos, id_ in enumerate(ordered_ids):
            self.conn.execute("UPDATE links SET position = ? WHERE id = ?;", (pos, id_))
        self.conn.commit()


class FileIconProvider:
    """Provides icons and thumbnails for files"""

    # File type to icon/color mapping
    FILE_TYPE_INFO = {
        # Documents
        '.doc': ('📄', QColor(46, 117, 182)),
        '.docx': ('📄', QColor(46, 117, 182)),
        '.pdf': ('📕', QColor(226, 57, 43)),
        '.txt': ('📝', QColor(100, 100, 100)),
        '.odt': ('📄', QColor(0, 105, 180)),
        '.rtf': ('📄', QColor(46, 117, 182)),

        # Spreadsheets
        '.xls': ('📊', QColor(27, 115, 51)),
        '.xlsx': ('📊', QColor(27, 115, 51)),
        '.csv': ('📊', QColor(100, 100, 100)),
        '.ods': ('📊', QColor(27, 115, 51)),

        # Presentations
        '.ppt': ('📽️', QColor(208, 71, 38)),
        '.pptx': ('📽️', QColor(208, 71, 38)),
        '.odp': ('📽️', QColor(208, 71, 38)),

        # Images
        '.jpg': ('🖼️', QColor(255, 152, 0)),
        '.jpeg': ('🖼️', QColor(255, 152, 0)),
        '.png': ('🖼️', QColor(76, 175, 80)),
        '.gif': ('🖼️', QColor(156, 39, 176)),
        '.bmp': ('🖼️', QColor(96, 125, 139)),
        '.svg': ('🖼️', QColor(255, 87, 34)),
        '.ico': ('🖼️', QColor(33, 150, 243)),
        '.webp': ('🖼️', QColor(0, 188, 212)),

        # Videos
        '.mp4': ('🎬', QColor(255, 87, 34)),
        '.avi': ('🎬', QColor(244, 67, 54)),
        '.mkv': ('🎬', QColor(76, 175, 80)),
        '.mov': ('🎬', QColor(96, 125, 139)),
        '.wmv': ('🎬', QColor(33, 150, 243)),
        '.flv': ('🎬', QColor(255, 152, 0)),
        '.webm': ('🎬', QColor(0, 188, 212)),

        # Audio
        '.mp3': ('🎵', QColor(156, 39, 176)),
        '.wav': ('🎵', QColor(103, 58, 183)),
        '.flac': ('🎵', QColor(63, 81, 181)),
        '.aac': ('🎵', QColor(48, 63, 159)),
        '.ogg': ('🎵', QColor(69, 90, 100)),
        '.wma': ('🎵', QColor(255, 111, 0)),
        '.m4a': ('🎵', QColor(255, 87, 34)),

        # Archives
        '.zip': ('📦', QColor(121, 85, 72)),
        '.rar': ('📦', QColor(78, 52, 46)),
        '.7z': ('📦', QColor(93, 64, 55)),
        '.tar': ('📦', QColor(62, 39, 35)),
        '.gz': ('📦', QColor(109, 76, 65)),
        '.bz2': ('📦', QColor(141, 110, 99)),

        # Programming
        '.py': ('🐍', QColor(55, 118, 171)),
        '.js': ('📜', QColor(240, 219, 79)),
        '.html': ('🌐', QColor(228, 79, 57)),
        '.css': ('🎨', QColor(38, 77, 228)),
        '.cpp': ('💻', QColor(0, 89, 156)),
        '.c': ('💻', QColor(89, 89, 89)),
        '.java': ('☕', QColor(244, 67, 54)),
        '.cs': ('💻', QColor(104, 33, 122)),
        '.php': ('💻', QColor(119, 123, 180)),
        '.rb': ('💎', QColor(176, 18, 10)),
        '.go': ('🔵', QColor(0, 172, 215)),
        '.rs': ('🦀', QColor(222, 165, 132)),
        '.swift': ('🦉', QColor(255, 172, 69)),
        '.kt': ('🟣', QColor(128, 108, 233)),
        '.ts': ('📘', QColor(0, 122, 204)),
        '.json': ('📋', QColor(55, 55, 55)),
        '.xml': ('📄', QColor(255, 152, 0)),
        '.yaml': ('📄', QColor(76, 175, 80)),
        '.yml': ('📄', QColor(76, 175, 80)),
        '.sql': ('🗃️', QColor(255, 111, 0)),
        '.sh': ('🖥️', QColor(76, 175, 80)),
        '.bat': ('🖥️', QColor(33, 150, 243)),
        '.ps1': ('🖥️', QColor(0, 188, 212)),

        # Executables
        '.exe': ('⚙️', QColor(96, 125, 139)),
        '.msi': ('📦', QColor(0, 150, 136)),
        '.app': ('📱', QColor(76, 175, 80)),
        '.dll': ('🔧', QColor(158, 158, 158)),
        '.so': ('🔧', QColor(117, 117, 117)),

        # Others
        '.iso': ('💿', QColor(103, 58, 183)),
        '.dmg': ('💿', QColor(63, 81, 181)),
        '.log': ('📃', QColor(117, 117, 117)),
        '.bak': ('💾', QColor(97, 97, 97)),
        '.tmp': ('⏳', QColor(158, 158, 158))
    }

    @classmethod
    def get_file_icon_info(cls, path: str) -> Tuple[str, QColor]:
        """Get icon and color for a file path"""
        if os.path.isdir(path):
            return ('📁', QColor(255, 193, 7))

        ext = os.path.splitext(path)[1].lower()
        if ext in cls.FILE_TYPE_INFO:
            return cls.FILE_TYPE_INFO[ext]

        return ('📄', QColor(158, 158, 158))

    @classmethod
    def can_generate_thumbnail(cls, path: str) -> bool:
        """Check if we can generate a thumbnail for this file"""
        if not os.path.exists(path) or os.path.isdir(path):
            return False

        ext = os.path.splitext(path)[1].lower()
        supported_formats = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico']
        return ext in supported_formats

    @classmethod
    def generate_thumbnail(cls, path: str, size: QSize) -> Optional[QPixmap]:
        """Generate a thumbnail for an image file"""
        if not cls.can_generate_thumbnail(path):
            return None

        try:
            reader = QImageReader(path)
            reader.setScaledSize(size)
            image = reader.read()
            if not image.isNull():
                return QPixmap.fromImage(image)
        except Exception as e:
            logger.error(f"Failed to generate thumbnail for {path}: {e}")

        return None


class CardItemDelegate(QStyledItemDelegate):
    """Custom delegate for card view rendering"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.card_width = 200
        self.card_height = 220
        self.padding = 16
        self.icon_size = 64
        self.tag_height = 20
        self.selected_scale = 1.02
        self.hover_opacity = 0.95
        self._hover_index = None
        self.is_dark_mode = False

    def paint(self, painter: QPainter, option, index):
        """Paint the card item"""
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

        # Draw card background
        card_path = QPainterPath()
        card_path.addRoundedRect(QRectF(card_rect), 10, 10)

        # Background color based on state and theme
        if self.is_dark_mode:
            if is_selected:
                bg_color = QColor(14, 99, 156)
                painter.setPen(QPen(QColor(17, 119, 187), 2))
            elif is_hover:
                bg_color = QColor(62, 62, 66)
                painter.setPen(QPen(QColor(80, 80, 82), 1))
            else:
                bg_color = QColor(45, 45, 48)
                painter.setPen(QPen(QColor(63, 63, 70), 1))
        else:
            if is_selected:
                bg_color = QColor(66, 165, 245)
                painter.setPen(QPen(QColor(33, 150, 243), 2))
            elif is_hover:
                bg_color = QColor(245, 245, 245)
                painter.setPen(QPen(QColor(200, 200, 200), 1))
            else:
                bg_color = QColor(255, 255, 255)
                painter.setPen(QPen(QColor(220, 220, 220), 1))

        painter.fillPath(card_path, bg_color)
        painter.drawPath(card_path)

        # Content area
        content_rect = card_rect.adjusted(12, 12, -12, -12)

        # Draw icon or thumbnail
        icon_rect = QRect(
            content_rect.x() + (content_rect.width() - self.icon_size) // 2,
            content_rect.y() + 10,
            self.icon_size,
            self.icon_size
        )

        # Try to get thumbnail first
        thumbnail = FileIconProvider.generate_thumbnail(record.path, QSize(self.icon_size, self.icon_size))
        if thumbnail:
            # Draw thumbnail with rounded corners
            thumb_path = QPainterPath()
            thumb_path.addRoundedRect(QRectF(icon_rect), 8, 8)
            painter.setClipPath(thumb_path)
            painter.drawPixmap(icon_rect, thumbnail)
            painter.setClipPath(QPainterPath())
        else:
            # Draw file type icon
            emoji, color = FileIconProvider.get_file_icon_info(record.path)

            # Draw colored circle background
            circle_rect = icon_rect.adjusted(8, 8, -8, -8)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color.lighter(170)))
            painter.drawEllipse(circle_rect)

            # Draw emoji/icon
            font = painter.font()
            font.setPointSize(24)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255) if is_selected else color)
            painter.drawText(circle_rect, Qt.AlignCenter, emoji)

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

        if self.is_dark_mode:
            painter.setPen(QColor(255, 255, 255) if is_selected else QColor(204, 204, 204))
        else:
            painter.setPen(QColor(255, 255, 255) if is_selected else QColor(33, 33, 33))

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
        painter.setPen(QColor(230, 230, 230) if is_selected else QColor(117, 117, 117))

        elided_path = painter.fontMetrics().elidedText(record.path, Qt.ElideMiddle, path_rect.width())
        painter.drawText(path_rect, Qt.AlignHCenter | Qt.AlignTop, elided_path)

        # Draw tags
        if record.tags:
            tags = record.get_tags_list()[:3]  # Show max 3 tags
            tag_y = path_rect.bottom() + 8
            tag_x = content_rect.x() + 4

            tag_font = painter.font()
            tag_font.setPointSize(7)
            painter.setFont(tag_font)

            for tag in tags:
                tag_width = painter.fontMetrics().horizontalAdvance(tag) + 12

                if tag_x + tag_width > content_rect.right() - 4:
                    break

                tag_rect = QRect(tag_x, tag_y, tag_width, 18)

                # Draw tag background
                tag_path = QPainterPath()
                tag_path.addRoundedRect(QRectF(tag_rect), 9, 9)

                tag_color = QColor(66, 165, 245) if is_selected else QColor(158, 158, 158)
                painter.fillPath(tag_path, tag_color.lighter(150))

                # Draw tag text
                painter.setPen(QColor(255, 255, 255) if is_selected else QColor(66, 66, 66))
                painter.drawText(tag_rect, Qt.AlignCenter, tag)

                tag_x += tag_width + 4

        # Draw file info (size/date)
        info = record.get_file_info()
        if info['exists']:
            info_text = ""
            if not info['is_dir'] and info['size'] > 0:
                size_mb = info['size'] / (1024 * 1024)
                if size_mb >= 1:
                    info_text = f"{size_mb:.1f} MB"
                else:
                    size_kb = info['size'] / 1024
                    info_text = f"{size_kb:.0f} KB"

            if info_text:
                info_rect = QRect(
                    content_rect.x(),
                    content_rect.bottom() - 16,
                    content_rect.width(),
                    14
                )

                info_font = painter.font()
                info_font.setPointSize(7)
                painter.setFont(info_font)
                painter.setPen(QColor(200, 200, 200) if is_selected else QColor(158, 158, 158))
                painter.drawText(info_rect, Qt.AlignCenter, info_text)

        painter.restore()

    def sizeHint(self, option, index):
        """Return the size hint for the card"""
        return QSize(self.card_width, self.card_height)


class ListItemDelegate(QStyledItemDelegate):
    """Custom delegate for list view rendering"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_size = 48
        self.item_height = 72
        self.padding = 12
        self.is_dark_mode = False

    def paint(self, painter: QPainter, option, index):
        """Paint the list item"""
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

        # Draw background
        if is_selected:
            painter.fillRect(rect, QColor(66, 165, 245, 50))
            painter.setPen(QPen(QColor(66, 165, 245), 1))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
        elif is_hover:
            painter.fillRect(rect, QColor(0, 0, 0, 10))

        # Icon area
        icon_rect = QRect(
            rect.x() + self.padding,
            rect.y() + (rect.height() - self.icon_size) // 2,
            self.icon_size,
            self.icon_size
        )

        # Try to get thumbnail
        thumbnail = FileIconProvider.generate_thumbnail(record.path, QSize(self.icon_size, self.icon_size))
        if thumbnail:
            # Draw thumbnail
            thumb_path = QPainterPath()
            thumb_path.addRoundedRect(QRectF(icon_rect), 6, 6)
            painter.setClipPath(thumb_path)
            painter.drawPixmap(icon_rect, thumbnail)
            painter.setClipPath(QPainterPath())
        else:
            # Draw file type icon
            emoji, color = FileIconProvider.get_file_icon_info(record.path)

            # Draw colored background
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color.lighter(180)))

            icon_bg_rect = icon_rect.adjusted(4, 4, -4, -4)
            icon_path = QPainterPath()
            icon_path.addRoundedRect(QRectF(icon_bg_rect), 6, 6)
            painter.fillPath(icon_path, color.lighter(180))

            # Draw emoji
            font = painter.font()
            font.setPointSize(18)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))
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
        painter.setPen(QColor(204, 204, 204) if self.is_dark_mode else QColor(33, 33, 33))

        title = record.name or os.path.basename(record.path)
        title_rect = QRect(text_rect.x(), text_rect.y(), text_rect.width(), 20)
        elided_title = painter.fontMetrics().elidedText(title, Qt.ElideRight, title_rect.width())
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_title)

        # Draw path
        path_font = painter.font()
        path_font.setPointSize(8)
        painter.setFont(path_font)
        painter.setPen(QColor(158, 158, 158) if self.is_dark_mode else QColor(117, 117, 117))

        path_rect = QRect(text_rect.x(), title_rect.bottom() + 2, text_rect.width(), 16)
        elided_path = painter.fontMetrics().elidedText(record.path, Qt.ElideMiddle, path_rect.width())
        painter.drawText(path_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_path)

        # Draw tags and info
        if record.tags or True:  # Always show info line
            info_parts = []

            # Add tags
            if record.tags:
                tags = record.get_tags_list()[:3]
                info_parts.extend([f"#{tag}" for tag in tags])

            # Add file info
            info = record.get_file_info()
            if info['exists'] and not info['is_dir'] and info['size'] > 0:
                size_mb = info['size'] / (1024 * 1024)
                if size_mb >= 1:
                    info_parts.append(f"{size_mb:.1f} MB")
                else:
                    size_kb = info['size'] / 1024
                    info_parts.append(f"{size_kb:.0f} KB")

            if info_parts:
                info_font = painter.font()
                info_font.setPointSize(8)
                painter.setFont(info_font)
                painter.setPen(QColor(158, 158, 158))

                info_rect = QRect(text_rect.x(), path_rect.bottom() + 2, text_rect.width(), 14)
                info_text = "  •  ".join(info_parts)
                elided_info = painter.fontMetrics().elidedText(info_text, Qt.ElideRight, info_rect.width())
                painter.drawText(info_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_info)

        painter.restore()

    def sizeHint(self, option, index):
        """Return the size hint for the list item"""
        return QSize(option.rect.width(), self.item_height)


class ModernLinkList(QListView):
    """Modern list view with multiple display modes"""

    linkDropped = Signal(list)  # list of (name, path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListView.SingleSelection)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListView.InternalMove)
        self.setAlternatingRowColors(False)
        self.setUniformItemSizes(False)
        self.setWordWrap(True)

        # View modes
        self._view_mode = ViewMode.LIST
        self._list_delegate = ListItemDelegate(self)
        self._card_delegate = CardItemDelegate(self)

        # Set initial delegate
        self.setItemDelegate(self._list_delegate)

        # Animation
        self._hover_timer = QTimer()
        self._hover_timer.timeout.connect(self._update_hover)

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
        else:  # LIST or COMPACT
            self.setViewMode(QListView.ListMode)
            self.setItemDelegate(self._list_delegate)
            self.setGridSize(QSize())
            self.setFlow(QListView.TopToBottom)
            self.setWrapping(False)
            self.setResizeMode(QListView.Fixed)
            self.setSpacing(2)
            self.setMovement(QListView.Free)

        self.viewport().update()

    def get_view_mode(self) -> ViewMode:
        """Get current view mode"""
        return self._view_mode

    def _update_hover(self):
        """Update hover state"""
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


class ModernMainWindow(QMainWindow):
    """Main window with modern UI"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FS Link Manager - Modern UI")
        self.resize(1000, 700)
        self.db = LinkDatabase()
        self.current_theme = Theme.LIGHT

        # Apply modern style
        self.setStyleSheet(self._get_modern_stylesheet())

        # Create UI
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()

        # Load initial data
        self.reload_list()

    def _get_modern_stylesheet(self) -> str:
        """Get modern stylesheet based on theme"""
        if self.current_theme == Theme.DARK:
            return self._get_dark_stylesheet()
        return self._get_light_stylesheet()

    def _get_light_stylesheet(self) -> str:
        """Get light theme stylesheet"""
        return """
        QMainWindow {
            background-color: #f5f5f5;
        }

        QToolBar {
            background-color: #ffffff;
            border: none;
            border-bottom: 1px solid #e0e0e0;
            padding: 8px;
            spacing: 8px;
        }

        QToolBar QToolButton {
            background-color: transparent;
            border: none;
            border-radius: 6px;
            padding: 8px;
            margin: 4px;
        }

        QToolBar QToolButton:hover {
            background-color: #f0f0f0;
        }

        QToolBar QToolButton:pressed {
            background-color: #e0e0e0;
        }

        QLineEdit {
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 8px 12px;
            background-color: #ffffff;
            font-size: 13px;
        }

        QLineEdit:focus {
            border: 2px solid #42a5f5;
            padding: 7px 11px;
        }

        QPushButton {
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 6px 16px;
            background-color: #ffffff;
            font-size: 13px;
        }

        QPushButton:hover {
            background-color: #f5f5f5;
            border: 1px solid #d0d0d0;
        }

        QPushButton:pressed {
            background-color: #e0e0e0;
        }

        QPushButton#primaryButton {
            background-color: #42a5f5;
            color: white;
            border: none;
        }

        QPushButton#primaryButton:hover {
            background-color: #2196f3;
        }

        QPushButton#primaryButton:pressed {
            background-color: #1976d2;
        }

        QListView {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 8px;
            outline: none;
        }

        QListView::item {
            background-color: transparent;
            border-radius: 6px;
            padding: 4px;
        }

        QListView::item:hover {
            background-color: #f5f5f5;
        }

        QListView::item:selected {
            background-color: #e3f2fd;
        }

        QStatusBar {
            background-color: #ffffff;
            border-top: 1px solid #e0e0e0;
        }

        QMenu {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 4px;
        }

        QMenu::item {
            padding: 8px 24px;
            border-radius: 4px;
        }

        QMenu::item:selected {
            background-color: #f5f5f5;
        }

        QMenu::separator {
            height: 1px;
            background-color: #e0e0e0;
            margin: 4px 12px;
        }
        """

    def _get_dark_stylesheet(self) -> str:
        """Get dark theme stylesheet"""
        return """
        QMainWindow {
            background-color: #1e1e1e;
        }

        QToolBar {
            background-color: #2d2d30;
            border: none;
            border-bottom: 1px solid #3f3f46;
            padding: 8px;
            spacing: 8px;
        }

        QToolBar QToolButton {
            background-color: transparent;
            border: none;
            border-radius: 6px;
            padding: 8px;
            margin: 4px;
            color: #cccccc;
        }

        QToolBar QToolButton:hover {
            background-color: #3e3e42;
        }

        QToolBar QToolButton:pressed {
            background-color: #505052;
        }

        QLineEdit {
            border: 1px solid #3f3f46;
            border-radius: 6px;
            padding: 8px 12px;
            background-color: #2d2d30;
            color: #cccccc;
            font-size: 13px;
        }

        QLineEdit:focus {
            border: 2px solid #0e639c;
            padding: 7px 11px;
        }

        QPushButton {
            border: 1px solid #3f3f46;
            border-radius: 6px;
            padding: 6px 16px;
            background-color: #2d2d30;
            color: #cccccc;
            font-size: 13px;
        }

        QPushButton:hover {
            background-color: #3e3e42;
            border: 1px solid #505052;
        }

        QPushButton:pressed {
            background-color: #505052;
        }

        QPushButton#primaryButton {
            background-color: #0e639c;
            color: white;
            border: none;
        }

        QPushButton#primaryButton:hover {
            background-color: #1177bb;
        }

        QPushButton#primaryButton:pressed {
            background-color: #0d5689;
        }

        QListView {
            background-color: #252526;
            border: 1px solid #3f3f46;
            border-radius: 8px;
            padding: 8px;
            outline: none;
        }

        QListView::item {
            background-color: transparent;
            border-radius: 6px;
            padding: 4px;
            color: #cccccc;
        }

        QListView::item:hover {
            background-color: #2d2d30;
        }

        QListView::item:selected {
            background-color: #094771;
        }

        QStatusBar {
            background-color: #2d2d30;
            border-top: 1px solid #3f3f46;
            color: #cccccc;
        }

        QMenu {
            background-color: #252526;
            border: 1px solid #3f3f46;
            border-radius: 8px;
            padding: 4px;
            color: #cccccc;
        }

        QMenu::item {
            padding: 8px 24px;
            border-radius: 4px;
        }

        QMenu::item:selected {
            background-color: #094771;
        }

        QMenu::separator {
            height: 1px;
            background-color: #3f3f46;
            margin: 4px 12px;
        }

        QComboBox {
            border: 1px solid #3f3f46;
            border-radius: 6px;
            padding: 4px 8px;
            background-color: #2d2d30;
            color: #cccccc;
        }

        QComboBox:hover {
            border: 1px solid #505052;
        }

        QComboBox::drop-down {
            border: none;
        }

        QComboBox QAbstractItemView {
            background-color: #252526;
            border: 1px solid #3f3f46;
            color: #cccccc;
            selection-background-color: #094771;
        }

        QLabel {
            color: #cccccc;
        }
        """

    def _create_toolbar(self):
        """Create modern toolbar"""
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # View mode switcher
        view_widget = QWidget()
        view_layout = QHBoxLayout(view_widget)
        view_layout.setContentsMargins(4, 0, 4, 0)
        view_layout.setSpacing(4)

        view_label = QLabel("表示:")
        view_layout.addWidget(view_label)

        self.view_combo = QComboBox()
        self.view_combo.addItems(["リスト", "グリッド", "コンパクト"])
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
        import_act.setToolTip("JSONファイルからインポート")
        import_act.triggered.connect(self.import_from_file)
        toolbar.addAction(import_act)

        export_act = QAction(self.style().standardIcon(QStyle.SP_ArrowUp), "エクスポート", self)
        export_act.setToolTip("JSONファイルにエクスポート")
        export_act.triggered.connect(self.export_to_file)
        toolbar.addAction(export_act)

        toolbar.addSeparator()

        # Item operations
        open_act = QAction(self.style().standardIcon(QStyle.SP_DirOpenIcon), "開く", self)
        open_act.setToolTip("エクスプローラで開く")
        open_act.triggered.connect(self.open_selected)
        toolbar.addAction(open_act)

        edit_act = QAction(self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "編集", self)
        edit_act.setToolTip("選択したアイテムを編集")
        edit_act.triggered.connect(self.edit_selected)
        toolbar.addAction(edit_act)

        delete_act = QAction(self.style().standardIcon(QStyle.SP_TrashIcon), "削除", self)
        delete_act.setToolTip("選択したアイテムを削除")
        delete_act.triggered.connect(self.delete_selected)
        toolbar.addAction(delete_act)

        # Spacer
        spacer = QWidget()
        from PySide6.QtWidgets import QSizePolicy
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        # Theme switcher
        theme_widget = QWidget()
        theme_layout = QHBoxLayout(theme_widget)
        theme_layout.setContentsMargins(4, 0, 4, 0)

        theme_label = QLabel("テーマ:")
        theme_layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["ライト", "ダーク"])
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

        # Search bar with icon
        search_container = QFrame()
        search_container.setObjectName("searchContainer")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 検索（名前 / パス / タグ）")
        self.search.textChanged.connect(self.reload_list)
        search_layout.addWidget(self.search)

        layout.addWidget(search_container)

        # List view
        self.list_view = ModernLinkList()
        self.list_view.linkDropped.connect(self.on_links_dropped)
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self.open_context_menu)
        self.list_view.doubleClicked.connect(self.on_item_double_clicked)

        # Create shadow effect for list view
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        self.list_view.setGraphicsEffect(shadow)

        layout.addWidget(self.list_view, 1)

    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _on_view_mode_changed(self, index):
        """Handle view mode change"""
        modes = [ViewMode.LIST, ViewMode.GRID, ViewMode.COMPACT]
        self.list_view.set_view_mode(modes[index])
        self.reload_list()

    def _on_theme_changed(self, index):
        """Handle theme change"""
        themes = [Theme.LIGHT, Theme.DARK]
        self.current_theme = themes[index]
        self.setStyleSheet(self._get_modern_stylesheet())

        # Update delegates for dark mode
        if hasattr(self, 'list_view'):
            self.list_view._card_delegate.is_dark_mode = (self.current_theme == Theme.DARK)
            self.list_view._list_delegate.is_dark_mode = (self.current_theme == Theme.DARK)
            self.list_view.viewport().update()

    def reload_list(self):
        """Reload the list with data"""
        from PySide6.QtCore import QAbstractListModel, QModelIndex

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

            # Add extension tag
            ext = os.path.splitext(path)[1].lower()
            if ext:
                emoji, color = FileIconProvider.get_file_icon_info(path)
                ext_tag = ext[1:].upper()
                tags.append(ext_tag)

            # Add folder tag if directory
            if os.path.isdir(path):
                tags.append("フォルダ")

            # Add to database
            self.db.add_link(
                name=name,
                path=path,
                tags=", ".join(tags) if tags else ""
            )

        self.reload_list()
        self.status_bar.showMessage(f"{len(pairs)} 件のアイテムを追加しました")

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

        self.db.delete_link(id_)
        self.reload_list()
        self.status_bar.showMessage("アイテムを削除しました")

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
            self.status_bar.showMessage("エクスポートしました")
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
            self.status_bar.showMessage(f"{count} 件をインポートしました")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"インポートに失敗: {e}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FS Link Manager Modern")

    # Set application font
    font = app.font()
    font.setFamily("Segoe UI, Yu Gothic UI, Meiryo, sans-serif")
    app.setFont(font)

    win = ModernMainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()