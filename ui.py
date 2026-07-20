from __future__ import annotations

import sys
from datetime import date

from PySide6.QtCore import QPoint, Qt, Signal, QDate, QRectF
from PySide6.QtGui import (
    QCursor,
    QDesktopServices,
    QFont,
    QIcon,
    QColor,
    QPainter,
    QPainterPath,
    QRegion,
)
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QCalendarWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from database import Database


def modern_stylesheet() -> str:
    dark = QApplication.palette().window().color().lightness() < 128
    if dark:
        panel = "#26262a"
        field = "#35353a"
        border = "#505057"
        text = "#f5f5f7"
        muted = "#a1a1a6"
    else:
        panel = "#fafafc"
        field = "#f0f0f3"
        border = "#d1d1d6"
        text = "#1d1d1f"
        muted = "#6e6e73"

    return (
        f"QDialog {{ background: {panel}; color: {text}; "
        f"border: 1px solid {border}; border-radius: 18px; }}"
        f"QLabel {{ color: {text}; }}"
        f"QLineEdit {{ background: {field}; color: {text}; border: 1px solid {border}; "
        "border-radius: 12px; padding: 11px 13px; min-height: 22px; "
        f"selection-background-color: #3478f6; }}"
        f"QLineEdit:focus {{ border: 2px solid #3478f6; padding: 10px 12px; }}"
        "QPushButton { background: #3478f6; color: white; border: none; "
        "border-radius: 11px; padding: 10px 18px; min-height: 22px; "
        "font-weight: 600; }"
        "QPushButton:hover { background: #2563d8; }"
        "QPushButton:pressed { background: #1d4fae; }"
        f"QPushButton#calendarNavButton {{ background: transparent; color: #3478f6; "
        "border: none; border-radius: 16px; padding: 0; min-width: 32px; min-height: 32px; "
        "font-size: 28px; font-weight: 400; }"
        f"QPushButton#calendarNavButton:hover {{ background: {field}; }}"
        f"QPushButton#secondaryButton {{ background: {field}; color: {text}; "
        f"border: 1px solid {border}; }}"
        f"QPushButton#secondaryButton:hover {{ background: {border}; }}"
        f"QListWidget {{ background: transparent; color: {text}; border: none; }}"
        "QListWidget::item { background: transparent; border-radius: 10px; }"
        f"QCalendarWidget {{ background: transparent; color: {text}; }}"
        f"QCalendarWidget QAbstractItemView {{ background: transparent; color: {text}; "
        "outline: 0; selection-background-color: transparent; }"
        f"QCalendarWidget QHeaderView::section {{ background: transparent; color: {muted}; "
        "border: none; padding: 0 0 6px 0; font-weight: 600; }"
        f"QLabel#secondaryLabel {{ color: {muted}; }}"
    )


def asset_path(name: str) -> str:
    root = getattr(sys, "_MEIPASS", ".")
    return f"{root}/assets/{name}"


