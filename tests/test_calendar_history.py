from datetime import date

from database import Database


def test_calendar_reads_existing_markdown_without_creating_or_deleting_files(tmp_path) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    existing = logs_dir / "2026-07-18.md"
    existing.write_text(
        "# YeahBouy — 2026-07-18\n\n"
        "## 2026-07-18 09:15:00\nReviewed the release checklist\n\n"
        "## 2026-07-18 10:30:00\nUpdated the documentation\n\n",
        encoding="utf-8",
    )

    store = Database(logs_dir)
    assert [entry.activity for entry in store.activities_for_date(date(2026, 7, 18))] == [
        "Updated the documentation",
        "Reviewed the release checklist",
    ]
    assert store.activity_counts_for_month(2026, 7) == {date(2026, 7, 18): 2}
    assert existing.read_text(encoding="utf-8").count("## ") == 2
    assert sorted(path.name for path in logs_dir.glob("*.md")) == ["2026-07-18.md"]
