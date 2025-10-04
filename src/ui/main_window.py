"""Main window implementation for FS Link Manager"""

from typing import Optional
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenu, QToolBar, QStatusBar, QSizePolicy, QStyle
)

from ..core import LinkDatabase, LinkRecord, LinkManager, SettingsManager
from ..themes import ThemeManager
from ..i18n import tr
from .widgets import LinkList
from .widgets.link_list import ViewMode
from .widgets.factory import WidgetFactory
from .models import LinkListModel
from .controllers import LinkController, ImportExportController
from .dialogs import SettingsDialog


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("app.title"))
        self.resize(1100, 750)

        # Get manager instances
        self.theme_manager = ThemeManager()
        self.settings_manager = SettingsManager()

        # Initialize database and manager
        self.db = LinkDatabase()
        self.manager = LinkManager()

        # Initialize controllers
        self.link_controller = LinkController(self.db, self.manager, self)
        self.import_export_controller = ImportExportController(self.manager, self)

        # Initialize model
        self.model = LinkListModel()

        # Create UI
        self._create_ui()

        # Connect controller signals
        self._connect_controller_signals()

        # Load initial data
        self.reload_list()

        # Connect manager signals
        self.theme_manager.theme_changed.connect(self.on_theme_changed)
        self.settings_manager.font_settings_changed.connect(self._on_font_settings_changed)

    def _create_ui(self):
        """Create the user interface"""
        self._create_menu_bar()
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()

    def _connect_controller_signals(self):
        """Connect controller signals to UI handlers"""
        self.link_controller.links_updated.connect(self.reload_list)
        self.link_controller.status_message.connect(self._show_status_message)
        self.import_export_controller.import_completed.connect(lambda c: self.reload_list())
        self.import_export_controller.export_completed.connect(lambda: None)
        self.import_export_controller.status_message.connect(self._show_status_message)

    def _create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # ファイルメニュー
        file_menu = menubar.addMenu(tr("menu.file"))

        add_action = QAction(tr("menu.add_link"), self)
        add_action.setShortcut("Ctrl+N")
        add_action.triggered.connect(self.add_link_dialog)
        file_menu.addAction(add_action)

        file_menu.addSeparator()

        import_action = QAction(tr("menu.import"), self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self.import_from_file)
        file_menu.addAction(import_action)

        export_action = QAction(tr("menu.export"), self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_to_file)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction(tr("menu.exit"), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 編集メニュー
        edit_menu = menubar.addMenu(tr("menu.edit"))

        edit_action = QAction(tr("menu.edit_link"), self)
        edit_action.triggered.connect(self.edit_selected)
        edit_menu.addAction(edit_action)

        delete_action = QAction(tr("menu.delete_link"), self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self.delete_selected)
        edit_menu.addAction(delete_action)

        # 表示メニュー
        view_menu = menubar.addMenu(tr("menu.view"))

        # 表示モード
        list_action = QAction(tr("menu.list_view"), self)
        list_action.setShortcut("Ctrl+1")
        list_action.triggered.connect(lambda: self._switch_view_mode(0))
        view_menu.addAction(list_action)

        grid_action = QAction(tr("menu.grid_view"), self)
        grid_action.setShortcut("Ctrl+2")
        grid_action.triggered.connect(lambda: self._switch_view_mode(1))
        view_menu.addAction(grid_action)

        view_menu.addSeparator()

        # テーマサブメニュー
        theme_menu = view_menu.addMenu(tr("menu.theme"))
        available_themes = self.theme_manager.get_available_themes()
        for theme_key in available_themes:
            display_name = tr(f"themes.{theme_key}")
            theme_action = QAction(display_name, self)
            theme_action.triggered.connect(lambda checked, t=theme_key: self._apply_theme_from_menu(t))
            theme_menu.addAction(theme_action)

        # 設定メニュー
        settings_menu = menubar.addMenu(tr("menu.settings"))

        settings_action = QAction(tr("menu.preferences"), self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(settings_action)

    def _create_toolbar(self):
        """Create toolbar"""
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # File operations
        add_act = QAction(
            self.style().standardIcon(QStyle.SP_FileDialogNewFolder),
            tr("toolbar.add_tooltip"), self
        )
        add_act.setToolTip(tr("toolbar.add_tooltip"))
        add_act.triggered.connect(self.add_link_dialog)
        toolbar.addAction(add_act)

        import_act = QAction(
            self.style().standardIcon(QStyle.SP_ArrowDown),
            tr("toolbar.import"), self
        )
        import_act.triggered.connect(self.import_from_file)
        toolbar.addAction(import_act)

        export_act = QAction(
            self.style().standardIcon(QStyle.SP_ArrowUp),
            tr("toolbar.export"), self
        )
        export_act.triggered.connect(self.export_to_file)
        toolbar.addAction(export_act)

        toolbar.addSeparator()

        # Item operations
        open_act = QAction(
            self.style().standardIcon(QStyle.SP_DirOpenIcon),
            tr("toolbar.open"), self
        )
        open_act.triggered.connect(self.open_selected)
        toolbar.addAction(open_act)

        edit_act = QAction(
            self.style().standardIcon(QStyle.SP_FileDialogDetailedView),
            tr("toolbar.edit"), self
        )
        edit_act.triggered.connect(self.edit_selected)
        toolbar.addAction(edit_act)

        delete_act = QAction(
            self.style().standardIcon(QStyle.SP_TrashIcon),
            tr("toolbar.delete"), self
        )
        delete_act.triggered.connect(self.delete_selected)
        toolbar.addAction(delete_act)

    def _create_central_widget(self):
        """Create central widget"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Search bar
        self.search = WidgetFactory.create_input_field(
            tr("search.placeholder"), "search"
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

    def _switch_view_mode(self, index):
        """Switch view mode from menu"""
        modes = [ViewMode.LIST, ViewMode.GRID]
        self.list_view.set_view_mode(modes[index])
        self.reload_list()

    def _apply_theme_from_menu(self, theme_key: str):
        """Apply theme from menu and save to settings"""
        self.settings_manager.settings.theme = theme_key
        self.settings_manager.save_settings()
        self.theme_manager.apply_theme(theme_key)

    def on_theme_changed(self, theme_name: str):
        """Handle theme change signal"""
        self.status_bar.showMessage(tr("status.theme_changed", theme=theme_name), 2000)

    def _on_font_settings_changed(self):
        """Handle font settings change"""
        settings = self.settings_manager.settings
        self.theme_manager.apply_custom_font_size(settings.font_size, settings.font_scale)

    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self)
        dialog.settings_applied.connect(self._on_settings_applied)
        dialog.exec()

    def _on_settings_applied(self):
        """Handle settings applied"""
        self.status_bar.showMessage(tr("status.settings_applied"), 2000)

    def _show_status_message(self, message: str, timeout_ms: int):
        """Show status message"""
        self.status_bar.showMessage(message, timeout_ms)

    def reload_list(self):
        """Reload the list with data"""
        query = self.search.text()
        records = self.link_controller.search_links(query)

        self.model.update_records(records)
        self.list_view.setModel(self.model)

        self.status_bar.showMessage(tr("status.items_count", count=len(records)))

    def current_record_id(self) -> Optional[int]:
        """Get current selected record ID"""
        index = self.list_view.currentIndex()
        if not index.isValid():
            return None
        return index.data(Qt.UserRole)

    def get_record(self, id_: int) -> Optional[LinkRecord]:
        """Get record by ID (optimized)"""
        return self.db.get_link_by_id(id_)

    @Slot(list)
    def on_links_dropped(self, pairs):
        """Handle dropped links"""
        self.link_controller.add_links_from_drops(pairs)

    def on_item_double_clicked(self, index):
        """Handle double click on item"""
        if not index.isValid():
            return

        record = index.data(Qt.UserRole + 1)
        if record:
            self.link_controller.open_link(record.path)

    def add_link_dialog(self):
        """Show dialog to add links"""
        self.link_controller.add_links_from_dialog(self)

    def edit_selected(self):
        """Edit selected item"""
        id_ = self.current_record_id()
        if id_ is None:
            return
        rec = self.get_record(id_)
        if rec:
            self.link_controller.edit_link(rec, self)

    def delete_selected(self):
        """Delete selected item"""
        id_ = self.current_record_id()
        if id_ is None:
            return
        self.link_controller.delete_link(id_, self)

    def open_selected(self):
        """Open selected item"""
        id_ = self.current_record_id()
        if id_ is None:
            return
        rec = self.get_record(id_)
        if rec:
            self.link_controller.open_link(rec.path)

    def open_context_menu(self, pos):
        """Show context menu"""
        index = self.list_view.indexAt(pos)
        menu = QMenu(self)

        if index.isValid():
            open_act = menu.addAction(tr("context_menu.open"))
            open_act.triggered.connect(self.open_selected)

            edit_act = menu.addAction(tr("context_menu.edit"))
            edit_act.triggered.connect(self.edit_selected)

            menu.addSeparator()

            delete_act = menu.addAction(tr("context_menu.delete"))
            delete_act.triggered.connect(self.delete_selected)
        else:
            add_act = menu.addAction(tr("context_menu.add"))
            add_act.triggered.connect(self.add_link_dialog)

        menu.exec(self.list_view.mapToGlobal(pos))

    def import_from_file(self):
        """Import links from JSON file"""
        self.import_export_controller.import_from_file(self)

    def export_to_file(self):
        """Export links to JSON file"""
        self.import_export_controller.export_to_file(self)

    def closeEvent(self, event):
        """Handle window close event with safe resource cleanup"""
        import logging
        logger = logging.getLogger(__name__)

        try:
            # データベース接続を安全にクローズ
            if hasattr(self, 'db') and self.db:
                try:
                    self.db.close()
                except Exception as e:
                    logger.warning(f"Error closing database: {e}")

            # マネージャーリソースをクローズ
            if hasattr(self, 'manager') and self.manager:
                try:
                    self.manager.close()
                except Exception as e:
                    logger.warning(f"Error closing manager: {e}")

            event.accept()
        except Exception as e:
            logger.error(f"Error in closeEvent: {e}", exc_info=True)
            event.accept()  # エラーでも確実にクローズ