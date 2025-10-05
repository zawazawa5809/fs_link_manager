"""Link list widget for FS Link Manager"""

import os
from enum import Enum
from typing import List, Tuple

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QListView

from .link_item import ThemedListDelegate, ThemedCardDelegate


class ViewMode(Enum):
    """View modes for the link list"""
    LIST = "list"
    GRID = "grid"


class LinkList(QListView):
    """Custom list view for displaying links with drag and drop support"""

    linkDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListView.SingleSelection)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListView.DragDrop)
        self.setAlternatingRowColors(False)
        self.setUniformItemSizes(False)

        # View modes
        self._view_mode = ViewMode.LIST
        self._list_delegate = ThemedListDelegate(self)
        self._card_delegate = ThemedCardDelegate(self)

        # Set initial delegate
        self.setItemDelegate(self._list_delegate)

    def set_view_mode(self, mode: ViewMode):
        """Change the view mode between list and grid"""
        self._view_mode = mode

        if mode == ViewMode.GRID:
            self.setViewMode(QListView.IconMode)
            self.setItemDelegate(self._card_delegate)
            self.setGridSize(QSize(self._card_delegate.card_width,
                                   self._card_delegate.card_height))
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

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events"""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        """Handle drag move events"""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handle drop events for external files"""
        # Handle URL drops (files/folders)
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

        # Handle text drops (paths)
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

        # Default to parent implementation for internal moves
        super().dropEvent(event)