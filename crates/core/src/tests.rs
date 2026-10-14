use super::*;

#[test]
fn browsing_does_not_create_files() -> Result<()> {
    let temporary = tempfile::tempdir()?;
    let store = Store::new(temporary.path().join("logs"));
    let day = NaiveDate::from_ymd_opt(2026, 7, 18).unwrap();
    assert!(store.activities(day)?.is_empty());
    assert!(store.month_counts(2026, 7)?.is_empty());
    assert!(store.todos()?.is_empty());
    assert!(!store.folder().exists());
    Ok(())
}

#[test]
fn invalid_timestamp_entries_match_the_python_parser() -> Result<()> {
    let temporary = tempfile::tempdir()?;
    let store = Store::new(temporary.path());
    let day = NaiveDate::from_ymd_opt(2026, 7, 18).unwrap();
    fs::write(
        store.day_path(day),
        "## 2026-07-18 09:15:00\nKeep this\n\n## 2026-02-30 10:30:00\nSkip invalid entry\n\n",
    )?;
    let logs = store.activities(day)?;
    assert_eq!(logs.len(), 1);
    assert_eq!(logs[0].text(), "Keep this");
    Ok(())
}

#[test]
fn adding_to_a_manually_edited_file_without_final_newline() -> Result<()> {
    let temporary = tempfile::tempdir()?;
    let store = Store::new(temporary.path());
    let day = Local::now().date_naive();
    let original = format!("# Notes\n\n## {day} 09:15:00\nOriginal text");
    fs::write(store.day_path(day), &original)?;
    store.add_activity("New entry")?;
    assert!(fs::read_to_string(store.day_path(day))?.starts_with(&original));
    let logs = store.activities(day)?;
    assert_eq!(logs.len(), 2);
    assert_eq!(logs[0].text(), "New entry");
    assert_eq!(logs[1].text(), "Original text");
    Ok(())
}

#[test]
fn python_logs_remain_readable_and_newest_first() -> Result<()> {
    let temporary = tempfile::tempdir()?;
    let store = Store::new(temporary.path());
    let day = NaiveDate::from_ymd_opt(2026, 7, 18).unwrap();
    let original = "# YeahBouy — 2026-07-18\n\n## 2026-07-18 09:15:00\nReviewed the release checklist\n\n## 2026-07-18 10:30:00\nUpdated the documentation\n#Development #Research\n\n";
    fs::write(store.day_path(day), original)?;
    let logs = store.activities(day)?;
    assert_eq!(logs.len(), 2);
    assert_eq!(
        activity_content(logs[0].text()),
        ("Updated the documentation", vec!["Development", "Research"])
    );
    assert_eq!(logs[1].text(), "Reviewed the release checklist");
    assert_ne!(logs[0].offset(), logs[1].offset());
    assert_eq!(store.month_counts(2026, 7)?, BTreeMap::from([(day, 2)]));
    assert_eq!(fs::read_to_string(store.day_path(day))?, original);
    assert_eq!(
        activity_content("Keep an unknown tag\n#custom"),
        ("Keep an unknown tag\n#custom", vec![])
    );
    Ok(())
}

#[test]
fn activity_round_trip_escapes_heading_like_lines() -> Result<()> {
    let temporary = tempfile::tempdir()?;
    let store = Store::new(temporary.path());
    let text =
        "Review <release> & fix rendering\n## not a timestamp\n## 2026-07-18 09:15:00\n世界 ✓";
    store.add_activity(text)?;
    let logs = store.activities(Local::now().date_naive())?;
    assert_eq!(logs.len(), 1);
    assert_eq!(logs[0].text(), text);
    assert!(
        fs::read_to_string(store.day_path(logs[0].entered_at().date()))?
            .contains("\\## 2026-07-18 09:15:00")
    );
    assert!(store.add_activity("  ").is_err());
    Ok(())
}

