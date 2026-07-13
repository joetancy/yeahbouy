from datetime import datetime

from database import Database


def test_creates_a_human_readable_day_file_only_on_write(tmp_path) -> None:
    store = Database(tmp_path / "logs")
    assert list((tmp_path / "logs").glob("*.md")) == []
    assert store.today_activities() == []
    assert not (tmp_path / "logs" / f"{datetime.now():%Y-%m-%d}.md").exists()

    store.add_activity("Review deployment checklist")
    path = tmp_path / "logs" / f"{datetime.now():%Y-%m-%d}.md"
    content = path.read_text(encoding="utf-8")
    assert content.startswith(f"# YeahBouy — {datetime.now():%Y-%m-%d}")
    assert "## " in content
    assert "Review deployment checklist" in content
    assert store.today_activities()[0].activity == "Review deployment checklist"
