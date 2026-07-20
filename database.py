from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class ActivityLog:
    entered_at: datetime
    activity: str


class Database:
    """Markdown-backed activity log store.

    The public name remains Database so the UI does not need to know how logs
    are stored. A day file is only created by add_activity().
    """

    ENTRY_PATTERN = re.compile(
        r"^## (?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\n"
        r"(?P<activity>.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )

    def __init__(self, path: str | Path | None = None) -> None:
        default = Path.home() / "Library/Application Support/YeahBouy/logs"
        self.logs_dir = Path(path) if path else Path(os.environ.get("YEAHBOUY_LOGS_DIR", default))

    def _day_path(self, day) -> Path:
        return self.logs_dir / f"{day:%Y-%m-%d}.md"

    def _read_file(self, path: Path) -> list[ActivityLog]:
        if not path.exists():
            return []
        content = path.read_text(encoding="utf-8")
        logs: list[ActivityLog] = []
        for match in self.ENTRY_PATTERN.finditer(content):
            try:
                entered_at = datetime.strptime(match.group("timestamp"), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            activity = match.group("activity").strip()
            if activity:
                logs.append(ActivityLog(entered_at=entered_at, activity=activity))
        return logs

    def add_activity(self, activity: str) -> ActivityLog:
        activity = activity.strip()
        if not activity:
            raise ValueError("Activity cannot be empty")

        entered_at = datetime.now()
        path = self._day_path(entered_at.date())
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(
                f"# YeahBouy — {entered_at:%Y-%m-%d}\n\n",
                encoding="utf-8",
            )
        with path.open("a", encoding="utf-8") as file:
            file.write(
                f"## {entered_at:%Y-%m-%d %H:%M:%S}\n"
                f"{activity}\n\n"
            )
        return ActivityLog(entered_at=entered_at, activity=activity)

    def today_activities(self) -> list[ActivityLog]:
        return list(reversed(self._read_file(self._day_path(datetime.now().date()))))

    def activities_for_date(self, day: date) -> list[ActivityLog]:
        """Return one day's activities, newest first, without modifying storage."""
        return list(reversed(self._read_file(self._day_path(day))))

    def activity_counts_for_month(self, year: int, month: int) -> dict[date, int]:
        """Return activity counts for the days in a month without creating files."""
        first_day = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)

        counts: dict[date, int] = {}
        day = first_day
        while day < next_month:
            entries = self._read_file(self._day_path(day))
            if entries:
                counts[day] = len(entries)
            day = day.fromordinal(day.toordinal() + 1)
        return counts

    def today_file_path(self) -> Path:
        return self._day_path(datetime.now().date())

    def file_path_for_date(self, day: date) -> Path:
        return self._day_path(day)

    def recent_activities(self, limit: int = 500) -> list[ActivityLog]:
        if not self.logs_dir.exists():
            return []
        logs: list[ActivityLog] = []
        for path in sorted(self.logs_dir.glob("????-??-??.md"), reverse=True):
            logs.extend(self._read_file(path))
            if len(logs) >= limit:
                break
        logs.sort(key=lambda log: log.entered_at, reverse=True)
        return logs[:limit]
