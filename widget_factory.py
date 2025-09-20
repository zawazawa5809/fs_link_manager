"""
Widget Factory for FS Link Manager
Creates themed widgets with consistent styling
"""

from PySide6.QtWidgets import (
    QPushButton, QLineEdit, QLabel, QComboBox,
    QCheckBox, QRadioButton, QGroupBox, QFrame,
    QVBoxLayout, QHBoxLayout, QWidget, QTextEdit,
    QListWidget, QListWidgetItem, QToolButton
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QFont
from typing import Optional, List


class WidgetFactory:
    """統一されたスタイルでウィジェットを生成するファクトリー"""

    @staticmethod
    def create_button(
        text: str,
        button_type: str = "default",
        icon: Optional[QIcon] = None,
        parent: Optional[QWidget] = None
    ) -> QPushButton:
        """スタイル付きボタンを作成"""
        button = QPushButton(text, parent)

        # タイプ別スタイルクラス適用
        style_classes = {
            "default": "btn-default",
            "primary": "btn-primary",
            "secondary": "btn-secondary",
            "success": "btn-success",
            "danger": "btn-danger",
            "warning": "btn-warning",
            "info": "btn-info",
            "ghost": "btn-ghost"
        }

        if button_type in style_classes:
            button.setProperty("class", style_classes[button_type])

        # アイコン設定
        if icon:
            button.setIcon(icon)
            button.setIconSize(QSize(20, 20))

        # 追加のスタイル設定
        button.setCursor(Qt.PointingHandCursor)

        return button

    @staticmethod
    def create_tool_button(
        text: str = "",
        icon: Optional[QIcon] = None,
        checkable: bool = False,
        parent: Optional[QWidget] = None
    ) -> QToolButton:
        """ツールバー用ボタンを作成"""
        button = QToolButton(parent)

        if text:
            button.setText(text)
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        if icon:
            button.setIcon(icon)
            button.setIconSize(QSize(24, 24))

        button.setCheckable(checkable)
        button.setCursor(Qt.PointingHandCursor)
        button.setProperty("class", "tool-button")

        return button

    @staticmethod
    def create_input_field(
        placeholder: str = "",
        input_type: str = "text",
        validator: Optional[object] = None,
        parent: Optional[QWidget] = None
    ) -> QLineEdit:
        """スタイル付き入力フィールドを作成"""
        field = QLineEdit(parent)
        field.setPlaceholderText(placeholder)

        # バリデーター設定
        if validator:
            field.setValidator(validator)

        # タイプ別設定
        if input_type == "password":
            field.setEchoMode(QLineEdit.Password)
        elif input_type == "email":
            from PySide6.QtGui import QRegularExpressionValidator
            from PySide6.QtCore import QRegularExpression
            email_regex = QRegularExpression(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            )
            field.setValidator(QRegularExpressionValidator(email_regex))
        elif input_type == "search":
            field.setPlaceholderText(f"🔍 {placeholder}" if placeholder else "🔍 検索")

        # 統一されたスタイル適用
        field.setProperty("class", "input-field")

        return field

    @staticmethod
    def create_label(
        text: str,
        label_type: str = "default",
        parent: Optional[QWidget] = None
    ) -> QLabel:
        """スタイル付きラベルを作成"""
        label = QLabel(text, parent)

        # タイプ別スタイルクラス
        style_classes = {
            "default": "",
            "heading1": "heading1",
            "heading2": "heading2",
            "heading3": "heading3",
            "caption": "caption",
            "error": "error-label",
            "success": "success-label",
            "warning": "warning-label",
            "info": "info-label"
        }

        if label_type in style_classes and style_classes[label_type]:
            label.setProperty("class", style_classes[label_type])

        return label

    @staticmethod
    def create_combo_box(
        items: List[str],
        current_text: str = "",
        parent: Optional[QWidget] = None
    ) -> QComboBox:
        """スタイル付きコンボボックスを作成"""
        combo = QComboBox(parent)
        combo.addItems(items)

        if current_text and current_text in items:
            combo.setCurrentText(current_text)

        combo.setProperty("class", "combo-box")
        return combo

    @staticmethod
    def create_card_widget(
        title: str = "",
        content: Optional[QWidget] = None,
        actions: Optional[List[QPushButton]] = None,
        collapsible: bool = False,
        parent: Optional[QWidget] = None
    ) -> QFrame:
        """カード型コンテナウィジェット"""
        card = QFrame(parent)
        card.setProperty("class", "card-widget")
        card.setFrameStyle(QFrame.Box)

        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # タイトル
        if title:
            title_layout = QHBoxLayout()

            title_label = WidgetFactory.create_label(title, "heading2")
            title_label.setProperty("class", "card-title")
            title_layout.addWidget(title_label)

            if collapsible:
                collapse_btn = QToolButton()
                collapse_btn.setArrowType(Qt.DownArrow)
                collapse_btn.setProperty("class", "collapse-button")
                title_layout.addWidget(collapse_btn)

            title_layout.addStretch()
            layout.addLayout(title_layout)

            # セパレータ
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setProperty("class", "card-separator")
            layout.addWidget(separator)

        # コンテンツ
        if content:
            layout.addWidget(content)

        # アクションボタン
        if actions:
            action_layout = QHBoxLayout()
            action_layout.addStretch()
            for button in actions:
                action_layout.addWidget(button)
                action_layout.addSpacing(8)
            layout.addLayout(action_layout)

        return card

    @staticmethod
    def create_form_group(
        label_text: str,
        widget: QWidget,
        help_text: str = "",
        required: bool = False,
        parent: Optional[QWidget] = None
    ) -> QWidget:
        """フォームグループ（ラベル付きウィジェット）を作成"""
        container = QWidget(parent)
        layout = QVBoxLayout(container)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        # ラベル
        label_str = label_text
        if required:
            label_str += " *"
        label = WidgetFactory.create_label(label_str)
        label.setProperty("class", "form-label")
        layout.addWidget(label)

        # ウィジェット
        layout.addWidget(widget)

        # ヘルプテキスト
        if help_text:
            help_label = WidgetFactory.create_label(help_text, "caption")
            help_label.setProperty("class", "form-help")
            layout.addWidget(help_label)

        return container

    @staticmethod
    def create_section_widget(
        title: str,
        widgets: List[QWidget],
        parent: Optional[QWidget] = None
    ) -> QGroupBox:
        """セクション（グループボックス）を作成"""
        group = QGroupBox(title, parent)
        group.setProperty("class", "section-widget")

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        for widget in widgets:
            layout.addWidget(widget)

        return group

    @staticmethod
    def create_list_widget(
        items: Optional[List[str]] = None,
        parent: Optional[QWidget] = None
    ) -> QListWidget:
        """スタイル付きリストウィジェットを作成"""
        list_widget = QListWidget(parent)
        list_widget.setProperty("class", "list-widget")
        list_widget.setAlternatingRowColors(True)

        if items:
            for item in items:
                list_widget.addItem(item)

        return list_widget

    @staticmethod
    def create_status_label(
        text: str,
        status_type: str = "info",
        parent: Optional[QWidget] = None
    ) -> QLabel:
        """ステータス表示用ラベルを作成"""
        label = QLabel(text, parent)

        # ステータスタイプ別のアイコンとスタイル
        status_config = {
            "info": ("ℹ️", "status-info"),
            "success": ("✅", "status-success"),
            "warning": ("⚠️", "status-warning"),
            "error": ("❌", "status-error"),
            "loading": ("⏳", "status-loading")
        }

        if status_type in status_config:
            icon, style_class = status_config[status_type]
            label.setText(f"{icon} {text}")
            label.setProperty("class", style_class)

        return label

    @staticmethod
    def create_icon_label(
        icon: QIcon,
        size: QSize = QSize(32, 32),
        parent: Optional[QWidget] = None
    ) -> QLabel:
        """アイコン表示用ラベルを作成"""
        label = QLabel(parent)
        pixmap = icon.pixmap(size)
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)
        return label

    @staticmethod
    def create_separator(
        orientation: Qt.Orientation = Qt.Horizontal,
        parent: Optional[QWidget] = None
    ) -> QFrame:
        """セパレータ（区切り線）を作成"""
        separator = QFrame(parent)
        if orientation == Qt.Horizontal:
            separator.setFrameShape(QFrame.HLine)
        else:
            separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setProperty("class", "separator")
        return separator

    @staticmethod
    def create_text_editor(
        placeholder: str = "",
        read_only: bool = False,
        parent: Optional[QWidget] = None
    ) -> QTextEdit:
        """スタイル付きテキストエディタを作成"""
        editor = QTextEdit(parent)
        editor.setPlaceholderText(placeholder)
        editor.setReadOnly(read_only)
        editor.setProperty("class", "text-editor")

        # フォント設定
        font = QFont("Consolas", 10)
        editor.setFont(font)

        return editor

    @staticmethod
    def apply_shadow_effect(
        widget: QWidget,
        blur_radius: int = 20,
        offset: tuple = (0, 2),
        color: tuple = (0, 0, 0, 30)
    ):
        """ウィジェットに影効果を適用"""
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur_radius)
        shadow.setColor(QColor(*color))
        shadow.setOffset(*offset)
        widget.setGraphicsEffect(shadow)

    @staticmethod
    def create_action_bar(
        actions: List[tuple],  # [(text, icon, callback), ...]
        parent: Optional[QWidget] = None
    ) -> QWidget:
        """アクションバー（ボタングループ）を作成"""
        container = QWidget(parent)
        layout = QHBoxLayout(container)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        for text, icon, callback in actions:
            button = WidgetFactory.create_tool_button(text, icon)
            if callback:
                button.clicked.connect(callback)
            layout.addWidget(button)

        layout.addStretch()
        return container