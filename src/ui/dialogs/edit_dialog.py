"""Link editing dialogs for FS Link Manager"""

import os
from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QDialogButtonBox, QFileDialog, QPushButton, QGridLayout
)
from PySide6.QtCore import Qt

from ...core import LinkRecord, SettingsManager
from ...i18n import tr
from ..widgets.factory import WidgetFactory


class LinkAddDialog(QDialog):
    """リンク追加ダイアログ"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialogs.add_link"))
        self.setModal(True)
        self.resize(500, 420)

        self.path = ""
        self.settings_manager = SettingsManager()
        self._setup_ui()
        self._load_default_tags()

    def _setup_ui(self):
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # パス選択
        path_layout = QHBoxLayout()
        path_label = WidgetFactory.create_label(tr("dialogs.path_label"), "default")
        path_layout.addWidget(path_label)

        self.path_field = WidgetFactory.create_input_field(
            tr("dialogs.path_placeholder"), "text"
        )
        self.path_field.setReadOnly(True)
        path_layout.addWidget(self.path_field, 1)

        browse_btn = WidgetFactory.create_button(tr("dialogs.browse"), "secondary")
        browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)

        # 名前入力
        name_layout = QHBoxLayout()
        name_label = WidgetFactory.create_label(tr("dialogs.display_name"), "default")
        name_layout.addWidget(name_label)

        self.name_field = WidgetFactory.create_input_field(
            tr("dialogs.name_placeholder"), "text"
        )
        name_layout.addWidget(self.name_field, 1)

        layout.addLayout(name_layout)

        # タグ入力
        tags_layout = QHBoxLayout()
        tags_label = WidgetFactory.create_label(tr("dialogs.tags_hint"), "default")
        tags_layout.addWidget(tags_label)

        self.tags_field = WidgetFactory.create_input_field(
            tr("dialogs.tags_placeholder"), "text"
        )
        tags_layout.addWidget(self.tags_field, 1)

        layout.addLayout(tags_layout)

        # カスタムアイコン選択
        icon_layout = QVBoxLayout()
        icon_header_layout = QHBoxLayout()
        icon_label = WidgetFactory.create_label("アイコン:", "default")
        icon_header_layout.addWidget(icon_label)

        self.icon_field = WidgetFactory.create_input_field("絵文字を入力", "text")
        self.icon_field.setMaxLength(2)  # 絵文字は通常1-2文字
        icon_header_layout.addWidget(self.icon_field)

        clear_icon_btn = WidgetFactory.create_button("デフォルトに戻す", "secondary")
        clear_icon_btn.clicked.connect(lambda: self.icon_field.clear())
        icon_header_layout.addWidget(clear_icon_btn)

        icon_layout.addLayout(icon_header_layout)

        # よく使う絵文字のプリセット
        preset_label = WidgetFactory.create_label("よく使う絵文字:", "default")
        icon_layout.addWidget(preset_label)

        emoji_presets = [
            "📁", "📄", "📷", "🎵", "🎬", "📚", "💻", "🎮",
            "🏠", "⚙️", "🔧", "📝", "📊", "🗂️", "🔍", "⭐"
        ]

        preset_grid = QGridLayout()
        preset_grid.setSpacing(4)
        for idx, emoji in enumerate(emoji_presets):
            btn = QPushButton(emoji)
            btn.setFixedSize(40, 40)
            btn.clicked.connect(lambda checked, e=emoji: self.icon_field.setText(e))
            preset_grid.addWidget(btn, idx // 8, idx % 8)

        icon_layout.addLayout(preset_grid)
        layout.addLayout(icon_layout)

        # ボタン
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_default_tags(self):
        """デフォルトタグを読み込み"""
        default_tags = self.settings_manager.settings.default_tags
        if default_tags:
            self.tags_field.setText(default_tags)

    def _apply_auto_tags(self, path: str):
        """パスに応じた自動タグを適用"""
        from ...utils import generate_auto_tags, merge_tags

        # 自動タグ機能が無効の場合は何もしない
        if not self.settings_manager.settings.auto_tag_enabled:
            return

        # デフォルトタグを取得
        default_tags = self.settings_manager.settings.default_tags

        # 自動タグを生成
        auto_tags = generate_auto_tags(path)

        # デフォルトタグと自動タグをマージ
        merged_tags = merge_tags(default_tags, auto_tags)

        # タグフィールドに設定
        self.tags_field.setText(merged_tags)

    def _browse_path(self):
        """パスを参照"""
        dlg = QFileDialog(self, tr("dialogs.select_link_target"))
        dlg.setFileMode(QFileDialog.ExistingFile)
        if dlg.exec():
            paths = dlg.selectedFiles()
            if paths:
                self.path = paths[0]
                self.path_field.setText(self.path)
                # 自動的に名前を設定
                if not self.name_field.text():
                    self.name_field.setText(os.path.basename(self.path))
                # 自動タグを適用
                self._apply_auto_tags(self.path)

    def get_values(self) -> Tuple[str, str, str, str]:
        """入力値を取得"""
        return (
            self.name_field.text(),
            self.path,
            self.tags_field.text(),
            self.icon_field.text()
        )


class LinkEditDialog(QDialog):
    """リンク編集ダイアログ"""

    def __init__(self, record: LinkRecord, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialogs.edit_link"))
        self.setModal(True)
        self.resize(500, 400)

        self.record = record
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # パス表示（読み取り専用）
        path_layout = QHBoxLayout()
        path_label = WidgetFactory.create_label(tr("dialogs.path_label"), "default")
        path_layout.addWidget(path_label)

        self.path_display = WidgetFactory.create_input_field("", "text")
        self.path_display.setReadOnly(True)
        path_layout.addWidget(self.path_display, 1)

        layout.addLayout(path_layout)

        # 名前入力
        name_layout = QHBoxLayout()
        name_label = WidgetFactory.create_label(tr("dialogs.display_name"), "default")
        name_layout.addWidget(name_label)

        self.name_field = WidgetFactory.create_input_field(
            tr("dialogs.name_placeholder"), "text"
        )
        name_layout.addWidget(self.name_field, 1)

        layout.addLayout(name_layout)

        # タグ入力
        tags_layout = QHBoxLayout()
        tags_label = WidgetFactory.create_label(tr("dialogs.tags_hint"), "default")
        tags_layout.addWidget(tags_label)

        self.tags_field = WidgetFactory.create_input_field(
            tr("dialogs.tags_placeholder"), "text"
        )
        tags_layout.addWidget(self.tags_field, 1)

        layout.addLayout(tags_layout)

        # カスタムアイコン選択
        icon_layout = QVBoxLayout()
        icon_header_layout = QHBoxLayout()
        icon_label = WidgetFactory.create_label("アイコン:", "default")
        icon_header_layout.addWidget(icon_label)

        self.icon_field = WidgetFactory.create_input_field("絵文字を入力", "text")
        self.icon_field.setMaxLength(2)  # 絵文字は通常1-2文字
        icon_header_layout.addWidget(self.icon_field)

        clear_icon_btn = WidgetFactory.create_button("デフォルトに戻す", "secondary")
        clear_icon_btn.clicked.connect(lambda: self.icon_field.clear())
        icon_header_layout.addWidget(clear_icon_btn)

        icon_layout.addLayout(icon_header_layout)

        # よく使う絵文字のプリセット
        preset_label = WidgetFactory.create_label("よく使う絵文字:", "default")
        icon_layout.addWidget(preset_label)

        emoji_presets = [
            "📁", "📄", "📷", "🎵", "🎬", "📚", "💻", "🎮",
            "🏠", "⚙️", "🔧", "📝", "📊", "🗂️", "🔍", "⭐"
        ]

        preset_grid = QGridLayout()
        preset_grid.setSpacing(4)
        for idx, emoji in enumerate(emoji_presets):
            btn = QPushButton(emoji)
            btn.setFixedSize(40, 40)
            btn.clicked.connect(lambda checked, e=emoji: self.icon_field.setText(e))
            preset_grid.addWidget(btn, idx // 8, idx % 8)

        icon_layout.addLayout(preset_grid)
        layout.addLayout(icon_layout)

        # ボタン
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_values(self):
        """既存の値を読み込み"""
        self.path_display.setText(self.record.path)
        self.name_field.setText(self.record.name)
        self.tags_field.setText(self.record.tags)
        self.icon_field.setText(self.record.custom_icon)

    def get_values(self) -> Tuple[str, str, str]:
        """入力値を取得"""
        return (
            self.name_field.text(),
            self.tags_field.text(),
            self.icon_field.text()
        )
