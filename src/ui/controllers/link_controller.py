"""Link operations controller for FS Link Manager"""

import os
from typing import List, Tuple
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from ...core import LinkDatabase, LinkRecord, LinkManager
from ...i18n import tr
from ...utils import handle_errors, DatabaseError


class LinkController(QObject):
    """リンク操作のビジネスロジックを管理"""

    # シグナル
    links_updated = Signal()
    status_message = Signal(str, int)  # (message, timeout_ms)

    def __init__(self, db: LinkDatabase, manager: LinkManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.manager = manager

    def add_links_from_dialog(self, parent_widget) -> bool:
        """ダイアログからリンクを追加"""
        dlg = QFileDialog(parent_widget, tr("dialogs.select_link_target"))
        dlg.setFileMode(QFileDialog.ExistingFiles)
        if dlg.exec():
            paths = dlg.selectedFiles()
            pairs = [(os.path.basename(p) or p, p) for p in paths]
            self.add_links_from_drops(pairs)
            return True
        return False

    @handle_errors()
    def add_links_from_drops(self, pairs: List[Tuple[str, str]]):
        """ドロップされたリンクを追加"""
        for name, path in pairs:
            # Auto-generate tags
            tags = []
            ext = os.path.splitext(path)[1].lower()
            if ext:
                tags.append(ext[1:].upper())
            if os.path.isdir(path):
                tags.append(tr("tags.folder"))

            self.db.add_link(
                name=name,
                path=path,
                tags=", ".join(tags) if tags else ""
            )

        self.links_updated.emit()
        self.status_message.emit(
            tr("status.items_added", count=len(pairs)),
            3000
        )

    @handle_errors(return_on_error=False)
    def edit_link(self, record: LinkRecord, parent_widget) -> bool:
        """リンクを編集"""
        name, ok1 = QInputDialog.getText(
            parent_widget,
            tr("dialogs.edit_name"),
            tr("dialogs.display_name"),
            text=record.name
        )
        if not ok1:
            return False

        tags, ok2 = QInputDialog.getText(
            parent_widget,
            tr("dialogs.edit_tags"),
            tr("dialogs.tags_hint"),
            text=record.tags
        )
        if not ok2:
            return False

        self.db.update_link(record.id, name=name, tags=tags)
        self.links_updated.emit()
        return True

    @handle_errors(return_on_error=False)
    def delete_link(self, record_id: int, parent_widget) -> bool:
        """リンクを削除（確認ダイアログ付き）"""
        reply = QMessageBox.question(
            parent_widget,
            tr("dialogs.confirm"),
            tr("dialogs.delete_confirm"),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_link(record_id)
            self.links_updated.emit()
            self.status_message.emit(tr("status.item_deleted"), 2000)
            return True
        return False

    @handle_errors()
    def open_link(self, path: str):
        """リンクをエクスプローラーで開く"""
        self.manager.open_in_explorer(path)

    @handle_errors(return_on_error=[])
    def search_links(self, query: str) -> List[LinkRecord]:
        """リンクを検索"""
        return self.db.list_links(query)
