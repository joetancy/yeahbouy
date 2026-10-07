from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal, QDate, QRectF
from PySide6.QtGui import (
    QCursor,
    QDesktopServices,
    QIcon,
    QColor,
    QPainter,
    QPainterPath,
    QPalette,
    QRegion,
    QTextCharFormat,
)
from PySide6.QtCore import QSettings, QUrl
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QCalendarWidget,
    QFileDialog,
    QFrame,
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


def modern_stylesheet(force_dark: bool = False) -> str:
    dark = force_dark or QApplication.palette().window().color().lightness() < 128
    if dark:
        panel = "#202630"
        field = "#303640"
        border = "#3c424a"
        text = "#f5f5f7"
        muted = "#abb6c7"
    else:
        panel = "#edf2f8"
        field = "#f8fafc"
        border = "#d3dae5"
        text = "#1d1d1f"
        muted = "#6e6e73"

    return (
        f"QDialog {{ background: {panel}; color: {text}; "
        f"border: 1px solid {border}; border-radius: 20px; }}"
        f"QLabel {{ color: {text}; background: transparent; font-size: 13px; }}"
        f"QLineEdit {{ background: {field}; color: {text}; border: 1px solid {border}; "
        "border-radius: 12px; padding: 10px 12px; min-height: 20px; font-size: 14px; "
        f"selection-background-color: #3478f6; }}"
        f"QLineEdit:focus {{ border: 2px solid #7eb6ff; padding: 9px 11px; }}"
        "QPushButton { background: #3478ed; color: white; border: 1px solid #83b3ff; "
        "border-radius: 12px; padding: 8px 12px; min-height: 20px; "
        "font-size: 13px; font-weight: 600; }"
        "QPushButton:hover { background: #619fff; }"
        "QPushButton:pressed { background: #1d4fae; }"
        "QPushButton:focus { border: 2px solid #b4d5ff; padding: 7px 11px; }"
        f"QPushButton#calendarNavButton {{ background: transparent; color: #3478f6; "
        "border: none; border-radius: 12px; padding: 0; min-width: 36px; min-height: 36px; "
        "font-size: 24px; font-weight: 400; }"
        f"QPushButton#calendarNavButton:hover {{ background: {field}; }}"
        f"QPushButton#dayNavButton {{ background: transparent; color: #3478f6; "
        f"border: 1px solid {border}; border-radius: 12px; padding: 0; min-width: 36px; min-height: 36px; "
        "font-size: 24px; font-weight: 400; }"
        f"QPushButton#dayNavButton:hover {{ background: {field}; }}"
        f"QPushButton#dayNavButton:disabled {{ color: {muted}; }}"
        f"QPushButton#secondaryButton {{ background: {field}; color: {text}; "
        f"border: 1px solid {border}; }}"
        f"QPushButton#secondaryButton:hover {{ background: {border}; }}"
        f"QPushButton#utilityButton {{ background: {field}; color: {text}; border: 1px solid {border}; "
        "border-radius: 12px; padding: 8px 12px; min-height: 20px; font-size: 12px; }"
        f"QPushButton#utilityButton:hover {{ background: {border}; }}"
        f"QListWidget {{ background: transparent; color: {text}; border: none; }}"
        "QScrollBar:vertical { background: transparent; width: 6px; margin: 0; }"
        f"QScrollBar::handle:vertical {{ background: {border}; border-radius: 3px; min-height: 24px; }}"
        "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }"
        "QListWidget::item { background: transparent; border: none; padding: 0; }"
        f"QFrame#activityCard {{ background: {field}; border: 1px solid {border}; border-radius: 14px; }}"
        "QFrame#timelineDot { background: #8abaff; border: none; border-radius: 4px; }"
        f"QFrame#timelineLine {{ background: {border}; border: none; max-width: 2px; }}"
        f"QLabel#activityTime {{ color: {'#9cc5ff' if dark else '#2468c5'}; font-size: 12px; font-weight: 600; }}"
        f"QCalendarWidget {{ background: transparent; color: {text}; }}"
        f"QCalendarWidget QAbstractItemView {{ background: transparent; color: {text}; "
        "outline: 0; selection-background-color: transparent; }"
        f"QCalendarWidget QHeaderView::section {{ background: transparent; color: {muted}; "
        "border: none; padding: 0 0 6px 0; font-weight: 600; }"
        f"QFrame#separator {{ background: {border}; border: none; max-height: 1px; }}"
        f"QLabel#titleLabel {{ color: {muted}; font-size: 12px; font-weight: 600; }}"
        "QLabel#dateHeading { font-size: 20px; font-weight: 700; }"
        "QLabel#promptLabel { font-size: 13px; font-weight: 600; }"
        "QLabel#sectionHeading { font-size: 14px; font-weight: 600; }"
        f"QLabel#tipLabel {{ color: {muted}; font-size: 11px; }}"
        f"QLabel#secondaryLabel {{ color: {muted}; font-size: 13px; }}"
    )


