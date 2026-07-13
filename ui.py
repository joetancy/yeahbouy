from __future__ import annotations

import sys

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QCursor, QDesktopServices, QFont, QIcon
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
)

from database import Database


def asset_path(name: str) -> str:
    root = getattr(sys, "_MEIPASS", ".")
    return f"{root}/assets/{name}"


class TodayWindow(QDialog):
    """Compact activity capture window, similar to a menu-bar checklist popup."""

    history_requested = Signal()
    quit_requested = Signal()

    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("YeahBouy")
        self.setMinimumSize(360, 460)
        # Qt.Popup treats the tray click that opened it as an outside click on
        # macOS, causing a first-click show/hide race. A tool window lets us
        # control visibility explicitly from the tray activation callback.
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setStyleSheet(
            "QDialog { background: #242424; color: #f2f2f2; }"
            "QLabel { color: #f2f2f2; }"
            "QLineEdit { background: #303030; color: #f2f2f2; border: none; border-radius: 10px; padding: 10px; }"
            "QPushButton { background: #4c78ff; color: white; border: none; border-radius: 8px; padding: 8px 12px; }"
            "QListWidget { background: #242424; color: #f2f2f2; border: none; }"
        )

        layout = QVBoxLayout(self)
        heading = QLabel("YeahBouy")
        heading.setFont(QFont("Helvetica", 16, QFont.Bold))
        layout.addWidget(heading)

        self.activity = QLineEdit()
        self.activity.setPlaceholderText("Add activity")
        self.activity.returnPressed.connect(self.add_activity)
        layout.addWidget(self.activity)

        add_button = QPushButton("Log activity")
        add_button.clicked.connect(self.add_activity)
        layout.addWidget(add_button)

        self.date_label = QLabel()
        self.date_label.setStyleSheet("color: #777; padding-top: 8px;")
        layout.addWidget(self.date_label)

        self.list = QListWidget()
        self.list.setSpacing(6)
        self.list.setStyleSheet(
            "QListWidget { border: none; } QListWidget::item { padding: 8px 4px; }"
        )
        layout.addWidget(self.list)

        actions = QHBoxLayout()
        history = QPushButton("History")
        history.clicked.connect(self.history_requested.emit)
        quit_button = QPushButton("Quit")
        quit_button.clicked.connect(self.quit_requested.emit)
        actions.addWidget(history)
        actions.addWidget(quit_button)
        layout.addLayout(actions)
        self.refresh()

    def add_activity(self) -> None:
        activity = self.activity.text().strip()
        if not activity:
            return
        self.db.add_activity(activity)
        self.activity.clear()
        self.refresh()

    def refresh(self) -> None:
        logs = self.db.today_activities()
        self.date_label.setText(f"Today · {len(logs)} log{'s' if len(logs) != 1 else ''}")
        self.list.clear()
        for log in logs:
            item = QListWidgetItem(f"{log.entered_at:%H:%M}\n{log.activity}")
            item.setFont(QFont("Helvetica", 12))
            self.list.addItem(item)


class HistoryWindow(QDialog):
    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("YeahBouy history")
        self.resize(650, 500)
        layout = QVBoxLayout(self)
        self.list = QListWidget()
        layout.addWidget(self.list)
        open_markdown = QPushButton("Open today’s Markdown")
        open_markdown.clicked.connect(self.open_markdown)
        layout.addWidget(open_markdown)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for log in self.db.recent_activities():
            self.list.addItem(QListWidgetItem(f"{log.entered_at:%Y-%m-%d %H:%M}\n{log.activity}"))

    def open_markdown(self) -> None:
        path = self.db.today_file_path()
        if not path.exists():
            QMessageBox.information(self, "No Markdown log", "Today’s Markdown file will be created when you log an activity.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


class WorkLogApp:
    def __init__(self, app: QApplication) -> None:
        self.app, self.db = app, Database()
        self.today = TodayWindow(self.db)
        self.today.history_requested.connect(self.show_history)
        self.today.quit_requested.connect(self.app.quit)
        self.history = None
        self.tray = QSystemTrayIcon(QIcon(asset_path("checkpoint-menubar.svg")), app)
        self.tray.setToolTip("YeahBouy")
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        # macOS can report more than one activation reason for a single
        # status-bar click. Always showing here prevents the second event
        # from immediately hiding the panel again.
        if reason == QSystemTrayIcon.Trigger:
            self.show_today()

    def show_today(self) -> None:
        self.today.refresh()
        self.today.adjustSize()
        tray_rect = self.tray.geometry()
        if tray_rect.isValid() and not tray_rect.isEmpty():
            position = QPoint(
                tray_rect.center().x() - self.today.width() // 2,
                tray_rect.bottom() + 8,
            )
        else:
            cursor = QCursor.pos()
            position = QPoint(
                cursor.x() - self.today.width() // 2,
                cursor.y() + 8,
            )
        self.today.move(position)
        self.today.show()
        self.today.raise_()
        self.today.activateWindow()
        self.today.activity.setFocus()

    def show_history(self) -> None:
        self.history = HistoryWindow(self.db)
        self.history.show()
        self.history.raise_()
        self.history.activateWindow()