#[test]
fn todos_persist_as_markdown_with_stable_ids() -> Result<()> {
    let temporary = tempfile::tempdir()?;
    let store = Store::new(temporary.path());
    let mut todos = vec![
        Todo::new("Review <release> ✓")?,
        Todo::new("Review <release> ✓")?,
    ];
    assert_ne!(todos[0].id(), todos[1].id());
    todos[1].set_completed(true);
    store.save_todos(&todos)?;
    let reopened = Store::new(temporary.path());
    assert_eq!(reopened.todos()?, todos);
    assert!(fs::read_to_string(store.todos_path())?.contains("- [x] Review <release> ✓"));
    todos.remove(0);
    store.save_todos(&todos)?;
    assert_eq!(reopened.todos()?, todos);
    store.save_todos(&[])?;
    assert!(reopened.todos()?.is_empty());
    Ok(())
}

#[test]
fn manually_edited_checklists_and_corrupt_files() -> Result<()> {
    let temporary = tempfile::tempdir()?;
    let store = Store::new(temporary.path());
    fs::write(
        store.todos_path(),
        "# YeahBouy — To-do\n\n- [ ] Plan next release\n- [X] Review interface\n",
    )?;
    let todos = store.todos()?;
    assert_eq!(todos[0].title(), "Plan next release");
    assert!(todos[1].is_completed());
    for invalid in [
        "- [ ] ",
        "- [y] Task",
        "Unrecognized notes",
        "- [ ] x <!-- yeahbouy:id=bad -->",
    ] {
        fs::write(store.todos_path(), invalid)?;
        assert!(store.todos().is_err());
        assert_eq!(fs::read_to_string(store.todos_path())?, invalid);
    }
    assert!(Todo::new("  ").is_err());
    assert!(Todo::new("One\n- [x] Injected task").is_err());
    Ok(())
}

#[test]
fn json_migration_saves_before_removing_old_data() -> Result<()> {
    let temporary = tempfile::tempdir()?;
    let store = Store::new(temporary.path());
    let legacy = store.folder().join("todos.json");
    let content = r#"[{"title":"Keep this task","completed":true}]"#;
    fs::write(&legacy, content)?;
    fs::create_dir(store.todos_path())?;
    assert!(store.todos().is_err());
    assert_eq!(fs::read_to_string(&legacy)?, content);
    fs::remove_dir(store.todos_path())?;
    let todos = store.todos()?;
    assert_eq!(todos[0].title(), "Keep this task");
    assert!(todos[0].is_completed());
    assert!(!legacy.exists());
    assert_eq!(store.todos()?, todos);
    Ok(())
}

#[test]
fn failed_atomic_save_preserves_old_file_and_cleans_temporary_file() -> Result<()> {
    let temporary = tempfile::tempdir()?;
    let store = Store::new(temporary.path());
    let todos = vec![Todo::new("Keep me")?];
    store.save_todos(&todos)?;
    let original = fs::read(store.todos_path())?;
    let invalid = vec![todos[0].clone(), todos[0].clone()];
    assert!(store.save_todos(&invalid).is_err());
    assert_eq!(fs::read(store.todos_path())?, original);
    let blocked = store.folder().join("blocked.md");
    fs::create_dir(&blocked)?;
    fs::write(blocked.join("keep.txt"), "Keep this")?;
    assert!(write_markdown(&blocked, "new content").is_err());
    assert_eq!(fs::read_to_string(blocked.join("keep.txt"))?, "Keep this");
    assert_eq!(fs::read_dir(store.folder())?.count(), 2);
    Ok(())
}

#[test]
fn malformed_json_is_never_replaced() -> Result<()> {
    let temporary = tempfile::tempdir()?;
    let store = Store::new(temporary.path());
    let legacy = store.folder().join("todos.json");
    for invalid in [
        "{broken",
        r#"[{"title":"Task","completed":"false"}]"#,
        r#"[{"title":"","completed":false}]"#,
    ] {
        fs::write(&legacy, invalid)?;
        assert!(store.todos().is_err());
        assert_eq!(fs::read_to_string(&legacy)?, invalid);
        assert!(!store.todos_path().exists());
    }
    Ok(())
}
