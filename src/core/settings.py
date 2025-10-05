"""Application settings management for FS Link Manager"""

from dataclasses import dataclass
from typing import Optional, ClassVar
from PySide6.QtCore import QObject, Signal, QSettings


@dataclass
class AppSettings:
    """アプリケーション設定のデータクラス"""

    # 外観設定
    font_size: int = 13
    font_scale: float = 1.0  # 0.85=小, 1.0=中, 1.15=大, 1.3=特大
    theme: str = "dark_professional"
    language: str = "ja_JP"

    # 表示設定
    default_view_mode: str = "list"  # "list" or "grid"
    list_item_height: int = 90
    grid_card_width: int = 200
    grid_card_height: int = 220

    # 一般設定
    auto_save: bool = True
    show_item_count: bool = True

    # タグ設定
    default_tags: str = ""  # 新規リンクのデフォルトタグ(カンマ区切り)
    auto_tag_enabled: bool = True  # ファイル種別自動タグ付けを有効化


class SettingsManager(QObject):
    """アプリケーション設定マネージャー"""

    _instance: ClassVar[Optional['SettingsManager']] = None
    settings_changed = Signal()  # 設定変更シグナル
    font_settings_changed = Signal()  # フォント設定変更シグナル
    view_settings_changed = Signal()  # 表示設定変更シグナル

    def __new__(cls):
        """シングルトンパターンの実装"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初期化（一度のみ実行）"""
        if hasattr(self, '_initialized'):
            return

        super().__init__()
        self.qsettings = QSettings("FSLinkManager", "AppSettings")
        self.settings = AppSettings()
        self._initialized = True
        self._load_settings()

    def _load_settings(self):
        """設定を読み込み"""
        # 外観設定
        self.settings.font_size = int(self.qsettings.value("appearance/font_size", 13))
        self.settings.font_scale = float(self.qsettings.value("appearance/font_scale", 1.0))
        self.settings.theme = self.qsettings.value("appearance/theme", "dark_professional")
        self.settings.language = self.qsettings.value("appearance/language", "ja_JP")

        # 表示設定
        self.settings.default_view_mode = self.qsettings.value("view/default_mode", "list")
        self.settings.list_item_height = int(self.qsettings.value("view/list_item_height", 90))
        self.settings.grid_card_width = int(self.qsettings.value("view/grid_card_width", 200))
        self.settings.grid_card_height = int(self.qsettings.value("view/grid_card_height", 220))

        # 一般設定
        self.settings.auto_save = self.qsettings.value("general/auto_save", True, type=bool)
        self.settings.show_item_count = self.qsettings.value("general/show_item_count", True, type=bool)

        # タグ設定
        self.settings.default_tags = self.qsettings.value("tags/default_tags", "")
        self.settings.auto_tag_enabled = self.qsettings.value("tags/auto_tag_enabled", True, type=bool)

    def save_settings(self):
        """設定を保存"""
        # 外観設定
        self.qsettings.setValue("appearance/font_size", self.settings.font_size)
        self.qsettings.setValue("appearance/font_scale", self.settings.font_scale)
        self.qsettings.setValue("appearance/theme", self.settings.theme)
        self.qsettings.setValue("appearance/language", self.settings.language)

        # 表示設定
        self.qsettings.setValue("view/default_mode", self.settings.default_view_mode)
        self.qsettings.setValue("view/list_item_height", self.settings.list_item_height)
        self.qsettings.setValue("view/grid_card_width", self.settings.grid_card_width)
        self.qsettings.setValue("view/grid_card_height", self.settings.grid_card_height)

        # 一般設定
        self.qsettings.setValue("general/auto_save", self.settings.auto_save)
        self.qsettings.setValue("general/show_item_count", self.settings.show_item_count)

        # タグ設定
        self.qsettings.setValue("tags/default_tags", self.settings.default_tags)
        self.qsettings.setValue("tags/auto_tag_enabled", self.settings.auto_tag_enabled)

        self.qsettings.sync()
        self.settings_changed.emit()

    def update_font_settings(self, font_size: Optional[int] = None, font_scale: Optional[float] = None):
        """フォント設定を更新"""
        changed = False
        if font_size is not None and self.settings.font_size != font_size:
            self.settings.font_size = font_size
            changed = True
        if font_scale is not None and self.settings.font_scale != font_scale:
            self.settings.font_scale = font_scale
            changed = True

        if changed:
            self.save_settings()
            self.font_settings_changed.emit()

    def update_view_settings(
        self,
        default_view_mode: Optional[str] = None,
        list_item_height: Optional[int] = None,
        grid_card_width: Optional[int] = None,
        grid_card_height: Optional[int] = None
    ):
        """表示設定を更新"""
        changed = False
        if default_view_mode is not None:
            self.settings.default_view_mode = default_view_mode
            changed = True
        if list_item_height is not None:
            self.settings.list_item_height = list_item_height
            changed = True
        if grid_card_width is not None:
            self.settings.grid_card_width = grid_card_width
            changed = True
        if grid_card_height is not None:
            self.settings.grid_card_height = grid_card_height
            changed = True

        if changed:
            self.save_settings()
            self.view_settings_changed.emit()

    def update_tag_settings(self, default_tags: str, auto_tag_enabled: Optional[bool] = None):
        """タグ設定を更新"""
        changed = False
        if self.settings.default_tags != default_tags:
            self.settings.default_tags = default_tags
            changed = True
        if auto_tag_enabled is not None and self.settings.auto_tag_enabled != auto_tag_enabled:
            self.settings.auto_tag_enabled = auto_tag_enabled
            changed = True
        if changed:
            self.save_settings()

    def reset_to_defaults(self):
        """デフォルト設定にリセット"""
        self.settings = AppSettings()
        self.save_settings()

    def get_effective_font_size(self) -> int:
        """スケールを適用した実効フォントサイズを取得"""
        return int(self.settings.font_size * self.settings.font_scale)

    def get_font_scale_name(self) -> str:
        """フォントスケールの表示名を取得"""
        scale_names = {
            0.85: "small",
            1.0: "medium",
            1.15: "large",
            1.3: "extra_large"
        }
        return scale_names.get(self.settings.font_scale, "custom")
