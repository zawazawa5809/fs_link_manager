"""Settings dialog for FS Link Manager"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QSlider, QComboBox, QCheckBox, QSpinBox,
    QDialogButtonBox, QGroupBox, QFormLayout, QLineEdit
)
from PySide6.QtCore import Qt, Signal

from ...core import SettingsManager
from ...themes import ThemeManager
from ...i18n import tr, Translator
from ..widgets.factory import WidgetFactory


class SettingsDialog(QDialog):
    """設定ダイアログ"""

    settings_applied = Signal()  # 設定適用シグナル

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialogs.settings_title"))
        self.setModal(True)
        self.resize(600, 500)

        self.settings_manager = SettingsManager()
        self.theme_manager = ThemeManager()
        self.translator = Translator()

        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        """UIをセットアップ"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # タブウィジェット
        tabs = QTabWidget()

        # 外観タブ
        appearance_tab = self._create_appearance_tab()
        tabs.addTab(appearance_tab, tr("settings.tabs.appearance"))

        # 表示タブ
        view_tab = self._create_view_tab()
        tabs.addTab(view_tab, tr("settings.tabs.view"))

        # 一般タブ
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, tr("settings.tabs.general"))

        # タグタブ
        tag_tab = self._create_tag_tab()
        tabs.addTab(tag_tab, tr("settings.tabs.tags"))

        layout.addWidget(tabs)

        # ボタン
        button_layout = QHBoxLayout()

        reset_btn = WidgetFactory.create_button(
            tr("settings.reset_defaults"), "secondary"
        )
        reset_btn.clicked.connect(self._reset_defaults)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        button_box.button(QDialogButtonBox.Ok).setText(tr("settings.ok"))
        button_box.button(QDialogButtonBox.Cancel).setText(tr("settings.cancel"))
        button_box.button(QDialogButtonBox.Apply).setText(tr("settings.apply"))

        button_box.accepted.connect(self._apply_and_close)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self._apply_settings)

        button_layout.addWidget(button_box)

        layout.addLayout(button_layout)

    def _create_appearance_tab(self) -> QWidget:
        """外観タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)

        # フォント設定グループ
        font_group = QGroupBox(tr("settings.appearance.font_settings"))
        font_layout = QFormLayout()
        font_layout.setSpacing(12)

        # フォントサイズ
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 20)
        self.font_size_spin.setSuffix(" px")
        font_layout.addRow(tr("settings.appearance.base_font_size"), self.font_size_spin)

        # フォントスケール
        scale_layout = QHBoxLayout()
        self.font_scale_slider = QSlider(Qt.Horizontal)
        self.font_scale_slider.setRange(0, 3)  # 0=0.85, 1=1.0, 2=1.15, 3=1.3
        self.font_scale_slider.setValue(1)
        self.font_scale_slider.setTickPosition(QSlider.TicksBelow)
        self.font_scale_slider.setTickInterval(1)

        self.scale_label = WidgetFactory.create_label(tr("settings.appearance.scale_medium"), "default")
        self.font_scale_slider.valueChanged.connect(self._update_scale_label)

        scale_layout.addWidget(self.font_scale_slider, 1)
        scale_layout.addWidget(self.scale_label)

        font_layout.addRow(tr("settings.appearance.font_scale"), scale_layout)

        font_group.setLayout(font_layout)
        layout.addWidget(font_group)

        # テーマ設定グループ
        theme_group = QGroupBox(tr("settings.appearance.theme_settings"))
        theme_layout = QFormLayout()
        theme_layout.setSpacing(12)

        # テーマ選択
        self.theme_combo = QComboBox()
        available_themes = self.theme_manager.get_available_themes()
        for theme_key in available_themes:
            display_name = tr(f"themes.{theme_key}")
            self.theme_combo.addItem(display_name, theme_key)
        theme_layout.addRow(tr("settings.appearance.theme"), self.theme_combo)

        # 言語選択
        self.language_combo = QComboBox()
        for lang_code in self.translator.get_available_languages():
            lang_name = self.translator.get_language_name(lang_code)
            self.language_combo.addItem(lang_name, lang_code)
        theme_layout.addRow(tr("settings.appearance.language"), self.language_combo)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        layout.addStretch()
        return widget

    def _create_view_tab(self) -> QWidget:
        """表示タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)

        # 表示モード設定グループ
        view_group = QGroupBox(tr("settings.view.view_mode_settings"))
        view_layout = QFormLayout()
        view_layout.setSpacing(12)

        # デフォルト表示モード
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItem(tr("view_modes.list"), "list")
        self.view_mode_combo.addItem(tr("view_modes.grid"), "grid")
        view_layout.addRow(tr("settings.view.default_view_mode"), self.view_mode_combo)

        view_group.setLayout(view_layout)
        layout.addWidget(view_group)

        # リスト表示設定グループ
        list_group = QGroupBox(tr("settings.view.list_settings"))
        list_layout = QFormLayout()
        list_layout.setSpacing(12)

        # リストアイテム高さ
        self.list_height_spin = QSpinBox()
        self.list_height_spin.setRange(70, 120)
        self.list_height_spin.setSuffix(" px")
        list_layout.addRow(tr("settings.view.list_item_height"), self.list_height_spin)

        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        # グリッド表示設定グループ
        grid_group = QGroupBox(tr("settings.view.grid_settings"))
        grid_layout = QFormLayout()
        grid_layout.setSpacing(12)

        # グリッドカードサイズ
        self.grid_size_combo = QComboBox()
        self.grid_size_combo.addItem(tr("settings.view.grid_size_small"), "small")
        self.grid_size_combo.addItem(tr("settings.view.grid_size_medium"), "medium")
        self.grid_size_combo.addItem(tr("settings.view.grid_size_large"), "large")
        grid_layout.addRow(tr("settings.view.grid_card_size"), self.grid_size_combo)

        grid_group.setLayout(grid_layout)
        layout.addWidget(grid_group)

        layout.addStretch()
        return widget

    def _create_general_tab(self) -> QWidget:
        """一般タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)

        # 動作設定グループ
        behavior_group = QGroupBox(tr("settings.general.behavior_settings"))
        behavior_layout = QVBoxLayout()
        behavior_layout.setSpacing(12)

        # 自動保存
        self.auto_save_check = QCheckBox(tr("settings.general.auto_save"))
        behavior_layout.addWidget(self.auto_save_check)

        # アイテム数表示
        self.show_count_check = QCheckBox(tr("settings.general.show_item_count"))
        behavior_layout.addWidget(self.show_count_check)

        behavior_group.setLayout(behavior_layout)
        layout.addWidget(behavior_group)

        layout.addStretch()
        return widget

    def _create_tag_tab(self) -> QWidget:
        """タグタブを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)

        # タグ設定グループ
        tag_group = QGroupBox(tr("settings.tags.tag_settings"))
        tag_layout = QFormLayout()
        tag_layout.setSpacing(12)

        # デフォルトタグ入力
        self.default_tags_field = WidgetFactory.create_input_field(
            tr("settings.tags.default_tags_placeholder"), "text"
        )
        tag_layout.addRow(tr("settings.tags.default_tags"), self.default_tags_field)

        # ヘルプテキスト
        hint_label = WidgetFactory.create_label(
            tr("settings.tags.default_tags_hint"), "caption"
        )
        hint_label.setWordWrap(True)
        tag_layout.addRow("", hint_label)

        tag_group.setLayout(tag_layout)
        layout.addWidget(tag_group)

        # 自動タグ付け設定グループ
        auto_tag_group = QGroupBox()
        auto_tag_layout = QVBoxLayout()
        auto_tag_layout.setSpacing(12)

        # 自動タグ有効化チェックボックス
        self.auto_tag_check = QCheckBox(tr("settings.tags.auto_tag_enabled"))
        auto_tag_layout.addWidget(self.auto_tag_check)

        # ヘルプテキスト
        auto_hint_label = WidgetFactory.create_label(
            tr("settings.tags.auto_tag_hint"), "caption"
        )
        auto_hint_label.setWordWrap(True)
        auto_tag_layout.addWidget(auto_hint_label)

        auto_tag_group.setLayout(auto_tag_layout)
        layout.addWidget(auto_tag_group)

        layout.addStretch()
        return widget

    def _update_scale_label(self, value: int):
        """スケールラベルを更新"""
        scale_map = {
            0: (0.85, tr("settings.appearance.scale_small")),
            1: (1.0, tr("settings.appearance.scale_medium")),
            2: (1.15, tr("settings.appearance.scale_large")),
            3: (1.3, tr("settings.appearance.scale_extra_large"))
        }
        _, label_text = scale_map.get(value, (1.0, tr("settings.appearance.scale_medium")))
        self.scale_label.setText(label_text)

    def _load_current_settings(self):
        """現在の設定を読み込み"""
        settings = self.settings_manager.settings

        # 外観設定
        self.font_size_spin.setValue(settings.font_size)

        # スケール値からスライダー位置を設定
        scale_to_index = {0.85: 0, 1.0: 1, 1.15: 2, 1.3: 3}
        slider_index = scale_to_index.get(settings.font_scale, 1)
        self.font_scale_slider.setValue(slider_index)

        # テーマ選択
        theme_index = self.theme_combo.findData(settings.theme)
        if theme_index >= 0:
            self.theme_combo.setCurrentIndex(theme_index)

        # 言語選択
        lang_index = self.language_combo.findData(settings.language)
        if lang_index >= 0:
            self.language_combo.setCurrentIndex(lang_index)

        # 表示設定
        view_index = self.view_mode_combo.findData(settings.default_view_mode)
        if view_index >= 0:
            self.view_mode_combo.setCurrentIndex(view_index)

        self.list_height_spin.setValue(settings.list_item_height)

        # グリッドサイズ
        if settings.grid_card_width <= 180:
            self.grid_size_combo.setCurrentIndex(0)  # small
        elif settings.grid_card_width <= 220:
            self.grid_size_combo.setCurrentIndex(1)  # medium
        else:
            self.grid_size_combo.setCurrentIndex(2)  # large

        # 一般設定
        self.auto_save_check.setChecked(settings.auto_save)
        self.show_count_check.setChecked(settings.show_item_count)

        # タグ設定
        self.default_tags_field.setText(settings.default_tags)
        self.auto_tag_check.setChecked(settings.auto_tag_enabled)

    def _apply_settings(self):
        """設定を適用"""
        # フォント設定
        scale_map = {0: 0.85, 1: 1.0, 2: 1.15, 3: 1.3}
        font_scale = scale_map.get(self.font_scale_slider.value(), 1.0)

        self.settings_manager.update_font_settings(
            font_size=self.font_size_spin.value(),
            font_scale=font_scale
        )

        # テーマ設定
        theme_key = self.theme_combo.currentData()
        if theme_key != self.settings_manager.settings.theme:
            self.settings_manager.settings.theme = theme_key
            self.theme_manager.apply_theme(theme_key)

        # 言語設定
        lang_code = self.language_combo.currentData()
        if lang_code != self.settings_manager.settings.language:
            self.settings_manager.settings.language = lang_code
            self.translator.set_language(lang_code)

        # 表示設定
        grid_size_map = {
            0: (160, 200),  # small
            1: (200, 220),  # medium
            2: (240, 260)   # large
        }
        grid_width, grid_height = grid_size_map.get(
            self.grid_size_combo.currentIndex(), (200, 220)
        )

        self.settings_manager.update_view_settings(
            default_view_mode=self.view_mode_combo.currentData(),
            list_item_height=self.list_height_spin.value(),
            grid_card_width=grid_width,
            grid_card_height=grid_height
        )

        # 一般設定
        self.settings_manager.settings.auto_save = self.auto_save_check.isChecked()
        self.settings_manager.settings.show_item_count = self.show_count_check.isChecked()
        self.settings_manager.save_settings()

        # タグ設定
        self.settings_manager.update_tag_settings(
            self.default_tags_field.text(),
            auto_tag_enabled=self.auto_tag_check.isChecked()
        )

        self.settings_applied.emit()

    def _apply_and_close(self):
        """設定を適用して閉じる"""
        self._apply_settings()
        self.accept()

    def _reset_defaults(self):
        """デフォルト設定にリセット"""
        self.settings_manager.reset_to_defaults()
        self._load_current_settings()
        self.settings_applied.emit()
