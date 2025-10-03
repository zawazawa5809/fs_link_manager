"""Link list model for FS Link Manager"""

from PySide6.QtCore import Qt, QModelIndex, QAbstractListModel
from typing import List

from ...core.models import LinkRecord


class LinkListModel(QAbstractListModel):
    """Model for link list view"""

    def __init__(self, records: List[LinkRecord] = None):
        super().__init__()
        self.records = records or []

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

    def update_records(self, records: List[LinkRecord]):
        """Update the model with new records"""
        self.beginResetModel()
        self.records = records
        self.endResetModel()
