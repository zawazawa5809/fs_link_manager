"""
Theme design tokens and constants for FS Link Manager
UI要素の統一的なデザイン定数を管理
"""

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class VisualConstants:
    """視覚的なデザイン定数"""

    # Icon background lightness
    ICON_BG_LIGHTNESS: ClassVar[int] = 180

    # Highlight colors
    HIGHLIGHT_LIGHTNESS: ClassVar[int] = 150
    HIGHLIGHT_BORDER_DARKNESS: ClassVar[int] = 110

    # List delegate dimensions
    LIST_ITEM_HEIGHT: ClassVar[int] = 90
    LIST_PADDING: ClassVar[int] = 12
    LIST_ICON_SIZE: ClassVar[int] = 48

    # Card delegate dimensions
    CARD_WIDTH: ClassVar[int] = 200
    CARD_HEIGHT: ClassVar[int] = 220
    CARD_PADDING: ClassVar[int] = 16
    CARD_ICON_SIZE: ClassVar[int] = 64

    # Font sizes
    FONT_TITLE: ClassVar[int] = 14
    FONT_PATH: ClassVar[int] = 11
    FONT_CARD_TITLE: ClassVar[int] = 13
    FONT_CARD_PATH: ClassVar[int] = 10
    FONT_CARD_TAGS: ClassVar[int] = 10
    FONT_ICON_LIST: ClassVar[int] = 18
    FONT_ICON_CARD: ClassVar[int] = 24

    # Border radius
    BORDER_RADIUS_SMALL: ClassVar[int] = 6
    BORDER_RADIUS_MEDIUM: ClassVar[int] = 10
    BORDER_RADIUS_LARGE: ClassVar[int] = 12

    # Shadow
    SHADOW_BLUR_RADIUS: ClassVar[int] = 20
    SHADOW_OFFSET_X: ClassVar[int] = 0
    SHADOW_OFFSET_Y: ClassVar[int] = 2
    SHADOW_COLOR_RGBA: ClassVar[tuple] = (0, 0, 0, 30)


@dataclass
class FileTypeIcons:
    """ファイルタイプ別のアイコン定義"""

    FOLDER: ClassVar[str] = "📁"
    FILE: ClassVar[str] = "📄"


# エクスポート用の便利な変数
VC = VisualConstants
FI = FileTypeIcons
