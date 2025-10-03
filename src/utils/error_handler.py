"""Unified error handling for FS Link Manager"""

import logging
import traceback
from functools import wraps
from typing import Optional, Callable, Any
from PySide6.QtWidgets import QMessageBox, QWidget

from ..i18n import tr


# ロガー設定
logger = logging.getLogger(__name__)


class AppError(Exception):
    """アプリケーション基底例外"""
    def __init__(self, message: str, title: str = None, recoverable: bool = True):
        super().__init__(message)
        self.title = title or tr("dialogs.error_title")
        self.recoverable = recoverable


class DatabaseError(AppError):
    """データベース操作エラー"""
    def __init__(self, message: str):
        super().__init__(message, tr("dialogs.database_error"))


class FileOperationError(AppError):
    """ファイル操作エラー"""
    def __init__(self, message: str):
        super().__init__(message, tr("dialogs.file_error"))


class ValidationError(AppError):
    """バリデーションエラー"""
    def __init__(self, message: str):
        super().__init__(message, tr("dialogs.validation_error"))


class ErrorReporter:
    """エラーレポート・通知管理"""

    @staticmethod
    def report_error(
        error: Exception,
        parent: Optional[QWidget] = None,
        show_dialog: bool = True,
        log_traceback: bool = True
    ):
        """エラーを報告・記録"""
        # ログ記録
        if log_traceback:
            logger.error(f"Error occurred: {error}", exc_info=True)
        else:
            logger.error(f"Error occurred: {error}")

        # ユーザー通知
        if show_dialog:
            if isinstance(error, AppError):
                ErrorReporter._show_error_dialog(
                    parent,
                    error.title,
                    str(error)
                )
            else:
                # 予期しないエラー
                ErrorReporter._show_error_dialog(
                    parent,
                    tr("dialogs.unexpected_error"),
                    f"{type(error).__name__}: {str(error)}"
                )

    @staticmethod
    def _show_error_dialog(parent: Optional[QWidget], title: str, message: str):
        """エラーダイアログを表示"""
        QMessageBox.critical(parent, title, message)

    @staticmethod
    def report_warning(
        message: str,
        parent: Optional[QWidget] = None,
        title: Optional[str] = None
    ):
        """警告を報告"""
        logger.warning(message)
        if parent:
            QMessageBox.warning(
                parent,
                title or tr("dialogs.warning"),
                message
            )

    @staticmethod
    def report_info(
        message: str,
        parent: Optional[QWidget] = None,
        title: Optional[str] = None
    ):
        """情報を報告"""
        logger.info(message)
        if parent:
            QMessageBox.information(
                parent,
                title or tr("dialogs.information"),
                message
            )


def handle_errors(
    show_dialog: bool = True,
    log_traceback: bool = True,
    return_on_error: Any = None
) -> Callable:
    """
    統一エラーハンドリングデコレーター

    使用例:
        @handle_errors(show_dialog=True)
        def some_method(self, parent_widget):
            # 処理
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AppError as e:
                # アプリケーション定義エラー
                parent = _extract_parent_widget(args, kwargs)
                ErrorReporter.report_error(e, parent, show_dialog, log_traceback)
                return return_on_error
            except Exception as e:
                # 予期しないエラー
                parent = _extract_parent_widget(args, kwargs)
                ErrorReporter.report_error(e, parent, show_dialog, log_traceback)
                return return_on_error

        return wrapper
    return decorator


def _extract_parent_widget(args: tuple, kwargs: dict) -> Optional[QWidget]:
    """引数からparent widgetを抽出"""
    # kwargsから探す
    if 'parent_widget' in kwargs:
        return kwargs['parent_widget']
    if 'parent' in kwargs:
        return kwargs['parent']

    # argsから探す（selfの次の引数がparentの場合が多い）
    for arg in args[1:]:  # args[0]はselfなのでスキップ
        if isinstance(arg, QWidget):
            return arg

    return None
