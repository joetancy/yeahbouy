from __future__ import annotations

from datetime import datetime

from models import WorkSession


def elapsed(started_at: datetime, ended_at: datetime | None = None) -> int:
    return max(0, int(((ended_at or datetime.now()) - started_at).total_seconds()))


def format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def chatgpt_prompt(work: WorkSession) -> str:
    return (
        "Turn this work log into a concise engineering update.\n\n"
        f"Task: {work.task.title}\nDuration: {format_duration(elapsed(work.started_at, work.ended_at))}\n"
        f"Accomplished: {work.accomplishment}\nBlockers: {work.blockers}\nNext step: {work.next_step}\n\n"
        "Do not invent details."
    )