class ActivityRow(QWidget):
    """A naturally sized activity row that wraps long text."""

    def __init__(self, timestamp: str, activity: str, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(12)

        time_label = QLabel(timestamp)
        time_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        time_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        time_label.setMinimumWidth(48)
        layout.addWidget(time_label)

        activity_label = QLabel(activity)
        activity_label.setWordWrap(True)
        activity_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        activity_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(activity_label, 1)


class RoundedDialog(QDialog):
    """A dialog whose native window surface is clipped to rounded corners."""

    corner_radius = 18.0

    def _update_corner_mask(self) -> None:
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self.corner_radius, self.corner_radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_corner_mask()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._update_corner_mask()


class IOSCalendar(QCalendarWidget):
    """A compact month calendar with iOS-style selection and activity dots."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._activity_counts: dict[date, int] = {}
        self.setGridVisible(False)
        self.setNavigationBarVisible(False)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
        self.setFixedHeight(255)
        self.selectionChanged.connect(self.updateCells)

    def set_activity_counts(self, counts: dict[date, int]) -> None:
        self._activity_counts = counts
        self.updateCells()

    def paintCell(self, painter: QPainter, rect, qdate: QDate) -> None:
        painter.save()
        is_dark = self.palette().window().color().lightness() < 128
        is_current_month = (
            qdate.year() == self.yearShown() and qdate.month() == self.monthShown()
        )
        is_selected = qdate == self.selectedDate()
        log_date = date(qdate.year(), qdate.month(), qdate.day())
        has_activity = log_date in self._activity_counts

        if not is_current_month:
            text_color = QColor("#636369" if is_dark else "#c7c7cc")
        elif qdate.dayOfWeek() in (6, 7):
            text_color = QColor("#a1a1a6" if is_dark else "#8e8e93")
        else:
            text_color = QColor("#f5f5f7" if is_dark else "#1c1c1e")

        font = painter.font()
        font.setBold(is_selected)
        painter.setFont(font)
        painter.setPen(text_color)
        text_rect = rect.adjusted(0, -5 if has_activity and not is_selected else 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignCenter, str(qdate.day()))

        if is_selected:
            accent = QColor("#0a84ff" if is_dark else "#007aff")
            painter.setPen(Qt.NoPen)
            painter.setBrush(accent)
            painter.drawRoundedRect(
                QRectF(rect.center().x() - 10, rect.bottom() - 8, 20, 3), 1.5, 1.5
            )
        elif has_activity:
            dot_color = QColor("#98989d" if is_dark else "#c7c7cc")
            painter.setPen(Qt.NoPen)
            painter.setBrush(dot_color)
            painter.drawEllipse(rect.center().x() - 2, rect.bottom() - 9, 4, 4)
        painter.restore()


class TodayWindow(RoundedDialog):
    """Compact activity capture window, similar to a menu-bar checklist popup."""

    history_requested = Signal()
    quit_requested = Signal()

    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("YeahBouy")
        self.setMinimumSize(390, 480)
        self.setStyleSheet(modern_stylesheet())
        # Qt.Popup treats the tray click that opened it as an outside click on
        # macOS, causing a first-click show/hide race. A tool window lets us
        # control visibility explicitly from the tray activation callback.
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(12)
        heading = QLabel("YeahBouy")
        heading.setFont(QFont("", 16, QFont.Bold))
        layout.addWidget(heading)

        self.activity = QLineEdit()
        self.activity.setPlaceholderText("Add activity")
        self.activity.returnPressed.connect(self.add_activity)
        layout.addWidget(self.activity)

        add_button = QPushButton("Log activity")
        add_button.clicked.connect(self.add_activity)
        layout.addWidget(add_button)

        self.date_label = QLabel()
        self.date_label.setObjectName("secondaryLabel")
        layout.addWidget(self.date_label)

        self.list = QListWidget()
        self.list.setSpacing(2)
        self.list.setWordWrap(True)
        self.list.setUniformItemSizes(False)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.list)

        actions = QHBoxLayout()
        history = QPushButton("History")
        history.clicked.connect(self.history_requested.emit)
        quit_button = QPushButton("Quit")
        quit_button.setObjectName("secondaryButton")
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
            item = QListWidgetItem(self.list)
            row = ActivityRow(f"{log.entered_at:%H:%M}", log.activity)
            item.setSizeHint(row.sizeHint())
            self.list.setItemWidget(item, row)


class HistoryWindow(QDialog):
    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("YeahBouy history")
        self.resize(760, 560)
        self.setStyleSheet(modern_stylesheet())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(12)

        calendar_header = QHBoxLayout()
        calendar_header.setContentsMargins(0, 0, 0, 0)
        calendar_header.setSpacing(8)
        previous_month = QPushButton("‹")
        previous_month.setObjectName("calendarNavButton")
        previous_month.clicked.connect(lambda: self.calendar.showPreviousMonth())
        self.month_label = QLabel()
        self.month_label.setAlignment(Qt.AlignCenter)
        self.month_label.setFont(QFont("", 15, QFont.DemiBold))
        next_month = QPushButton("›")
        next_month.setObjectName("calendarNavButton")
        next_month.clicked.connect(lambda: self.calendar.showNextMonth())
        calendar_header.addWidget(previous_month)
        calendar_header.addWidget(self.month_label, 1)
        calendar_header.addWidget(next_month)
        layout.addLayout(calendar_header)

        self.calendar = IOSCalendar()
        self.calendar.clicked.connect(self.show_selected_day)
        self.calendar.currentPageChanged.connect(self.refresh_calendar)
        layout.addWidget(self.calendar)

        self.day_label = QLabel()
        self.day_label.setFont(QFont("", 13, QFont.Bold))
        layout.addWidget(self.day_label)

        self.list = QListWidget()
        self.list.setWordWrap(True)
        self.list.setUniformItemSizes(False)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.list)

        open_markdown = QPushButton("Open selected day’s Markdown")
        open_markdown.clicked.connect(self.open_markdown)
        layout.addWidget(open_markdown)
        self.refresh()

    def refresh(self) -> None:
        self.refresh_calendar(self.calendar.yearShown(), self.calendar.monthShown())
        self.show_selected_day(self.calendar.selectedDate())

    def refresh_calendar(self, year: int, month: int) -> None:
        self.month_label.setText(QDate(year, month, 1).toString("MMMM yyyy"))
        self.calendar.set_activity_counts(self.db.activity_counts_for_month(year, month))

    def show_selected_day(self, qdate) -> None:
        selected = date(qdate.year(), qdate.month(), qdate.day())
        logs = self.db.activities_for_date(selected)
        self.day_label.setText(
            f"{selected:%A, %B %-d, %Y} · {len(logs)} log{'s' if len(logs) != 1 else ''}"
        )
        self.list.clear()
        for log in logs:
            item = QListWidgetItem(self.list)
            row = ActivityRow(f"{log.entered_at:%H:%M}", log.activity)
            item.setSizeHint(row.sizeHint())
            self.list.setItemWidget(item, row)

    def open_markdown(self) -> None:
        qdate = self.calendar.selectedDate()
        selected = date(qdate.year(), qdate.month(), qdate.day())
        path = self.db.file_path_for_date(selected)
        if not path.exists():
            QMessageBox.information(self, "No Markdown log", "No Markdown log exists for the selected day.")
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
