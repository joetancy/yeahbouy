from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from ui import WorkLogApp, asset_path


def main() -> None:
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(asset_path("yeahbouy-mark.png")))
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "YeahBouy", "No system tray is available on this system.")
        raise SystemExit(1)
    app.setQuitOnLastWindowClosed(False)
    worklog = WorkLogApp(app)
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
