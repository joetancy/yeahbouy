# YeahBouy

YeahBouy is a lightweight macOS menu-bar activity logger. Click its menu-bar
icon, record what you are working on, and keep a simple, portable daily log.

## What it does

- Captures an activity with a timestamp by pressing Enter or clicking **Log activity**.
- Shows today's full date and today's entries in the compact menu-bar panel.
- Lets you use the panel's **Back** and **Forward** buttons to browse earlier daily logs without opening the calendar. Forward stops at today.
- Provides a calendar-based History window for browsing a month at a time and opening a selected day's Markdown file.
- Stores every day as readable Markdown; no database service is required.

## Storage

Logs live at:

```text
~/Library/Application Support/YeahBouy/logs/YYYY-MM-DD.md
```

YeahBouy creates a day's file only after its first activity is recorded. Reading
or browsing a day never creates a new file.

Each log is ordinary Markdown, for example:

```markdown
# YeahBouy — 2026-07-21

## 2026-07-21 09:30:00
Review release checklist
```

## Run from source

Requirements: macOS and Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Build the macOS app

With the virtual environment activated:

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name YeahBouy --icon assets/checkpoint.icns --add-data 'assets/checkpoint-menubar.svg:assets' main.py
```

The rebuilt application is placed at `dist/YeahBouy.app`. The `--noconfirm`
option replaces the prior generated app bundle.
