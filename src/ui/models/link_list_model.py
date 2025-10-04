"""Link list model for FS Link Manager"""

from PySide6.QtCore import Qt, QModelIndex, QAbstractListModel
from typing import List, Any, Optional

from ...core.models import LinkRecord
from .model_roles import LinkModelRoles


class LinkListModel(QAbstractListModel):
    """Model for link list view.

    Provides Qt model interface for displaying LinkRecord data
    with support for custom data roles.
    """

    def __init__(self, records: Optional[List[LinkRecord]] = None) -> None:
        """Initialize model with optional initial data.

        Args:
            records: Optional list of LinkRecord objects
        """
        super().__init__()
        self.records = records or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of rows in the model.

        Args:
            parent: Parent index (unused for list models)

        Returns:
            Number of link records
        """
        return len(self.records)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Return data for the given index and role.

        Args:
            index: Model index
            role: Data role (DisplayRole, RecordId, RecordData)

        Returns:
            Requested data or None if invalid
        """
        if not index.isValid():
            return None

        record = self.records[index.row()]

        if role == Qt.DisplayRole:
            return record.display_text()
        elif role == LinkModelRoles.RecordId:
            return record.id
        elif role == LinkModelRoles.RecordData:
            return record

        return None

    def update_records(self, records: List[LinkRecord]) -> None:
        """Update the model with new records.

        Args:
            records: New list of LinkRecord objects

        Note:
            Uses beginResetModel/endResetModel for full refresh.
            For incremental updates, use insert/remove methods.
        """
        self.beginResetModel()
        self.records = records
        self.endResetModel()

    def add_record(self, record: LinkRecord) -> None:
        """Add a single record to the model.

        Args:
            record: LinkRecord to add

        Note:
            Appends to the end of the list with proper notifications.
        """
        position = len(self.records)
        self.beginInsertRows(QModelIndex(), position, position)
        self.records.append(record)
        self.endInsertRows()

    def remove_record_by_id(self, record_id: int) -> bool:
        """Remove a record by its ID.

        Args:
            record_id: ID of the record to remove

        Returns:
            True if record was found and removed, False otherwise
        """
        for i, record in enumerate(self.records):
            if record.id == record_id:
                self.beginRemoveRows(QModelIndex(), i, i)
                del self.records[i]
                self.endRemoveRows()
                return True
        return False

    def update_record_by_id(self, record_id: int, updated_record: LinkRecord) -> bool:
        """Update a specific record by its ID.

        Args:
            record_id: ID of the record to update
            updated_record: New record data

        Returns:
            True if record was found and updated, False otherwise
        """
        for i, record in enumerate(self.records):
            if record.id == record_id:
                self.records[i] = updated_record
                index = self.index(i, 0)
                self.dataChanged.emit(index, index, [Qt.DisplayRole, LinkModelRoles.RecordData])
                return True
        return False
