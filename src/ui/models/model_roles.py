"""Custom model roles for LinkListModel

Defines semantic constants for Qt.UserRole values to improve code clarity.
"""

from PySide6.QtCore import Qt


class LinkModelRoles:
    """Custom data roles for LinkListModel.

    Provides semantic naming for Qt.UserRole-based data access.
    """
    # Record ID (int)
    RecordId = Qt.UserRole

    # Full LinkRecord object
    RecordData = Qt.UserRole + 1
