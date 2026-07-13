# YeahBouy

A small macOS menu-bar activity logger built with Python, PySide6, and SQLite.

Click the YeahBouy menu-bar icon, type an activity, and press Enter. Each entry is saved immediately with the current time. Today's entries appear in the popup as a timestamp followed by the activity; there is no timer or stop action.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Logs are stored as human-readable Markdown files at `~/Library/Application Support/YeahBouy/logs/YYYY-MM-DD.md` on macOS. Reading today’s logs does not create a file; a day file is created only when the first activity is saved.

## Package

```bash
pip install pyinstaller
pyinstaller --windowed --name YeahBouy --icon assets/checkpoint.icns --add-data 'assets/checkpoint-menubar.svg:assets' main.py
```
