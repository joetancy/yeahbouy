from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QByteArray, QPoint, Qt, Signal, QDate, QRectF, QSettings, QSize, QUrl
from PySide6.QtGui import (
    QCursor,
    QDesktopServices,
    QIcon,
    QColor,
    QPainter,
    QPainterPath,
    QPalette,
    QPixmap,
    QRegion,
    QKeySequence,
    QShortcut,
    QTextCharFormat,
)
from PySide6.QtSvg import QSvgRenderer
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
    QMenu,
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
        panel = "#111b26"
        field = "#202c3a"
        border = "#344252"
        text = "#f5f7fc"
        muted = "#a7b4ca"
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
        "QPushButton { background: #087cff; color: white; border: 1px solid #258cff; "
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
        f"QLabel#activityTime {{ color: {text}; font-size: 12px; font-weight: 400; }}"
        "QLabel#activityText { font-size: 12px; font-weight: 400; }"
        f"QFrame#timeDivider {{ background: {border}; border: none; max-width: 1px; }}"
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
        f"QMenu {{ background: {field}; color: {text}; border: 1px solid {border}; padding: 6px; }}"
        "QMenu::item { padding: 8px 16px; } QMenu::item:selected { background: #285887; }"
        "QDialog#todayWindow QLabel#titleLabel { color: #f5f7fc; font-size: 16px; font-weight: 500; }"
        "QDialog#todayWindow QLabel#dateHeading { font-size: 18px; font-weight: 500; }"
        f"QDialog#todayWindow QLabel#promptLabel {{ color: {muted}; font-size: 13px; font-weight: 400; }}"
        "QDialog#todayWindow QLabel#sectionHeading { font-size: 12px; font-weight: 400; }"
        "QDialog#todayWindow QLabel#secondaryLabel { font-size: 12px; }"
        "QDialog#todayWindow QPushButton { font-size: 12px; font-weight: 400; }"
        "QDialog#todayWindow QLineEdit#activityInput { border: 2px solid #258cff; "
        "border-radius: 12px; padding: 10px; font-size: 13px; min-height: 20px; }"
        f"QPushButton#categoryButton {{ background: {field}; color: {text}; border: 1px solid {border}; "
        "font-size: 12px; padding: 8px; font-weight: 400; }"
        "QDialog#todayWindow QPushButton#categoryButton { font-size: 11px; padding: 6px; }"
        "QPushButton#categoryButton:checked { background: #193d65; border-color: #258cff; color: #8bbfff; }"
        "QPushButton#iconButton { background: #202c3a; border: 1px solid #344252; padding: 8px; }"
        "QPushButton#iconButton:hover { background: #304154; }"
        "QPushButton#rowMenuButton { background: transparent; border: none; padding: 0; }"
        "QPushButton#quitButton { background: #38232c; color: #ff686b; border: 1px solid #70333e; }"
        "QPushButton#quitButton:hover { background: #542b36; }"
        "QLabel#shortcutLabel { color: #a7b4ca; font-size: 12px; padding-right: 12px; }"
        "QDialog#todayWindow { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
        "stop:0 #111922, stop:0.5 #15202c, stop:1 #111b26); }"
        "QFrame#activityCard { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
        "stop:0 #202d3b, stop:1 #1c2734); }"
        "QPushButton::menu-indicator { image: none; width: 0; }"
    )


def asset_path(name: str) -> str:
    root = getattr(sys, "_MEIPASS", ".")
    return f"{root}/assets/{name}"


