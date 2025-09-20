"""
Theme Manager for FS Link Manager
Implements QPalette-based theme system with design tokens
"""

import json
from pathlib import Path
from typing import Dict, Optional, ClassVar
from PySide6.QtCore import QObject, Signal, QSettings
from PySide6.QtGui import QPalette, QColor, QPainter
from PySide6.QtWidgets import QApplication, QWidget


class ThemeManager(QObject):
    """統一されたテーマ管理システム"""

    _instance: ClassVar[Optional['ThemeManager']] = None
    theme_changed = Signal(str)  # テーマ変更シグナル

    def __new__(cls, app: Optional[QApplication] = None):
        """シングルトンパターンの実装"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, app: Optional[QApplication] = None):
        """初期化（一度のみ実行）"""
        if hasattr(self, '_initialized'):
            return

        super().__init__()
        self.app = app or QApplication.instance()
        self.themes: Dict[str, Dict] = {}
        self.current_theme: Optional[str] = None
        self.settings = QSettings("FSLinkManager", "ThemeSettings")
        self._initialized = True
        self._load_theme_definitions()
        self._restore_last_theme()

    def _load_theme_definitions(self):
        """テーマ定義をJSONから読み込み"""
        theme_dir = Path("themes")
        theme_dir.mkdir(exist_ok=True)

        # デフォルトテーマを作成
        self._create_default_themes()

        # カスタムテーマを読み込み
        for theme_file in theme_dir.glob("*.json"):
            try:
                with open(theme_file, 'r', encoding='utf-8') as f:
                    theme_data = json.load(f)
                    self.themes[theme_file.stem] = theme_data
            except (json.JSONDecodeError, IOError) as e:
                print(f"テーマ読み込みエラー {theme_file}: {e}")

    def _create_default_themes(self):
        """組み込みのデフォルトテーマを作成"""
        self.themes['dark_professional'] = {
            'name': 'Dark Professional',
            'colors': {
                'window': '#232428',
                'window_text': '#eeeeee',
                'base': '#2b2d31',
                'alternate_base': '#35363a',
                'text': '#ffffff',
                'button': '#35363a',
                'button_text': '#ffffff',
                'bright_text': '#ff0000',
                'highlight': '#2f6fff',
                'highlighted_text': '#ffffff',
                'link': '#5a8fff',
                'link_visited': '#8a6fff',
                'mid': '#5a5c63',
                'shadow': '#191a1d',
                'light': '#45474e',
                'disabled_text': '#7f8084',
                # Semantic colors
                'primary': '#2f6fff',
                'primary_light': '#5a8fff',
                'primary_dark': '#1a4fcc',
                'secondary': '#6c757d',
                'success': '#4caf50',
                'warning': '#ff9800',
                'danger': '#f44336',
                'info': '#2196f3'
            },
            'dimensions': {
                'border_radius': 6,
                'padding': 8,
                'padding_small': 4,
                'padding_large': 12,
                'spacing': 8,
                'min_button_height': 32,
                'font_family': 'Segoe UI',
                'font_size': 10,
                'font_size_small': 9,
                'font_size_large': 12,
                'icon_size': 20,
                'icon_size_small': 16,
                'icon_size_large': 24
            }
        }

        self.themes['light_professional'] = {
            'name': 'Light Professional',
            'colors': {
                'window': '#f5f5f5',
                'window_text': '#212121',
                'base': '#ffffff',
                'alternate_base': '#f0f0f0',
                'text': '#212121',
                'button': '#ffffff',
                'button_text': '#212121',
                'bright_text': '#ff0000',
                'highlight': '#2196f3',
                'highlighted_text': '#ffffff',
                'link': '#1976d2',
                'link_visited': '#7b1fa2',
                'mid': '#bdbdbd',
                'shadow': '#e0e0e0',
                'light': '#fafafa',
                'disabled_text': '#9e9e9e',
                # Semantic colors
                'primary': '#2196f3',
                'primary_light': '#64b5f6',
                'primary_dark': '#1976d2',
                'secondary': '#6c757d',
                'success': '#4caf50',
                'warning': '#ff9800',
                'danger': '#f44336',
                'info': '#00bcd4'
            },
            'dimensions': {
                'border_radius': 6,
                'padding': 8,
                'padding_small': 4,
                'padding_large': 12,
                'spacing': 8,
                'min_button_height': 32,
                'font_family': 'Segoe UI',
                'font_size': 10,
                'font_size_small': 9,
                'font_size_large': 12,
                'icon_size': 20,
                'icon_size_small': 16,
                'icon_size_large': 24
            }
        }

        self.themes['dark_high_contrast'] = {
            'name': 'Dark High Contrast',
            'colors': {
                'window': '#000000',
                'window_text': '#ffffff',
                'base': '#0a0a0a',
                'alternate_base': '#1a1a1a',
                'text': '#ffffff',
                'button': '#1a1a1a',
                'button_text': '#ffffff',
                'bright_text': '#ffff00',
                'highlight': '#00ff00',
                'highlighted_text': '#000000',
                'link': '#00ffff',
                'link_visited': '#ff00ff',
                'mid': '#808080',
                'shadow': '#000000',
                'light': '#404040',
                'disabled_text': '#808080',
                # Semantic colors
                'primary': '#00ff00',
                'primary_light': '#66ff66',
                'primary_dark': '#00cc00',
                'secondary': '#808080',
                'success': '#00ff00',
                'warning': '#ffff00',
                'danger': '#ff0000',
                'info': '#00ffff'
            },
            'dimensions': {
                'border_radius': 4,
                'padding': 10,
                'padding_small': 6,
                'padding_large': 14,
                'spacing': 10,
                'min_button_height': 36,
                'font_family': 'Segoe UI',
                'font_size': 11,
                'font_size_small': 10,
                'font_size_large': 14,
                'icon_size': 24,
                'icon_size_small': 20,
                'icon_size_large': 28
            }
        }

    def _restore_last_theme(self):
        """前回のテーマを復元"""
        last_theme = self.settings.value("theme", "dark_professional")
        if last_theme in self.themes:
            self.apply_theme(last_theme)
        else:
            self.apply_theme("dark_professional")

    def apply_theme(self, theme_name: str):
        """テーマを適用"""
        if theme_name not in self.themes:
            raise ValueError(f"Unknown theme: {theme_name}")

        # Fusionスタイルを強制（必須）
        self.app.setStyle("Fusion")

        # パレット生成と適用
        palette = self._create_palette(self.themes[theme_name])
        self.app.setPalette(palette)

        # グローバルスタイルシート適用
        qss = self._generate_qss(self.themes[theme_name])
        self.app.setStyleSheet(qss)

        # すべてのウィジェットを再描画
        self._repolish_widgets()

        # 状態を保存
        self.current_theme = theme_name
        self.settings.setValue("theme", theme_name)
        self.theme_changed.emit(theme_name)

    def _create_palette(self, theme: Dict) -> QPalette:
        """テーマ定義からQPaletteを生成"""
        palette = QPalette()

        # 色役割マッピング
        color_roles = {
            'window': QPalette.Window,
            'window_text': QPalette.WindowText,
            'base': QPalette.Base,
            'alternate_base': QPalette.AlternateBase,
            'text': QPalette.Text,
            'button': QPalette.Button,
            'button_text': QPalette.ButtonText,
            'bright_text': QPalette.BrightText,
            'highlight': QPalette.Highlight,
            'highlighted_text': QPalette.HighlightedText,
            'link': QPalette.Link,
            'link_visited': QPalette.LinkVisited,
            'mid': QPalette.Mid,
            'shadow': QPalette.Shadow,
            'light': QPalette.Light
        }

        colors = theme.get('colors', {})
        for key, role in color_roles.items():
            if key in colors:
                palette.setColor(role, QColor(colors[key]))

        # 無効状態の色も設定
        if 'disabled_text' in colors:
            palette.setColor(QPalette.Disabled, QPalette.WindowText,
                           QColor(colors['disabled_text']))
            palette.setColor(QPalette.Disabled, QPalette.ButtonText,
                           QColor(colors['disabled_text']))
            palette.setColor(QPalette.Disabled, QPalette.Text,
                           QColor(colors['disabled_text']))

        return palette

    def _generate_qss(self, theme: Dict) -> str:
        """テーマ定義からQSSを生成"""
        dims = theme.get('dimensions', {})
        colors = theme.get('colors', {})

        qss = f"""
        * {{
            font-family: '{dims.get('font_family', 'Segoe UI')}';
            font-size: {dims.get('font_size', 10)}px;
        }}

        QWidget {{
            background-color: palette(window);
            color: palette(window-text);
        }}

        /* 入力フィールド */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
            background-color: palette(base);
            color: palette(text);
            border: 1px solid palette(mid);
            border-radius: {dims.get('border_radius', 4)}px;
            padding: {dims.get('padding', 6)}px;
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: palette(highlight);
            border-width: 2px;
        }}

        /* ボタン */
        QPushButton {{
            background-color: palette(button);
            color: palette(button-text);
            border: 1px solid palette(mid);
            border-radius: {dims.get('border_radius', 4)}px;
            padding: {dims.get('padding', 6)}px {dims.get('padding_large', 12)}px;
            min-height: {dims.get('min_button_height', 24)}px;
        }}

        QPushButton:hover {{
            background-color: palette(light);
        }}

        QPushButton:pressed {{
            background-color: palette(mid);
        }}

        QPushButton[class="btn-primary"] {{
            background-color: {colors.get('primary', '#2196f3')};
            color: white;
            border: none;
        }}

        QPushButton[class="btn-primary"]:hover {{
            background-color: {colors.get('primary_light', '#64b5f6')};
        }}

        QPushButton[class="btn-primary"]:pressed {{
            background-color: {colors.get('primary_dark', '#1976d2')};
        }}

        /* メニュー */
        QMenu {{
            background-color: palette(base);
            border: 1px solid palette(mid);
            border-radius: {dims.get('border_radius', 4)}px;
            padding: 4px;
        }}

        QMenu::item {{
            padding: {dims.get('padding', 6)}px 24px;
            border-radius: {dims.get('border_radius', 4) - 2}px;
        }}

        QMenu::item:selected {{
            background-color: palette(highlight);
            color: palette(highlighted-text);
        }}

        QMenu::separator {{
            height: 1px;
            background-color: palette(mid);
            margin: 4px 12px;
        }}

        /* リストビュー */
        QListView {{
            background-color: palette(base);
            border: 1px solid palette(mid);
            border-radius: {dims.get('border_radius', 4)}px;
            padding: {dims.get('padding', 6)}px;
            outline: none;
        }}

        QListView::item {{
            border-radius: {dims.get('border_radius', 4) - 2}px;
            padding: {dims.get('padding_small', 4)}px;
        }}

        QListView::item:hover {{
            background-color: palette(alternate-base);
        }}

        QListView::item:selected {{
            background-color: palette(highlight);
            color: palette(highlighted-text);
        }}

        /* スクロールバー */
        QScrollBar:vertical {{
            background-color: palette(base);
            width: 12px;
            border: none;
        }}

        QScrollBar::handle:vertical {{
            background-color: palette(mid);
            border-radius: 6px;
            min-height: 30px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: palette(light);
        }}

        QScrollBar:horizontal {{
            background-color: palette(base);
            height: 12px;
            border: none;
        }}

        QScrollBar::handle:horizontal {{
            background-color: palette(mid);
            border-radius: 6px;
            min-width: 30px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: palette(light);
        }}

        /* コンボボックス */
        QComboBox {{
            background-color: palette(button);
            color: palette(button-text);
            border: 1px solid palette(mid);
            border-radius: {dims.get('border_radius', 4)}px;
            padding: {dims.get('padding', 6)}px;
            min-height: {dims.get('min_button_height', 24)}px;
        }}

        QComboBox:hover {{
            border-color: palette(highlight);
        }}

        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}

        QComboBox QAbstractItemView {{
            background-color: palette(base);
            border: 1px solid palette(mid);
            color: palette(text);
            selection-background-color: palette(highlight);
            selection-color: palette(highlighted-text);
        }}

        /* ツールバー */
        QToolBar {{
            background-color: palette(window);
            border: none;
            border-bottom: 1px solid palette(mid);
            padding: {dims.get('padding', 6)}px;
            spacing: {dims.get('spacing', 6)}px;
        }}

        QToolBar QToolButton {{
            background-color: transparent;
            border: none;
            border-radius: {dims.get('border_radius', 4)}px;
            padding: {dims.get('padding', 6)}px;
        }}

        QToolBar QToolButton:hover {{
            background-color: palette(alternate-base);
        }}

        QToolBar QToolButton:pressed {{
            background-color: palette(mid);
        }}

        /* ステータスバー */
        QStatusBar {{
            background-color: palette(window);
            border-top: 1px solid palette(mid);
            color: palette(window-text);
        }}

        /* フレーム */
        QFrame {{
            background-color: palette(base);
            border: 1px solid palette(mid);
            border-radius: {dims.get('border_radius', 4)}px;
        }}

        /* カードウィジェット */
        QFrame[class="card-widget"] {{
            background-color: palette(base);
            border: 1px solid palette(mid);
            border-radius: {dims.get('border_radius', 4) * 2}px;
            padding: {dims.get('padding_large', 12)}px;
        }}

        /* ラベル */
        QLabel[class="heading1"] {{
            font-size: {dims.get('font_size_large', 12) + 6}px;
            font-weight: bold;
            color: palette(window-text);
        }}

        QLabel[class="heading2"] {{
            font-size: {dims.get('font_size_large', 12) + 2}px;
            font-weight: bold;
            color: palette(window-text);
        }}

        QLabel[class="heading3"] {{
            font-size: {dims.get('font_size_large', 12)}px;
            font-weight: bold;
            color: palette(window-text);
        }}

        QLabel[class="caption"] {{
            font-size: {dims.get('font_size_small', 9)}px;
            color: palette(mid);
        }}
        """

        return qss

    def _repolish_widgets(self):
        """すべてのウィジェットを再描画"""
        for widget in self.app.allWidgets():
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            # Check if widget has update method that takes no arguments
            try:
                widget.update()
            except TypeError:
                # Some widgets might require arguments for update
                pass

    def get_current_theme(self) -> Optional[str]:
        """現在のテーマ名を取得"""
        return self.current_theme

    def get_available_themes(self) -> list:
        """利用可能なテーマのリストを取得"""
        return list(self.themes.keys())

    def get_theme_data(self, theme_name: str) -> Dict:
        """テーマデータを取得"""
        return self.themes.get(theme_name, {})

    def get_color(self, color_name: str) -> QColor:
        """現在のテーマから色を取得"""
        if self.current_theme:
            colors = self.themes[self.current_theme].get('colors', {})
            if color_name in colors:
                color_value = colors[color_name]
                # Handle nested color definitions (like primary.main)
                if isinstance(color_value, dict):
                    color_value = color_value.get('main', '#000000')
                return QColor(color_value)
        return QColor()

    def get_dimension(self, dimension_name: str):
        """現在のテーマから寸法を取得"""
        if self.current_theme:
            dims = self.themes[self.current_theme].get('dimensions', {})
            return dims.get(dimension_name)
        return None

    def save_custom_theme(self, theme_name: str, theme_data: Dict):
        """カスタムテーマを保存"""
        theme_dir = Path("themes")
        theme_dir.mkdir(exist_ok=True)

        theme_file = theme_dir / f"{theme_name}.json"
        with open(theme_file, 'w', encoding='utf-8') as f:
            json.dump(theme_data, f, ensure_ascii=False, indent=2)

        self.themes[theme_name] = theme_data


class ThemedWidget(QWidget):
    """テーマ対応の基底ウィジェットクラス"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.theme_manager = ThemeManager()
        self.theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """テーマ変更時の処理"""
        self.update()
        self._apply_theme_specifics(theme_name)

    def _apply_theme_specifics(self, theme_name: str):
        """テーマ固有の設定を適用（サブクラスでオーバーライド）"""
        pass

    def get_palette_color(self, role: str) -> QColor:
        """パレットから色を取得"""
        role_map = {
            'window': QPalette.Window,
            'window_text': QPalette.WindowText,
            'base': QPalette.Base,
            'alternate_base': QPalette.AlternateBase,
            'text': QPalette.Text,
            'button': QPalette.Button,
            'button_text': QPalette.ButtonText,
            'highlight': QPalette.Highlight,
            'highlighted_text': QPalette.HighlightedText,
            'mid': QPalette.Mid,
            'shadow': QPalette.Shadow,
            'light': QPalette.Light
        }
        return self.palette().color(role_map.get(role, QPalette.Window))

    def paintEvent(self, event):
        """基本的な描画処理"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景を描画
        painter.fillRect(self.rect(), self.palette().color(QPalette.Window))

        # カスタム描画（サブクラスでオーバーライド）
        self._custom_paint(painter)

    def _custom_paint(self, painter: QPainter):
        """カスタム描画処理（サブクラスでオーバーライド）"""
        pass