"""Main window implementation for FS Link Manager"""

import os
from typing import List, Optional
from pathlib import Path

from PySide6.QtCore import Qt, Slot, QModelIndex, QAbstractListModel
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox, QMenu, QToolBar, QStatusBar,
    QInputDialog, QSizePolicy, QStyle
)

from ..core import LinkDatabase, LinkRecord, LinkManager
from ..themes import ThemeManager
from .widgets import LinkList
from .widgets.link_list import ViewMode
from .widgets.factory import WidgetFactory


class LinkListModel(QAbstractListModel):
    """Model for link list view"""

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


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FS Link Manager")
        self.resize(1100, 750)

        # Get theme manager instance (already initialized in main.py)
        self.theme_manager = ThemeManager()

        # Initialize database and manager
        self.db = LinkDatabase()
        self.manager = LinkManager()

        # Create UI
        self._create_ui()

        # Load initial data
        self.reload_list()

        # Connect theme change signal
        self.theme_manager.theme_changed.connect(self.on_theme_changed)

    def _create_ui(self):
        """Create the user interface"""
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()

    def _create_toolbar(self):
        """Create toolbar"""
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

        self.view_combo = WidgetFactory.create_combo_box(["リスト", "グリッド"])
        self.view_combo.currentIndexChanged.connect(self._on_view_mode_changed)
        view_layout.addWidget(self.view_combo)

        toolbar.addWidget(view_widget)
        toolbar.addSeparator()

        # File operations
        add_act = QAction(
            self.style().standardIcon(QStyle.SP_FileDialogNewFolder),
            "追加", self
        )
        add_act.setToolTip("ファイルまたはフォルダを追加")
        add_act.triggered.connect(self.add_link_dialog)
        toolbar.addAction(add_act)

        import_act = QAction(
            self.style().standardIcon(QStyle.SP_ArrowDown),
            "インポート", self
        )
        import_act.triggered.connect(self.import_from_file)
        toolbar.addAction(import_act)

        export_act = QAction(
            self.style().standardIcon(QStyle.SP_ArrowUp),
            "エクスポート", self
        )
        export_act.triggered.connect(self.export_to_file)
        toolbar.addAction(export_act)

        toolbar.addSeparator()

        # Item operations
        open_act = QAction(
            self.style().standardIcon(QStyle.SP_DirOpenIcon),
            "開く", self
        )
        open_act.triggered.connect(self.open_selected)
        toolbar.addAction(open_act)

        edit_act = QAction(
            self.style().standardIcon(QStyle.SP_FileDialogDetailedView),
            "編集", self
        )
        edit_act.triggered.connect(self.edit_selected)
        toolbar.addAction(edit_act)

        delete_act = QAction(
            self.style().standardIcon(QStyle.SP_TrashIcon),
            "削除", self
        )
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
        self.search = WidgetFactory.create_input_field(
            "検索（名前 / パス / タグ）", "search"
        )
        self.search.textChanged.connect(self.reload_list)
        layout.addWidget(self.search)

        # List view
        self.list_view = LinkList()
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
        if 0 <= index < len(self.theme_keys):
            theme_key = self.theme_keys[index]
            self.theme_manager.apply_theme(theme_key)

    def on_theme_changed(self, theme_name: str):
        """Handle theme change signal"""
        self.status_bar.showMessage(f"テーマを変更しました: {theme_name}", 2000)

    def reload_list(self):
        """Reload the list with data"""
        query = self.search.text()
        records = self.db.list_links(query)

        model = LinkListModel(records)
        self.list_view.setModel(model)

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
            self.manager.open_in_explorer(record.path)

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

        name, ok1 = QInputDialog.getText(
            self, "名前を編集", "表示名:", text=rec.name
        )
        if not ok1:
            return
        tags, ok2 = QInputDialog.getText(
            self, "タグを編集", "カンマ区切りタグ:", text=rec.tags
        )
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
            self.manager.open_in_explorer(rec.path)

    def open_context_menu(self, pos):
        """Show context menu"""
        index = self.list_view.indexAt(pos)
        menu = QMenu(self)

        if index.isValid():
            open_act = menu.addAction("開く")
            open_act.triggered.connect(self.open_selected)

            edit_act = menu.addAction("編集")
            edit_act.triggered.connect(self.edit_selected)

            menu.addSeparator()

            delete_act = menu.addAction("削除")
            delete_act.triggered.connect(self.delete_selected)
        else:
            add_act = menu.addAction("追加...")
            add_act.triggered.connect(self.add_link_dialog)

        menu.exec(self.list_view.mapToGlobal(pos))

    def import_from_file(self):
        """Import links from JSON file"""
        path, _ = QFileDialog.getOpenFileName(
            self, "インポートファイルを選択", "", "JSON files (*.json)"
        )
        if not path:
            return

        try:
            count = self.manager.import_links(path)
            self.reload_list()
            self.status_bar.showMessage(f"{count} 件のリンクをインポートしました", 3000)

        except Exception as e:
            QMessageBox.warning(self, "インポートエラー", str(e))

    def export_to_file(self):
        """Export links to JSON file"""
        path, _ = QFileDialog.getSaveFileName(
            self, "エクスポート先を選択", "", "JSON files (*.json)"
        )
        if not path:
            return

        try:
            self.manager.export_links(path)
            self.status_bar.showMessage("エクスポートが完了しました", 3000)

        except Exception as e:
            QMessageBox.warning(self, "エクスポートエラー", str(e))

    def closeEvent(self, event):
        """Handle window close event"""
        self.db.close()
        event.accept()