ICON_PATHS = {
    "search": '<circle cx="10" cy="10" r="7"/><path d="m15 15 6 6"/>',
    "chart": '<path d="M5 20v-7m7 7V4m7 16V9"/>',
    "Development": '<rect x="4" y="3" width="16" height="13" rx="1"/><path d="m4 16-2 4h20l-2-4"/>',
    "Paperwork": '<path d="M5 2h9l5 5v15H5Z M14 2v6h5 M8 12h8 M8 16h8"/>',
    "Research": '<path d="M9 18h6m-6 3h6M8 14a7 7 0 1 1 8 0l-1 3H9Z"/>',
    "history": '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 3"/>',
    "folder": '<path d="M2 5h8l2 3h10v13H2Z"/>',
    "quit": '<path d="M10 3H3v18h7m4-15 6 6-6 6m-7-6h13"/>',
}
CATEGORY_COLORS = {
    "Development": ("#193859", "#83b9ff"),
    "Research": ("#3c3525", "#e7cc87"),
    "Paperwork": ("#322d51", "#c0a6ff"),
    # Keep badges on entries saved with the previous category choices.
    "Review": ("#303449", "#bec8ef"),
    "Fix": ("#183e35", "#88ebc1"),
    "Finance": ("#322d51", "#c0a6ff"),
}


def line_icon(name: str, color: str = "#cbd5e7") -> QIcon:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
           f'fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
           f'stroke-linejoin="round">{ICON_PATHS[name]}</svg>')
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    return QIcon(pixmap)


def activity_content(activity: str) -> tuple[str, list[str]]:
    """Recognize an optional final line of our Markdown category hashtags."""
    text, separator, tags = activity.rpartition("\n")
    categories = tags.split()
    if separator and categories and all(
        tag.startswith("#") and tag[1:] in CATEGORY_COLORS for tag in categories
    ):
        return text, [tag[1:] for tag in categories]
    return activity, []


