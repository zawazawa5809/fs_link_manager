"""
Widget Factory for FS Link Manager
Creates themed widgets with consistent styling
"""

from PySide6.QtWidgets import (
    QPushButton, QLineEdit, QLabel, QComboBox, QFrame, QWidget, QToolButton
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
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
            # Don't use emoji for search as it may not render properly on all systems
            field.setPlaceholderText(placeholder if placeholder else "検索")

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
