from database import Database


def test_compact_windows_fit_controls_and_show_activity(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QPushButton
    from ui import HistoryWindow, TodayWindow

    app = QApplication.instance() or QApplication([])
    db = Database(tmp_path)
    today = TodayWindow(db)
    today.activity.setText("Review the updated interface")
    today.add_activity()
    history = HistoryWindow(db)
    try:
        for window in (today, history):
            window.resize(window.minimumWidth() or 400, 640)
            window.show()
            app.processEvents()
            assert window.list.count() == 1
            for button in window.findChildren(QPushButton):
                if button.isVisible():
                    assert window.rect().contains(button.geometry())
                    assert button.fontMetrics().horizontalAdvance(button.text()) <= button.contentsRect().width(), button.text()
            row = window.list.itemWidget(window.list.item(0))
            assert row.height() >= row.minimumSizeHint().height()
    finally:
        today.close()
        history.close()


def test_categories_search_and_navigation_preserve_markdown(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from datetime import date, timedelta
    from PySide6.QtWidgets import QApplication, QMessageBox
    from types import SimpleNamespace
    from PySide6.QtCore import QRect
    from ui import TodayWindow, WorkLogApp, activity_content

    app = QApplication.instance() or QApplication([])
    db = Database(tmp_path)
    window = TodayWindow(db)
    try:
        screen = app.primaryScreen().availableGeometry()
        worklog = WorkLogApp.__new__(WorkLogApp)
        worklog.app = app
        worklog.today = window
        worklog.tray = SimpleNamespace(geometry=lambda: QRect(screen.right() - 20, screen.top(), 20, 20))
        worklog.show_today()
        app.processEvents()
        assert screen.contains(window.geometry())
        window.activity.setText("Review <release> & fix rendering")
        window.category_buttons["Development"].setChecked(True)
        assert list(window.category_buttons) == ["Development", "Research", "Paperwork"]
        window.category_buttons["Research"].setChecked(True)
        window.add_activity()
        saved = db.today_activities()[0].activity
        assert activity_content(saved) == (
            "Review <release> & fix rendering", ["Development", "Research"]
        )
        assert "#Development #Research" in db.today_file_path().read_text()
        assert not window.category_buttons["Research"].isChecked()
        assert activity_content("Keep unknown tags\n#custom") == ("Keep unknown tags\n#custom", [])
        window.search.setText("RELEASE")
        assert window.list.count() == 1
        window.search.setText("missing")
        assert window.list.count() == 0
        window.search.clear()
        window.show_previous_day()
        assert window.selected_date == date.today() - timedelta(days=1)
        assert window.list.count() == 0
        window.show_next_day()
        assert window.list.count() == 1
        assert not window.next_day.isEnabled()

        def fail_save(activity):
            raise OSError("disk full")

        monkeypatch.setattr(db, "add_activity", fail_save)
        monkeypatch.setattr(QMessageBox, "critical", lambda *args: None)
        window.activity.setText("Unsaved work")
        window.category_buttons["Paperwork"].setChecked(True)
        window.add_activity()
        assert window.activity.text() == "Unsaved work"
        assert window.category_buttons["Paperwork"].isChecked()
    finally:
        window.close()
