"""Tag filter panel for FS Link Manager"""

from typing import List, Set
from PySide6.QtCore import Qt, Signal, QRect, QSize, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLayout, QLayoutItem, QSizePolicy
)


class FlowLayout(QLayout):
    """フロー レイアウト - 水平方向に配置し、必要に応じて折り返す

    Qt標準のFlowLayoutパターン実装
    """

    def __init__(self, parent=None, margin=0, hspacing=-1, vspacing=-1):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)

        self._hspacing = hspacing
        self._vspacing = vspacing
        self._item_list: List[QLayoutItem] = []

    def __del__(self):
        """デストラクタ - アイテムをクリア"""
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem):
        """アイテムを追加"""
        self._item_list.append(item)

    def horizontalSpacing(self) -> int:
        """水平スペーシングを取得"""
        if self._hspacing >= 0:
            return self._hspacing
        else:
            return self._smart_spacing(QSizePolicy.PushButton, Qt.Horizontal)

    def verticalSpacing(self) -> int:
        """垂直スペーシングを取得"""
        if self._vspacing >= 0:
            return self._vspacing
        else:
            return self._smart_spacing(QSizePolicy.PushButton, Qt.Vertical)

    def count(self) -> int:
        """アイテム数を取得"""
        return len(self._item_list)

    def itemAt(self, index: int) -> QLayoutItem:
        """指定インデックスのアイテムを取得"""
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem:
        """指定インデックスのアイテムを削除して返す"""
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        """拡張方向を返す"""
        return Qt.Orientations(0)

    def hasHeightForWidth(self) -> bool:
        """幅に応じた高さを持つか"""
        return True

    def heightForWidth(self, width: int) -> int:
        """指定幅での高さを計算"""
        height = self._do_layout(QRect(0, 0, width, 0), test_only=True)
        return height

    def setGeometry(self, rect: QRect):
        """ジオメトリを設定"""
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        """推奨サイズを返す"""
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        """最小サイズを計算"""
        size = QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(),
                     margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        """レイアウト計算・適用の実装

        Args:
            rect: レイアウト領域
            test_only: Trueの場合は高さ計算のみ

        Returns:
            必要な高さ
        """
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(left, top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        for item in self._item_list:
            widget = item.widget()
            hspace = self.horizontalSpacing()
            vspace = self.verticalSpacing()

            next_x = x + item.sizeHint().width() + hspace

            if next_x - hspace > effective_rect.right() and line_height > 0:
                # 次の行へ
                x = effective_rect.x()
                y = y + line_height + vspace
                next_x = x + item.sizeHint().width() + hspace
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y() + bottom

    def _smart_spacing(self, pm: QSizePolicy.ControlType, orientation: Qt.Orientation) -> int:
        """スマートスペーシング計算"""
        parent = self.parent()
        if parent is None:
            return -1
        elif parent.isWidgetType():
            return parent.style().layoutSpacing(
                pm, pm, orientation
            )
        else:
            return parent.spacing()


class TagButton(QPushButton):
    """テーマ対応のタグボタン

    QPalette/QSSベースでテーマカラーを自動適用する
    チェック可能なボタンとして実装
    """

    def __init__(self, tag: str, parent=None):
        super().__init__(tag, parent)
        self.tag = tag
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)

        # テーマシステム統一: プロパティベースでスタイル適用
        self.setProperty("class", "tag-button")
        self.toggled.connect(self._update_style)

    def _update_style(self, checked: bool):
        """選択状態に応じてプロパティを更新"""
        # QPaletteベースで自動的にテーマカラーを適用
        if checked:
            self.setProperty("selected", "true")
        else:
            self.setProperty("selected", "false")

        # スタイルを再適用
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class TagFilterPanel(QWidget):
    """タグフィルタリングパネル(テーマ統一版)

    Signals:
        filter_changed: 選択タグリストが変更された時に発火
    """

    filter_changed = Signal(list)  # List[str]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_tags: Set[str] = set()
        self.tag_buttons: dict[str, TagButton] = {}
        self.all_button: QPushButton = None

        self._setup_ui()

    def _setup_ui(self):
        """UIセットアップ"""
        from .factory import WidgetFactory

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(8)

        # ヘッダー行
        header_layout = QHBoxLayout()

        # WidgetFactory経由でテーマ統一
        self.label = WidgetFactory.create_label(
            "タグで絞り込み:", "caption"
        )
        header_layout.addWidget(self.label)

        # 件数表示
        self.count_label = WidgetFactory.create_label("", "caption")
        header_layout.addStretch()
        header_layout.addWidget(self.count_label)

        layout.addLayout(header_layout)

        # タグボタンエリア(FlowLayout)
        self.tag_container = QWidget()
        self.tag_layout = FlowLayout(self.tag_container, margin=0, hspacing=6, vspacing=6)
        layout.addWidget(self.tag_container)

    def set_available_tags(self, tags: List[str], total_count: int, filtered_count: int):
        """利用可能なタグを設定

        Args:
            tags: タグリスト
            total_count: 総リンク件数
            filtered_count: フィルタ後の件数
        """
        # 既存のボタンをクリア
        for button in self.tag_buttons.values():
            self.tag_layout.removeWidget(button)
            button.deleteLater()
        self.tag_buttons.clear()

        if self.all_button:
            self.tag_layout.removeWidget(self.all_button)
            self.all_button.deleteLater()
            self.all_button = None

        # タグが存在しない場合は非表示
        if not tags:
            self.hide()
            return

        self.show()

        # 「全て」ボタン
        self.all_button = self._create_all_button()
        self.tag_layout.addWidget(self.all_button)

        # 各タグボタンを生成
        for tag in sorted(tags):
            button = TagButton(f"#{tag}")
            button.tag = tag  # 元のタグ名を保存

            # シグナル接続
            button.toggled.connect(lambda checked, t=tag: self._on_tag_toggled(t, checked))

            # 現在選択中のタグがあれば復元(シグナルをブロックして再帰を防ぐ)
            if tag in self.selected_tags:
                button.blockSignals(True)
                button.setChecked(True)
                button._update_style(True)  # 手動でスタイル更新
                button.blockSignals(False)

            self.tag_layout.addWidget(button)
            self.tag_buttons[tag] = button

        # 件数表示更新
        self._update_count_label(total_count, filtered_count)

    def _create_all_button(self) -> QPushButton:
        """「全て」ボタン生成"""
        from .factory import WidgetFactory

        button = WidgetFactory.create_button("⚪全て", "secondary")
        button.setProperty("class", "tag-button-all")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(self.clear_selection)
        return button

    def _on_tag_toggled(self, tag: str, checked: bool):
        """タグの選択/解除

        Args:
            tag: タグ名
            checked: 選択状態
        """
        if checked:
            self.selected_tags.add(tag)
        else:
            self.selected_tags.discard(tag)

        self.filter_changed.emit(list(self.selected_tags))

    def clear_selection(self):
        """選択解除"""
        for button in self.tag_buttons.values():
            button.setChecked(False)
        self.selected_tags.clear()
        self.filter_changed.emit([])

    def get_selected_tags(self) -> List[str]:
        """選択中のタグを取得

        Returns:
            選択中のタグリスト
        """
        return list(self.selected_tags)

    def _update_count_label(self, total: int, filtered: int):
        """件数ラベル更新

        Args:
            total: 総件数
            filtered: フィルタ後の件数
        """
        self.count_label.setText(f"📊 {total}件中 {filtered}件を表示")
