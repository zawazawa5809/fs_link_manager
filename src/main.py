"""Main application entry point for FS Link Manager"""

import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from .ui import MainWindow
from .themes import ThemeManager


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

    # Initialize theme manager
    theme_manager = ThemeManager(app)

    # Create and show main window
    window = MainWindow()
    window.show()

    logger.info("Application started successfully")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())