def asset_path(name: str) -> str:
    root = getattr(sys, "_MEIPASS", ".")
    return f"{root}/assets/{name}"


class ActivityRow(QWidget):
    """A selectable activity card with a timeline marker."""

    def __init__(self, timestamp: str, activity: str, last: bool = False, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        timeline = QVBoxLayout()
        timeline.setContentsMargins(0, 16, 0, 0)
        timeline.setSpacing(0)
        dot = QFrame()
        dot.setObjectName("timelineDot")
        dot.setFixedSize(8, 8)
        line = QFrame()
        line.setObjectName("timelineLine")
        line.setFrameShape(QFrame.VLine)
        line.setVisible(not last)
        timeline.addWidget(dot, 0, Qt.AlignHCenter)
        timeline.addWidget(line, 1, Qt.AlignHCenter)
        layout.addLayout(timeline)

        card = QFrame()
        card.setObjectName("activityCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(12)

        time_label = QLabel(timestamp)
        time_label.setObjectName("activityTime")
        time_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        time_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        time_label.setMinimumWidth(46)
        card_layout.addWidget(time_label)

        activity_label = QLabel(activity)
        activity_label.setWordWrap(True)
        activity_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        activity_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card_layout.addWidget(activity_label, 1)
        layout.addWidget(card, 1)

    def sizeHint(self):
        size = super().sizeHint()
        if isinstance(self.parentWidget(), QListWidget):
            width = self.parentWidget().contentsRect().width() - 2 * self.parentWidget().spacing()
            size.setWidth(0)
            size.setHeight(self.layout().heightForWidth(width))
        return size


class RoundedDialog(QDialog):
    """A dialog whose native window surface is clipped to rounded corners."""

    corner_radius = 20.0

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
        self.setFixedHeight(224)
        weekday_format = QTextCharFormat()
        weekday_format.setForeground(QColor("#abb6c7"))
        weekday_format.setBackground(QColor("#29313d"))
        for weekday in (Qt.Monday, Qt.Tuesday, Qt.Wednesday, Qt.Thursday, Qt.Friday, Qt.Saturday, Qt.Sunday):
            self.setWeekdayTextFormat(weekday, weekday_format)
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
    """Activity capture panel with a timeline-style daily log."""

    history_requested = Signal()
    folder_requested = Signal()
    quit_requested = Signal()

    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.selected_date = date.today()
        self.setWindowTitle("YeahBouy")
        self.setMinimumSize(400, 520)
        self.resize(440, 620)
        self.setStyleSheet(modern_stylesheet(force_dark=True))
        # Qt.Popup treats the tray click that opened it as an outside click on
        # macOS, causing a first-click show/hide race. A tool window lets us
        # control visibility explicitly from the tray activation callback.
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        heading = QLabel("YeahBouy")
        heading.setObjectName("titleLabel")
        layout.addWidget(heading)

        self.today_label = QLabel()
        self.today_label.setObjectName("dateHeading")
        layout.addWidget(self.today_label)

        prompt = QLabel("What did you work on?")
        prompt.setObjectName("promptLabel")
        layout.addWidget(prompt)

        self.activity = QLineEdit()
        self.activity.setPlaceholderText("Add activity...")
        self.activity.returnPressed.connect(self.add_activity)
        layout.addWidget(self.activity)

        capture_actions = QHBoxLayout()
        capture_actions.setContentsMargins(0, 0, 0, 0)
        tip = QLabel("Tip: Press Enter to log activity")
        tip.setObjectName("tipLabel")
        capture_actions.addWidget(tip, 1)
        add_button = QPushButton("Log activity")
        add_button.clicked.connect(self.add_activity)
        capture_actions.addWidget(add_button)
        layout.addLayout(capture_actions)

        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)

        day_navigation = QHBoxLayout()
        day_navigation.setContentsMargins(0, 0, 0, 0)
        previous_day = QPushButton("‹")
        previous_day.setObjectName("dayNavButton")
        previous_day.setAccessibleName("Previous day")
        previous_day.setToolTip("Previous day")
        previous_day.clicked.connect(self.show_previous_day)
        self.selected_date_label = QLabel()
        self.selected_date_label.setAlignment(Qt.AlignCenter)
        self.selected_date_label.setObjectName("sectionHeading")
        self.next_day = QPushButton("›")
        self.next_day.setObjectName("dayNavButton")
        self.next_day.setAccessibleName("Next day")
        self.next_day.setToolTip("Next day")
        self.next_day.clicked.connect(self.show_next_day)
        day_navigation.addWidget(previous_day)
        day_navigation.addWidget(self.selected_date_label, 1)
        day_navigation.addWidget(self.next_day)
        layout.addLayout(day_navigation)

        self.list = QListWidget()
        self.list.setSpacing(8)
        self.list.setWordWrap(True)
        self.list.setUniformItemSizes(False)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.list, 1)
        self.empty_state = QLabel("No activities for this day yet.")
        self.empty_state.setObjectName("secondaryLabel")
        self.empty_state.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_state, 1)

        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(8)
        history = QPushButton("History")
        history.setObjectName("utilityButton")
        history.setAccessibleName("Activity history")
        history.setToolTip("Activity history")
        history.clicked.connect(self.history_requested.emit)
        self.folder_button = QPushButton("Folder")
        self.folder_button.setObjectName("utilityButton")
        self.folder_button.setAccessibleName("Choose Markdown folder")
        self.folder_button.clicked.connect(self.folder_requested.emit)
        self.quit_button = QPushButton("Quit")
        self.quit_button.setObjectName("utilityButton")
        self.quit_button.setAccessibleName("Quit YeahBouy")
        self.quit_button.setToolTip("Quit YeahBouy")
        self.quit_button.clicked.connect(self.quit_requested.emit)
        actions.addWidget(history)
        actions.addWidget(self.folder_button)
        actions.addStretch(1)
        actions.addWidget(self.quit_button)
        layout.addLayout(actions)
        layout.activate()
        self.refresh()

    def add_activity(self) -> None:
        activity = self.activity.text().strip()
        if not activity:
            return
        try:
            self.db.add_activity(activity)
        except OSError as error:
            QMessageBox.critical(self, "Could not save activity", str(error))
            return
        self.activity.clear()
        self.selected_date = date.today()
        self.refresh()

    def refresh(self) -> None:
        today = date.today()
        if self.selected_date > today:
            self.selected_date = today
        self.today_label.setText(
            QDate(today.year, today.month, today.day).toString("dddd, MMMM d")
        )
        logs = self.db.activities_for_date(self.selected_date)
        selected_qdate = QDate(
            self.selected_date.year, self.selected_date.month, self.selected_date.day
        )
        day_name = "Today" if self.selected_date == today else selected_qdate.toString("ddd, MMM d")
        self.selected_date_label.setText(
            f"{day_name} · {len(logs)} activit{'y' if len(logs) == 1 else 'ies'}"
        )
        self.folder_button.setToolTip(f"Markdown folder: {self.db.logs_dir}\nClick to change")
        self.next_day.setEnabled(self.selected_date < today)
        self.list.clear()
        self.empty_state.setVisible(not logs)
        self.list.setVisible(bool(logs))
        for index, log in enumerate(logs):
            item = QListWidgetItem(self.list)
            row = ActivityRow(f"{log.entered_at:%H:%M}", log.activity, index == len(logs) - 1, self.list)
            row.ensurePolished()
            item.setSizeHint(row.sizeHint())
            self.list.setItemWidget(item, row)

    def show_previous_day(self) -> None:
        self.selected_date -= timedelta(days=1)
        self.refresh()

    def show_next_day(self) -> None:
        if self.selected_date < date.today():
            self.selected_date += timedelta(days=1)
            self.refresh()