class ActivityRow(QWidget):
    """A daily activity card shared by the capture and history windows."""

    def __init__(self, timestamp: str, activity: str, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("activityCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 10, 12)
        card_layout.setSpacing(12)

        time_label = QLabel(timestamp)
        time_label.setObjectName("activityTime")
        time_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        time_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        time_label.setMinimumWidth(52)
        card_layout.addWidget(time_label)
        divider = QFrame()
        divider.setObjectName("timeDivider")
        divider.setFixedWidth(1)
        card_layout.addWidget(divider)

        content = QVBoxLayout()
        content.setSpacing(8)
        text, categories = activity_content(activity)
        activity_label = QLabel(text)
        activity_label.setTextFormat(Qt.PlainText)
        activity_label.setObjectName("activityText")
        activity_label.setWordWrap(True)
        activity_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        activity_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        content.addWidget(activity_label)
        if categories:
            for start in range(0, len(categories), 2):
                badges = QHBoxLayout()
                badges.setSpacing(8)
                for category in categories[start:start + 2]:
                    background, foreground = CATEGORY_COLORS[category]
                    badge = QLabel(category)
                    badge.setStyleSheet(
                        f"background: {background}; color: {foreground}; border-radius: 9px; "
                        "padding: 6px 8px; font-size: 11px; font-weight: 400;"
                    )
                    badges.addWidget(badge)
                badges.addStretch()
                content.addLayout(badges)
        card_layout.addLayout(content, 1)
        more = QPushButton("⋮")
        more.setObjectName("rowMenuButton")
        more.setAccessibleName("Activity actions")
        more.setFixedWidth(24)
        menu = QMenu(more)
        menu.addAction("Copy activity", lambda: QApplication.clipboard().setText(activity))
        more.setMenu(menu)
        card_layout.addWidget(more, 0, Qt.AlignTop)
        layout.addWidget(card, 1)

    def sizeHint(self):
        size = super().sizeHint()
        if isinstance(self.parentWidget(), QListWidget):
            width = self.parentWidget().contentsRect().width() - 2 * self.parentWidget().spacing()
            size.setWidth(0)
            size.setHeight(self.layout().heightForWidth(width))
        return size


def populate_activities(widget: QListWidget, logs) -> None:
    widget.clear()
    for log in logs:
        item = QListWidgetItem(widget)
        row = ActivityRow(f"{log.entered_at:%H:%M}", log.activity, widget)
        row.ensurePolished()
        item.setSizeHint(row.sizeHint())
        widget.setItemWidget(item, row)


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
    """Activity capture panel with category chips and a daily log."""

    history_requested = Signal()
    folder_requested = Signal()
    quit_requested = Signal()

    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.selected_date = date.today()
        self.setWindowTitle("YeahBouy")
        self.setObjectName("todayWindow")
        self.setMinimumSize(400, 540)
        self.resize(420, 620)
        self.setStyleSheet(modern_stylesheet(force_dark=True))
        # Qt.Popup treats the tray click that opened it as an outside click on
        # macOS, causing a first-click show/hide race. A tool window lets us
        # control visibility explicitly from the tray activation callback.
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)
        header = QHBoxLayout()
        header.setSpacing(14)
        mark = QLabel()
        mark.setPixmap(
            QPixmap(asset_path("yeahbouy-mark.png")).scaled(
                32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )
        mark.setAlignment(Qt.AlignCenter)
        mark.setFixedSize(32, 32)
        header.addWidget(mark)
        heading = QLabel("YeahBouy")
        heading.setObjectName("titleLabel")
        header.addWidget(heading, 1)
        for icon, label, callback in (
            ("search", "Search this day", self.toggle_search),
            ("chart", "Monthly activity summary", self.show_summary),
        ):
            button = QPushButton()
            button.setIcon(line_icon(icon))
            button.setIconSize(QSize(18, 18))
            button.setObjectName("iconButton")
            button.setFixedSize(36, 36)
            button.setAccessibleName(label)
            button.setToolTip(label)
            button.clicked.connect(callback)
            header.addWidget(button)
        layout.addLayout(header)
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        self.today_label = QLabel()
        self.today_label.setObjectName("dateHeading")
        layout.addWidget(self.today_label)

        prompt = QLabel("What did you work on?")
        prompt.setObjectName("promptLabel")
        layout.addWidget(prompt)

        self.activity = QLineEdit()
        self.activity.setObjectName("activityInput")
        self.activity.setAccessibleName("Activity description")
        self.activity.setPlaceholderText("Add activity...")
        self.activity.returnPressed.connect(self.add_activity)
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut.activated.connect(self.add_activity)
        input_layout = QHBoxLayout(self.activity)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.addStretch()
        hint = QLabel("⌘ + ↵" if sys.platform == "darwin" else "Ctrl + ↵")
        hint.setObjectName("shortcutLabel")
        hint.setAttribute(Qt.WA_TransparentForMouseEvents)
        input_layout.addWidget(hint)
        self.activity.setTextMargins(0, 0, hint.sizeHint().width() + 12, 0)
        capture_input = QHBoxLayout()
        capture_input.setSpacing(8)
        capture_input.addWidget(self.activity, 1)
        add_button = QPushButton("Log activity  →")
        add_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        add_button.clicked.connect(self.add_activity)
        capture_input.addWidget(add_button)
        layout.addLayout(capture_input)

        capture_actions = QHBoxLayout()
        capture_actions.setContentsMargins(0, 0, 0, 0)
        capture_actions.setSpacing(8)
        self.category_buttons = {}
        for category in ("Development", "Research", "Paperwork"):
            button = QPushButton(category)
            button.setObjectName("categoryButton")
            button.setCheckable(True)
            button.setIcon(line_icon(category))
            button.setToolTip(f"Tag as {category}")
            self.category_buttons[category] = button
            capture_actions.addWidget(button)
        capture_actions.addStretch()
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
        day_navigation.addWidget(previous_day)
        self.next_day = QPushButton("›")
        self.next_day.setObjectName("dayNavButton")
        self.next_day.setAccessibleName("Next day")
        self.next_day.setToolTip("Next day")
        self.next_day.clicked.connect(self.show_next_day)
        day_navigation.addWidget(self.next_day)
        selected_day = QVBoxLayout()
        selected_day.setSpacing(4)
        self.selected_date_label = QLabel()
        self.selected_date_label.setAlignment(Qt.AlignCenter)
        self.selected_date_label.setObjectName("sectionHeading")
        selected_day.addWidget(self.selected_date_label)
        self.activity_count = QLabel()
        self.activity_count.setObjectName("secondaryLabel")
        self.activity_count.setAlignment(Qt.AlignCenter)
        selected_day.addWidget(self.activity_count)
        day_navigation.addLayout(selected_day, 1)
        view = QPushButton("Day view  ⌄")
        view.setObjectName("secondaryButton")
        view_menu = QMenu(view)
        view_menu.addAction("Go to today", self.show_current_day)
        view_menu.addAction("Calendar history", self.history_requested.emit)
        view.setMenu(view_menu)
        day_navigation.addWidget(view)
        layout.addLayout(day_navigation)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search this day...")
        self.search.setAccessibleName("Search this day's activities")
        self.search.textChanged.connect(self.refresh)
        self.search.hide()
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.setSpacing(7)
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
        history.setIcon(line_icon("history"))
        history.setAccessibleName("Activity history")
        history.setToolTip("Activity history")
        history.clicked.connect(self.history_requested.emit)
        self.folder_button = QPushButton("Folder")
        self.folder_button.setObjectName("utilityButton")
        self.folder_button.setIcon(line_icon("folder"))
        self.folder_button.setAccessibleName("Choose Markdown folder")
        self.folder_button.clicked.connect(self.folder_requested.emit)
        self.quit_button = QPushButton("Quit")
        self.quit_button.setObjectName("quitButton")
        self.quit_button.setIcon(line_icon("quit", "#ff686b"))
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
        categories = [name for name, button in self.category_buttons.items() if button.isChecked()]
        if categories:
            activity += "\n" + " ".join(f"#{name}" for name in categories)
        try:
            self.db.add_activity(activity)
        except OSError as error:
            QMessageBox.critical(self, "Could not save activity", str(error))
            return
        self.activity.clear()
        for button in self.category_buttons.values():
            button.setChecked(False)
        self.search.clear()
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
        self.selected_date_label.setText(f"▦  {day_name}")
        self.activity_count.setText(f"{len(logs)} activit{'y' if len(logs) == 1 else 'ies'}")
        self.folder_button.setToolTip(f"Markdown folder: {self.db.logs_dir}\nClick to change")
        self.next_day.setEnabled(self.selected_date < today)
        query = self.search.text().casefold().strip()
        logs = [log for log in logs if query in log.activity.casefold()]
        self.empty_state.setText("No matching activities." if query else "No activities for this day yet.")
        self.empty_state.setVisible(not logs)
        self.list.setVisible(bool(logs))
        populate_activities(self.list, logs)

    def toggle_search(self) -> None:
        self.search.setVisible(self.search.isHidden())
        if self.search.isVisible():
            self.search.setFocus()
        else:
            self.search.clear()
            self.activity.setFocus()

    def show_summary(self) -> None:
        counts = self.db.activity_counts_for_month(self.selected_date.year, self.selected_date.month)
        month = QDate(self.selected_date.year, self.selected_date.month, 1).toString("MMMM yyyy")
        QMessageBox.information(self, month, f"{sum(counts.values())} activities across {len(counts)} active days.")

    def show_current_day(self) -> None:
        self.selected_date = date.today()
        self.refresh()

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
        self.empty_state.setVisible(not logs)
        self.list.setVisible(bool(logs))
        populate_activities(self.list, logs)

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
        self.tray = QSystemTrayIcon(QIcon(asset_path("yeahbouy-menubar.svg")), app)
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
        screen = self.app.screenAt(position) or self.app.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            self.today.resize(
                min(self.today.width(), available.width()),
                min(self.today.height(), available.height()),
            )
            position.setX(max(available.left(), min(position.x(), available.right() - self.today.width() + 1)))
            position.setY(max(available.top(), min(position.y(), available.bottom() - self.today.height() + 1)))
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
