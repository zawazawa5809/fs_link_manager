"""Import/Export controller for FS Link Manager"""

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog

from ...core import LinkManager
from ...i18n import tr
from ...utils import handle_errors, FileOperationError


class ImportExportController(QObject):
    """インポート/エクスポート処理を管理"""

    # シグナル
    import_completed = Signal(int)  # imported count
    export_completed = Signal()
    status_message = Signal(str, int)  # (message, timeout_ms)

    def __init__(self, manager: LinkManager, parent=None):
        super().__init__(parent)
        self.manager = manager

    @handle_errors(return_on_error=False)
    def import_from_file(self, parent_widget) -> bool:
        """ファイルからリンクをインポート"""
        path, _ = QFileDialog.getOpenFileName(
            parent_widget,
            tr("dialogs.import_file_select"),
            "",
            "JSON files (*.json)"
        )
        if not path:
            return False

        count = self.manager.import_links(path)
        if count is None:
            raise FileOperationError(tr("dialogs.import_error"))

        self.import_completed.emit(count)
        self.status_message.emit(
            tr("status.links_imported", count=count),
            3000
        )
        return True

    @handle_errors(return_on_error=False)
    def export_to_file(self, parent_widget) -> bool:
        """リンクをファイルにエクスポート"""
        path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            tr("dialogs.export_file_select"),
            "",
            "JSON files (*.json)"
        )
        if not path:
            return False

        self.manager.export_links(path)
        self.export_completed.emit()
        self.status_message.emit(
            tr("status.export_completed"),
            3000
        )
        return True
