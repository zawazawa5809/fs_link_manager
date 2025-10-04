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
        self._custom_font_size: Optional[int] = None
        self._initialized = True
        self._load_theme_definitions()

    def _load_theme_definitions(self):
        """テーマ定義をJSONから読み込み"""
        theme_dir = Path(__file__).parent / "data"
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
                'info': '#2196f3',
                # Selection colors (高コントラスト)
                'selection_background': '#2f6fff',
                'selection_text': '#ffffff'
            },
            'dimensions': {
                'border_radius': 6,
                'padding': 8,
                'padding_small': 4,
                'padding_large': 12,
                'spacing': 8,
                'min_button_height': 36,
                'font_family': 'Noto Sans CJK JP, Yu Gothic UI, Meiryo UI, Segoe UI, sans-serif',
                'font_size': 13,
                'font_size_small': 11,
                'font_size_large': 16,
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
                'info': '#00bcd4',
                # Selection colors (高コントラスト)
                'selection_background': '#2196f3',
                'selection_text': '#ffffff'
            },
            'dimensions': {
                'border_radius': 6,
                'padding': 8,
                'padding_small': 4,
                'padding_large': 12,
                'spacing': 8,
                'min_button_height': 36,
                'font_family': 'Noto Sans CJK JP, Yu Gothic UI, Meiryo UI, Segoe UI, sans-serif',
                'font_size': 13,
                'font_size_small': 11,
                'font_size_large': 16,
                'icon_size': 20,
                'icon_size_small': 16,
                'icon_size_large': 24
            }
        }


    def restore_theme(self, theme_name: str):
        """外部から指定されたテーマを復元"""
        if theme_name in self.themes:
            self.apply_theme(theme_name, save=False, preserve_font=False)
        else:
            self.apply_theme("dark_professional", save=False, preserve_font=False)

    def apply_theme(self, theme_name: str, save: bool = True, preserve_font: bool = True):
        """テーマを適用"""
        if theme_name not in self.themes:
            raise ValueError(f"Unknown theme: {theme_name}")

        # Fusionスタイルを強制（必須）
        self.app.setStyle("Fusion")

        # パレット生成と適用
        palette = self._create_palette(self.themes[theme_name])
        self.app.setPalette(palette)

        # グローバルスタイルシート適用
        qss = self._generate_qss(self.themes[theme_name], preserve_font=preserve_font)
        self.app.setStyleSheet(qss)

        # すべてのウィジェットを再描画
        self._repolish_widgets()

        # 状態を更新
        self.current_theme = theme_name

        # シグナル発火（saveフラグに関わらず通知）
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

    def _generate_qss(self, theme: Dict, preserve_font: bool = False) -> str:
        """テーマ定義からQSSを生成（テンプレートベース）"""
        dims = theme.get('dimensions', {}).copy()
        colors = theme.get('colors', {})

        # フォント設定を保持する場合は、現在の設定を使用
        if preserve_font and self._custom_font_size:
            dims['font_size'] = self._custom_font_size
            dims['font_size_small'] = max(9, self._custom_font_size - 2)
            dims['font_size_large'] = self._custom_font_size + 3



        # QSSテンプレートを読み込み
        template_path = Path(__file__).parent / "data" / "base_styles.qss"
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                qss_template = f.read()
        except FileNotFoundError:
            # Fallback to minimal inline template
            return self._generate_qss_fallback(theme)

        # テンプレート変数を置換
        replacements = {
            'font_family': dims.get('font_family', 'Segoe UI'),
            'font_size': dims.get('font_size', 10),
            'border_radius': dims.get('border_radius', 4),
            'border_radius_small': dims.get('border_radius', 4) - 2,
            'border_radius_card': dims.get('border_radius', 4) * 2,
            'padding': dims.get('padding', 6),
            'padding_small': dims.get('padding_small', 4),
            'padding_large': dims.get('padding_large', 12),
            'spacing': dims.get('spacing', 6),
            'min_button_height': dims.get('min_button_height', 24),
            'font_size_small': dims.get('font_size_small', 9),
            'font_heading1': dims.get('font_size_large', 12) + 6,
            'font_heading2': dims.get('font_size_large', 12) + 2,
            'font_heading3': dims.get('font_size_large', 12),
            'color_primary': colors.get('primary', '#2196f3'),
            'color_primary_light': colors.get('primary_light', '#64b5f6'),
            'color_primary_dark': colors.get('primary_dark', '#1976d2'),
        }

        # テンプレート変数を置換
        qss = qss_template
        for key, value in replacements.items():
            qss = qss.replace(f'${{{key}}}', str(value))

        return qss

    def _generate_qss_fallback(self, theme: Dict) -> str:
        """Fallback QSS generation (minimal inline version)"""
        dims = theme.get('dimensions', {})
        return f"""
        * {{
            font-family: '{dims.get('font_family', 'Segoe UI')}';
            font-size: {dims.get('font_size', 10)}px;
        }}
        QWidget {{
            background-color: palette(window);
            color: palette(window-text);
        }}
        """

    def _repolish_widgets(self):
        """すべてのウィジェットを再描画（最適化版）"""
        # トップレベルウィジェットのみ処理し、カスケードさせる
        for widget in self.app.topLevelWidgets():
            if widget.isVisible():
                self._repolish_widget_tree(widget)

    def _repolish_widget_tree(self, widget: QWidget):
        """ウィジェットツリーを再帰的に再描画"""
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        try:
            widget.update()
        except TypeError:
            pass

        # 子ウィジェットも処理（visible のみ）
        for child in widget.findChildren(QWidget):
            if child.isVisible():
                child.style().unpolish(child)
                child.style().polish(child)
                try:
                    child.update()
                except TypeError:
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

    def apply_custom_font_size(self, base_size: int, scale: float = 1.0):
        """カスタムフォントサイズを適用"""
        if not self.current_theme:
            return

        # カスタムフォントサイズを記録
        effective_size = int(base_size * scale)
        self._custom_font_size = effective_size

        # QSSを再生成して適用（フォント設定を保持）
        theme = self.themes[self.current_theme]
        qss = self._generate_qss(theme, preserve_font=True)
        self.app.setStyleSheet(qss)

        # ウィジェットを再描画
        self._repolish_widgets()


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