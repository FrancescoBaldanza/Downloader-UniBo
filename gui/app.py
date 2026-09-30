"""
app.py - Entry point per l'applicazione grafica macOS di UniBo Downloader.
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from core.auth import get_current_moodle_session, verify_moodle_session
from gui.login_dialog import LoginDialog
from gui.main_window import MainWindow
from gui.theme import MACOS_STYLE


def launch_gui():
    # Support high-DPI displays
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("UniBo Downloader")
    app.setStyleSheet(MACOS_STYLE)

    icon_path = Path(__file__).resolve().parent / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
        try:
            import Cocoa
            img = Cocoa.NSImage.alloc().initWithContentsOfFile_(str(icon_path))
            if img:
                Cocoa.NSApplication.sharedApplication().setApplicationIconImage_(img)
        except Exception:
            pass

    main_win = MainWindow()

    # Controlla se la sessione Moodle salvata è già valida
    session_cookie = get_current_moodle_session()
    is_authenticated = False
    if session_cookie:
        is_authenticated = verify_moodle_session(session_cookie)

    if not is_authenticated:
        login = LoginDialog()
        login.login_successful.connect(lambda: main_win.show())
        # Mostra login dialog modal
        if login.exec():
            main_win.show()
            main_win.refresh_courses_list()
        else:
            # Utente ha chiuso il login senza autenticarsi
            sys.exit(0)
    else:
        main_win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    launch_gui()