class HistoryWindow(QDialog):
    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("YeahBouy history")
        self.resize(520, 620)
        self.setStyleSheet(modern_stylesheet(force_dark=True))
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#202630"))
        palette.setColor(QPalette.WindowText, QColor("#f5f5f7"))
        palette.setColor(QPalette.Base, QColor("#202630"))
        palette.setColor(QPalette.Text, QColor("#f5f5f7"))
        self.setPalette(palette)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        heading = QLabel("Activity history")
        heading.setObjectName("dateHeading")
        layout.addWidget(heading)

        calendar_header = QHBoxLayout()
        calendar_header.setContentsMargins(0, 0, 0, 0)
        calendar_header.setSpacing(8)
        previous_month = QPushButton("‹")
        previous_month.setObjectName("calendarNavButton")
        previous_month.clicked.connect(lambda: self.calendar.showPreviousMonth())
        self.month_label = QLabel()
        self.month_label.setAlignment(Qt.AlignCenter)
        self.month_label.setObjectName("sectionHeading")
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
        self.day_label.setObjectName("sectionHeading")
        layout.addWidget(self.day_label)

        self.list = QListWidget()
        self.list.setSpacing(8)
        self.list.setWordWrap(True)
        self.list.setUniformItemSizes(False)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.list, 1)
        self.empty_state = QLabel("No activities recorded for this day.")
        self.empty_state.setObjectName("secondaryLabel")
        self.empty_state.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_state, 1)

        open_markdown = QPushButton("Open selected day’s Markdown")
        open_markdown.setObjectName("secondaryButton")
        open_markdown.clicked.connect(self.open_markdown)
        layout.addWidget(open_markdown)
        layout.activate()
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
            f"{QDate(selected.year, selected.month, selected.day).toString('dddd, MMMM d, yyyy')} · "
            f"{len(logs)} log{'s' if len(logs) != 1 else ''}"
        )
        self.list.clear()
        self.empty_state.setVisible(not logs)
        self.list.setVisible(bool(logs))
        for index, log in enumerate(logs):
            item = QListWidgetItem(self.list)
            row = ActivityRow(f"{log.entered_at:%H:%M}", log.activity, index == len(logs) - 1, self.list)
            row.ensurePolished()
            item.setSizeHint(row.sizeHint())
            self.list.setItemWidget(item, row)

    def open_markdown(self) -> None:
        qdate = self.calendar.selectedDate()
        selected = date(qdate.year(), qdate.month(), qdate.day())
        path = self.db.file_path_for_date(selected)
        if not path.exists():
            QMessageBox.information(self, "No Markdown log", "No Markdown log exists for the selected day.")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QMessageBox.warning(self, "Could not open Markdown", f"Could not open:\n{path}")


class WorkLogApp:
    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.settings = QSettings("YeahBouy", "YeahBouy")
        logs_dir = self.settings.value("logs_dir", "", type=str)
        self.db = Database(logs_dir or None)
        self.today = TodayWindow(self.db)
        self.today.history_requested.connect(self.show_history)
        self.today.folder_requested.connect(self.choose_log_folder)
        self.today.quit_requested.connect(self.app.quit)
        self.history = None
        self.tray = QSystemTrayIcon(QIcon(asset_path("checkpoint-menubar.svg")), app)
        self.tray.setToolTip("YeahBouy")
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()
        self.show_today()

    def choose_log_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self.today,
            "Choose Markdown folder",
            str(self.db.logs_dir),
            QFileDialog.ShowDirsOnly,
        )
        if not folder:
            return
        self.db.logs_dir = Path(folder)
        self.settings.setValue("logs_dir", folder)
        self.today.refresh()
        if self.history is not None:
            self.history.refresh()

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        # macOS can report more than one activation reason for a single
        # status-bar click. Always showing here prevents the second event
        # from immediately hiding the panel again.
        if reason == QSystemTrayIcon.Trigger:
            self.show_today()

    def show_today(self) -> None:
        self.today.refresh()
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
