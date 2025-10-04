"""Main application entry point for FS Link Manager"""

import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from .ui import MainWindow
from .themes import ThemeManager
from .core import SettingsManager
from .i18n import Translator


def setup_logging():
    """Configure logging for the application"""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'app.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def main():
    """Main entry point"""
    logger = setup_logging()
    logger.info("Starting FS Link Manager")

    # Enable high DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("FS Link Manager")
    app.setOrganizationName("FSLinkManager")

    # Initialize managers
    settings_manager = SettingsManager()
    theme_manager = ThemeManager(app)
    translator = Translator()

    # Restore settings from SettingsManager
    theme_manager.restore_theme(settings_manager.settings.theme)
    translator.restore_language(settings_manager.settings.language)

    # Apply initial font settings
    theme_manager.apply_custom_font_size(
        settings_manager.settings.font_size,
        settings_manager.settings.font_scale
    )

    # Create and show main window
    window = MainWindow()
    window.show()

    logger.info("Application started successfully")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())