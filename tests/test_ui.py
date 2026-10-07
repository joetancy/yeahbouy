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
            window.resize(400, 620)
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
