"""Link item delegates for different view modes"""

import os
from PySide6.QtCore import Qt, QSize, QRect, QRectF
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath, QPalette, QFont
)
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QApplication

from ...themes.manager import ThemeManager
from ...themes.constants import VisualConstants as VC, FileTypeIcons as FI
from ...core import SettingsManager


class ThemedListDelegate(QStyledItemDelegate):
    """Theme-aware list view delegate"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = ThemeManager()
        self.settings_manager = SettingsManager()
        self.item_height = self.settings_manager.settings.list_item_height
        self.padding = VC.LIST_PADDING
        self.icon_size = VC.LIST_ICON_SIZE

        # Connect to settings changes for live updates
        self.settings_manager.font_settings_changed.connect(self._on_font_settings_changed)
        self.settings_manager.view_settings_changed.connect(self._on_view_settings_changed)

    def _on_font_settings_changed(self):
        """Handle font settings change - trigger repaint"""
        if self.parent():
            self.parent().viewport().update()

    def _on_view_settings_changed(self):
        """Handle view settings change - update item height"""
        self.item_height = self.settings_manager.settings.list_item_height
        if self.parent():
            self.parent().viewport().update()

    def _get_contrast_text_color(self, palette, is_selected: bool) -> QColor:
        """選択状態に応じて適切なコントラストのテキスト色を取得"""
        if is_selected:
            # テーマで定義された選択時のテキスト色を使用
            selection_color = self.theme_manager.get_color('selection_text')
            # フォールバック: 空の色（黒）の場合は白を使用
            if not selection_color.isValid() or selection_color.name() == '#000000':
                return QColor('#ffffff')
            return selection_color
        else:
            return palette.color(QPalette.WindowText)

    def _get_scaled_font_size(self, base_size: int) -> int:
        """Get font size scaled by global settings"""
        global_size = self.settings_manager.get_effective_font_size()
        # Scale proportionally: base 13px is the reference
        return int(base_size * (global_size / 13.0))

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
            # テーマで定義された選択背景色を使用
            selection_bg = self.theme_manager.get_color('selection_background')
            # フォールバック: 無効な色の場合はパレットのハイライト色を使用
            if not selection_bg.isValid() or selection_bg.name() == '#000000':
                selection_bg = palette.color(QPalette.Highlight)
            painter.fillRect(rect, selection_bg)
            painter.setPen(QPen(selection_bg.darker(110), 1))
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
        if record.custom_icon:
            # カスタムアイコンが設定されている場合はそれを使用
            emoji = record.custom_icon
            icon_color = self.theme_manager.get_color('primary')
        elif os.path.isdir(record.path):
            emoji = FI.FOLDER
            icon_color = self.theme_manager.get_color('primary')
        else:
            emoji = FI.FILE
            icon_color = palette.color(QPalette.ButtonText)

        # Draw icon background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(icon_color.lighter(VC.ICON_BG_LIGHTNESS)))
        icon_bg_rect = icon_rect.adjusted(4, 4, -4, -4)
        painter.drawRoundedRect(icon_bg_rect, VC.BORDER_RADIUS_SMALL, VC.BORDER_RADIUS_SMALL)

        # Draw emoji
        font = painter.font()
        font.setPointSize(self._get_scaled_font_size(VC.FONT_ICON_LIST))
        painter.setFont(font)
        text_color = self._get_contrast_text_color(palette, is_selected)
        painter.setPen(text_color)
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
        title_font.setPointSize(self._get_scaled_font_size(VC.FONT_TITLE))
        title_font.setWeight(QFont.Weight.DemiBold)  # SemiBold (600)
        painter.setFont(title_font)
        painter.setPen(text_color)

        title = record.name or os.path.basename(record.path)
        title_rect = QRect(text_rect.x(), text_rect.y(), text_rect.width(), 24)
        elided_title = painter.fontMetrics().elidedText(
            title, Qt.ElideRight, title_rect.width()
        )
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_title)

        # Draw path
        path_font = painter.font()
        path_font.setPointSize(self._get_scaled_font_size(VC.FONT_PATH))
        path_font.setWeight(QFont.Weight.Medium)  # Medium (500)
        painter.setFont(path_font)
        # Improved contrast: use WindowText with 75% opacity instead of Mid
        path_color = QColor(palette.color(QPalette.WindowText))
        path_color.setAlphaF(0.75)
        painter.setPen(path_color)

        path_rect = QRect(
            text_rect.x(),
            title_rect.bottom() + 2,
            text_rect.width(),
            18
        )
        elided_path = painter.fontMetrics().elidedText(
            record.path, Qt.ElideMiddle, path_rect.width()
        )
        painter.drawText(path_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_path)

        painter.restore()

    def sizeHint(self, option, index):
        """Return the size hint for the list item"""
        return QSize(option.rect.width(), self.item_height)


class ThemedCardDelegate(QStyledItemDelegate):
    """Theme-aware card view delegate"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = ThemeManager()
        self.settings_manager = SettingsManager()
        self.card_width = self.settings_manager.settings.grid_card_width
        self.card_height = self.settings_manager.settings.grid_card_height
        self.padding = VC.CARD_PADDING
        self.icon_size = VC.CARD_ICON_SIZE

        # Connect to settings changes for live updates
        self.settings_manager.font_settings_changed.connect(self._on_font_settings_changed)
        self.settings_manager.view_settings_changed.connect(self._on_view_settings_changed)

    def _on_font_settings_changed(self):
        """Handle font settings change - trigger repaint"""
        if self.parent():
            self.parent().viewport().update()

    def _on_view_settings_changed(self):
        """Handle view settings change - update card size"""
        self.card_width = self.settings_manager.settings.grid_card_width
        self.card_height = self.settings_manager.settings.grid_card_height
        if self.parent():
            self.parent().viewport().update()

    def _get_contrast_text_color(self, palette, is_selected: bool) -> QColor:
        """選択状態に応じて適切なコントラストのテキスト色を取得"""
        if is_selected:
            # テーマで定義された選択時のテキスト色を使用
            selection_color = self.theme_manager.get_color('selection_text')
            # フォールバック: 空の色（黒）の場合は白を使用
            if not selection_color.isValid() or selection_color.name() == '#000000':
                return QColor('#ffffff')
            return selection_color
        else:
            return palette.color(QPalette.WindowText)

    def _get_scaled_font_size(self, base_size: int) -> int:
        """Get font size scaled by global settings"""
        global_size = self.settings_manager.get_effective_font_size()
        # Scale proportionally: base 13px is the reference
        return int(base_size * (global_size / 13.0))

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
        card_path.addRoundedRect(QRectF(card_rect), VC.BORDER_RADIUS_MEDIUM, VC.BORDER_RADIUS_MEDIUM)

        # Use palette colors
        palette = QApplication.palette()
        if is_selected:
            # テーマで定義された選択背景色を使用
            bg_color = self.theme_manager.get_color('selection_background')
            # フォールバック: 無効な色の場合はパレットのハイライト色を使用
            if not bg_color.isValid() or bg_color.name() == '#000000':
                bg_color = palette.color(QPalette.Highlight)
            painter.setPen(QPen(bg_color.darker(110), 2))
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

        # File icon
        icon_rect = QRect(
            content_rect.x() + (content_rect.width() - self.icon_size) // 2,
            content_rect.y() + 10,
            self.icon_size,
            self.icon_size
        )

        # Draw file type icon
        if record.custom_icon:
            # カスタムアイコンが設定されている場合はそれを使用
            emoji = record.custom_icon
            icon_color = self.theme_manager.get_color('primary')
        elif os.path.isdir(record.path):
            emoji = FI.FOLDER
            icon_color = self.theme_manager.get_color('primary')
        else:
            ext = os.path.splitext(record.path)[1].lower()
            emoji = FI.FILE
            icon_color = palette.color(QPalette.ButtonText)

        # Draw icon background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(icon_color.lighter(VC.ICON_BG_LIGHTNESS)))
        painter.drawEllipse(icon_rect.adjusted(8, 8, -8, -8))

        # Draw emoji
        font = painter.font()
        font.setPointSize(self._get_scaled_font_size(VC.FONT_ICON_CARD))
        painter.setFont(font)
        text_color = self._get_contrast_text_color(palette, is_selected)
        painter.setPen(text_color)
        painter.drawText(icon_rect, Qt.AlignCenter, emoji)

        # Draw title
        title_rect = QRect(
            content_rect.x(),
            icon_rect.bottom() + 12,
            content_rect.width(),
            30
        )

        title_font = painter.font()
        title_font.setPointSize(self._get_scaled_font_size(VC.FONT_CARD_TITLE))
        title_font.setWeight(QFont.Weight.DemiBold)  # SemiBold (600)
        painter.setFont(title_font)
        painter.setPen(text_color)

        title = record.name or os.path.basename(record.path)
        elided_title = painter.fontMetrics().elidedText(
            title, Qt.ElideRight, title_rect.width() - 8
        )
        painter.drawText(title_rect, Qt.AlignCenter, elided_title)

        # Draw path
        path_rect = QRect(
            content_rect.x() + 4,
            title_rect.bottom() + 4,
            content_rect.width() - 8,
            content_rect.height() - title_rect.bottom() - 8
        )

        path_font = painter.font()
        path_font.setPointSize(self._get_scaled_font_size(VC.FONT_CARD_PATH))
        path_font.setWeight(QFont.Weight.Medium)  # Medium (500)
        painter.setFont(path_font)
        # Improved contrast: use WindowText with 75% opacity instead of Mid
        path_color = QColor(palette.color(QPalette.WindowText))
        path_color.setAlphaF(0.75)
        painter.setPen(path_color)

        elided_path = painter.fontMetrics().elidedText(
            record.path, Qt.ElideMiddle, path_rect.width()
        )
        painter.drawText(path_rect, Qt.AlignTop | Qt.AlignHCenter, elided_path)

        # Draw tags if present
        if record.tags:
            tags_rect = QRect(
                content_rect.x() + 4,
                content_rect.bottom() - 20,
                content_rect.width() - 8,
                16
            )

            tags_font = painter.font()
            tags_font.setPointSize(self._get_scaled_font_size(VC.FONT_CARD_TAGS))
            tags_font.setWeight(QFont.Weight.Medium)  # Medium (500)
            tags_font.setItalic(True)
            painter.setFont(tags_font)
            painter.setPen(self.theme_manager.get_color('secondary'))

            tags_text = f"[{record.tags}]"
            elided_tags = painter.fontMetrics().elidedText(
                tags_text, Qt.ElideRight, tags_rect.width()
            )
            painter.drawText(tags_rect, Qt.AlignCenter, elided_tags)

        painter.restore()

    def sizeHint(self, option, index):
        """Return the size hint for the card item"""
        return QSize(self.card_width, self.card_height)