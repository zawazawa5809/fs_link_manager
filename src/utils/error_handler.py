"""Unified error handling for FS Link Manager"""

import logging
import traceback
from functools import wraps
from typing import Optional, Callable, Any
from PySide6.QtWidgets import QMessageBox, QWidget

from ..i18n import tr


# Logger configuration
logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base exception for application-specific errors.

    Attributes:
        message: Human-readable error message
        title: Dialog title for user notifications
        recoverable: Whether the error allows continuation
    """
    def __init__(self, message: str, title: Optional[str] = None, recoverable: bool = True) -> None:
        """Initialize application error.

        Args:
            message: Error description
            title: Optional custom dialog title
            recoverable: Whether app can continue after error
        """
        super().__init__(message)
        self.title = title or tr("dialogs.error_title")
        self.recoverable = recoverable


class DatabaseError(AppError):
    """Database operation error."""
    def __init__(self, message: str) -> None:
        """Initialize database error.

        Args:
            message: Error description
        """
        super().__init__(message, tr("dialogs.database_error"))


class FileOperationError(AppError):
    """File system operation error."""
    def __init__(self, message: str) -> None:
        """Initialize file operation error.

        Args:
            message: Error description
        """
        super().__init__(message, tr("dialogs.file_error"))


class ValidationError(AppError):
    """Data validation error."""
    def __init__(self, message: str) -> None:
        """Initialize validation error.

        Args:
            message: Error description
        """
        super().__init__(message, tr("dialogs.validation_error"))


class ErrorReporter:
    """Error reporting and notification management.

    Provides centralized error handling with logging and user notifications.
    """

    @staticmethod
    def report_error(
        error: Exception,
        parent: Optional[QWidget] = None,
        show_dialog: bool = True,
        log_traceback: bool = True
    ) -> None:
        """Report and log error with optional user notification.

        Args:
            error: Exception to report
            parent: Parent widget for dialog (optional)
            show_dialog: Whether to show error dialog
            log_traceback: Whether to log full traceback
        """
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
    def _show_error_dialog(parent: Optional[QWidget], title: str, message: str) -> None:
        """Display error dialog to user.

        Args:
            parent: Parent widget
            title: Dialog title
            message: Error message
        """
        QMessageBox.critical(parent, title, message)

    @staticmethod
    def report_warning(
        message: str,
        parent: Optional[QWidget] = None,
        title: Optional[str] = None
    ) -> None:
        """Report warning message.

        Args:
            message: Warning description
            parent: Parent widget for dialog
            title: Optional custom title
        """
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
    ) -> None:
        """Report informational message.

        Args:
            message: Information to display
            parent: Parent widget for dialog
            title: Optional custom title
        """
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
    """Unified error handling decorator.

    Automatically catches and reports exceptions with optional user notifications.

    Args:
        show_dialog: Whether to show error dialog to user
        log_traceback: Whether to log full stack trace
        return_on_error: Value to return if error occurs

    Returns:
        Decorator function

    Example:
        @handle_errors(show_dialog=True)
        def some_method(self, parent_widget):
            # Implementation
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
    """Extract parent widget from function arguments.

    Args:
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Parent QWidget if found, None otherwise
    """
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
