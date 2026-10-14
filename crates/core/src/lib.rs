use anyhow::{Context, Result, bail, ensure};
use chrono::{Datelike, Local, NaiveDate, NaiveDateTime};
use serde::Deserialize;
use std::{
    collections::{BTreeMap, HashSet},
    env, fs,
    io::Write,
    path::{Path, PathBuf},
};
use uuid::Uuid;

const TODO_HEADING: &str = "# YeahBouy — To-do";
pub const CATEGORIES: [&str; 3] = ["Development", "Research", "Paperwork"];

#[derive(Clone, Debug, PartialEq)]
pub struct Activity {
    entered_at: NaiveDateTime,
    text: String,
    offset: u64,
}

impl Activity {
    pub fn entered_at(&self) -> NaiveDateTime {
        self.entered_at
    }
    pub fn text(&self) -> &str {
        &self.text
    }
    pub fn offset(&self) -> u64 {
        self.offset
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Todo {
    id: String,
    title: String,
    completed: bool,
}

impl Todo {
    pub fn new(title: impl Into<String>) -> Result<Self> {
        let title = title.into().trim().to_owned();
        ensure!(
            !title.is_empty() && !title.contains(['\n', '\r']),
            "To-dos need a nonempty, single-line title"
        );
        Ok(Self {
            id: Uuid::new_v4().to_string(),
            title,
            completed: false,
        })
    }
    pub fn id(&self) -> &str {
        &self.id
    }
    pub fn title(&self) -> &str {
        &self.title
    }
    pub fn is_completed(&self) -> bool {
        self.completed
    }
    pub fn set_completed(&mut self, completed: bool) {
        self.completed = completed;
    }
}

#[derive(Clone)]
pub struct Store {
    folder: PathBuf,
}

impl Store {
    pub fn new(folder: impl Into<PathBuf>) -> Self {
        Self {
            folder: folder.into(),
        }
    }
    pub fn folder(&self) -> &Path {
        &self.folder
    }
    pub fn day_path(&self, day: NaiveDate) -> PathBuf {
        self.folder.join(format!("{day}.md"))
    }
    pub fn todos_path(&self) -> PathBuf {
        self.folder.join("todos.md")
    }

    pub fn activities(&self, day: NaiveDate) -> Result<Vec<Activity>> {
        let path = self.day_path(day);
        let content = read_optional(&path)?.unwrap_or_default();
        let mut activities = Vec::new();
        let mut current: Option<Activity> = None;
        let mut offset = 0;
        for line in content.split_inclusive('\n') {
            let line_text = line.trim_end_matches(['\r', '\n']);
            if is_entry_heading(line_text) {
                if let Some(mut activity) = current.take() {
                    activity.text = activity.text.trim().to_owned();
                    if !activity.text.is_empty() {
                        activities.push(activity);
                    }
                }
                current = entry_timestamp(line_text).map(|timestamp| Activity {
                    entered_at: timestamp,
                    text: String::new(),
                    offset,
                });
            } else if let Some(activity) = current.as_mut() {
                let unescaped = line_text
                    .strip_prefix('\\')
                    .filter(|text| is_entry_heading(text))
                    .unwrap_or(line_text);
                activity.text.push_str(unescaped);
                activity.text.push('\n');
            }
            offset += line.len() as u64;
        }
        if let Some(mut activity) = current {
            activity.text = activity.text.trim().to_owned();
            if !activity.text.is_empty() {
                activities.push(activity);
            }
        }
        activities.reverse();
        Ok(activities)
    }

    pub fn add_activity(&self, text: &str) -> Result<()> {
        let text = text.trim();
        ensure!(!text.is_empty(), "Activity cannot be empty");
        let now = Local::now().naive_local();
        let path = self.day_path(now.date());
        let mut entry = read_optional(&path)?.unwrap_or_default();
        if entry.is_empty() {
            entry.push_str(&format!("# YeahBouy — {}\n\n", now.date()));
        } else {
            if !entry.ends_with('\n') {
                entry.push('\n');
            }
            if !entry.ends_with("\n\n") {
                entry.push('\n');
            }
        }
        entry.push_str(&format!("## {}\n", now.format("%Y-%m-%d %H:%M:%S")));
        for line in text.lines() {
            if is_entry_heading(line) {
                entry.push('\\');
            }
            entry.push_str(line);
            entry.push('\n');
        }
        entry.push('\n');
        write_markdown(&path, &entry)
    }

    pub fn month_counts(&self, year: i32, month: u32) -> Result<BTreeMap<NaiveDate, usize>> {
        let mut day = NaiveDate::from_ymd_opt(year, month, 1).context("Invalid month")?;
        let mut counts = BTreeMap::new();
        while day.month() == month && day.year() == year {
            let count = self.activities(day)?.len();
            if count > 0 {
                counts.insert(day, count);
            }
            let Some(next) = day.succ_opt() else {
                break;
            };
            day = next;
        }
        Ok(counts)
    }

    pub fn todos(&self) -> Result<Vec<Todo>> {
        if let Some(content) = read_optional(&self.todos_path())? {
            return parse_todos(&content);
        }
        let legacy_path = self.folder.join("todos.json");
        let Some(content) = read_optional(&legacy_path)? else {
            return Ok(Vec::new());
        };
        #[derive(Deserialize)]
        #[serde(deny_unknown_fields)]
        struct LegacyTodo {
            title: String,
            completed: bool,
        }
        let legacy: Vec<LegacyTodo> = serde_json::from_str(&content)
            .context("Invalid legacy todos.json; it has not been changed")?;
        let todos: Vec<_> = legacy
            .into_iter()
            .map(|item| {
                let mut todo = Todo::new(item.title)?;
                todo.completed = item.completed;
                Ok(todo)
            })
            .collect::<Result<_>>()?;
        self.save_todos(&todos)?;
        fs::remove_file(legacy_path)?;
        Ok(todos)
    }

    pub fn save_todos(&self, todos: &[Todo]) -> Result<()> {
        let mut content = format!("{TODO_HEADING}\n\n");
        let mut ids = HashSet::new();
        for todo in todos {
            ensure!(ids.insert(&todo.id), "Duplicate to-do ID");
            ensure!(
                !todo.title.is_empty() && !todo.title.contains(['\n', '\r']),
                "Invalid to-do title"
            );
            content.push_str(&format!(
                "- [{}] {} <!-- yeahbouy:id={} -->\n",
                if todo.completed { 'x' } else { ' ' },
                todo.title,
                todo.id
            ));
        }
        write_markdown(&self.todos_path(), &content)
    }
}

fn entry_timestamp(line: &str) -> Option<NaiveDateTime> {
    let timestamp = line.strip_prefix("## ")?;
    if timestamp.len() != 19 {
        return None;
    }
    NaiveDateTime::parse_from_str(timestamp, "%Y-%m-%d %H:%M:%S").ok()
}

fn is_entry_heading(line: &str) -> bool {
    let Some(timestamp) = line.strip_prefix("## ") else {
        return false;
    };
    timestamp.len() == 19
        && timestamp.bytes().enumerate().all(|(ix, byte)| match ix {
            4 | 7 => byte == b'-',
            10 => byte == b' ',
            13 | 16 => byte == b':',
            _ => byte.is_ascii_digit(),
        })
}

fn read_optional(path: &Path) -> Result<Option<String>> {
    match fs::read_to_string(path) {
        Ok(content) => Ok(Some(content)),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(error).with_context(|| format!("Could not read {}", path.display())),
    }
}

fn parse_todos(content: &str) -> Result<Vec<Todo>> {
    let mut todos = Vec::new();
    let mut ids = HashSet::new();
    for line in content.lines() {
        if line.trim().is_empty() || line == TODO_HEADING {
            continue;
        }
        let (completed, title) = if let Some(title) = line.strip_prefix("- [ ] ") {
            (false, title)
        } else if let Some(title) = line
            .strip_prefix("- [x] ")
            .or_else(|| line.strip_prefix("- [X] "))
        {
            (true, title)
        } else {
            bail!(
                "Invalid todos.md; use '- [ ] Task' or '- [x] Task' on each line. Your file has not been changed."
            );
        };
        let (title, id) = if let Some((title, suffix)) = title.rsplit_once(" <!-- yeahbouy:id=") {
            let id = suffix
                .strip_suffix(" -->")
                .context("Invalid to-do ID comment")?;
            Uuid::parse_str(id).context("Invalid to-do ID")?;
            (title, Some(id))
        } else {
            (title, None)
        };
        let mut todo = Todo::new(title)?;
        if let Some(id) = id {
            todo.id = id.to_owned();
        }
        ensure!(
            ids.insert(todo.id.clone()),
            "Duplicate to-do ID in todos.md"
        );
        todo.completed = completed;
        todos.push(todo);
    }
    Ok(todos)
}

pub fn activity_content(activity: &str) -> (&str, Vec<&str>) {
    let Some((text, tags)) = activity.rsplit_once('\n') else {
        return (activity, vec![]);
    };
    let categories: Vec<_> = tags.split_whitespace().collect();
    if !categories.is_empty()
        && categories.iter().all(|tag| {
            matches!(
                *tag,
                "#Development" | "#Research" | "#Paperwork" | "#Review" | "#Fix" | "#Finance"
            )
        })
    {
        (text, categories.into_iter().map(|tag| &tag[1..]).collect())
    } else {
        (activity, vec![])
    }
}

pub fn data_directory() -> Result<PathBuf> {
    Ok(dirs::data_dir()
        .context("Could not locate your user data directory")?
        .join("YeahBouy"))
}

pub fn default_folder() -> Result<PathBuf> {
    if let Some(folder) = env::var_os("YEAHBOUY_LOGS_DIR") {
        return Ok(folder.into());
    }
    let settings = data_directory()?.join("settings.md");
    if let Some(content) = read_optional(&settings)? {
        let folder = content
            .strip_prefix("# YeahBouy settings\n\n## Log folder\n")
            .context("Invalid settings.md")?
            .trim();
        ensure!(
            !folder.is_empty() && !folder.contains(['\n', '\r']),
            "Invalid log folder in settings.md"
        );
        return Ok(folder.into());
    }
    if let Some(folder) = legacy_folder()? {
        return Ok(folder);
    }
    Ok(data_directory()?.join("logs"))
}

fn legacy_folder() -> Result<Option<PathBuf>> {
    #[cfg(target_os = "macos")]
    {
        let path = dirs::home_dir()
            .context("Could not locate your home directory")?
            .join("Library/Preferences/com.yeahbouy.YeahBouy.plist");
        if path.exists() {
            let value = plist::Value::from_file(path)?;
            return Ok(value
                .as_dictionary()
                .and_then(|dict| dict.get("logs_dir"))
                .and_then(plist::Value::as_string)
                .filter(|value| !value.is_empty())
                .map(PathBuf::from));
        }
    }
    #[cfg(target_os = "windows")]
    {
        use winreg::{RegKey, enums::HKEY_CURRENT_USER};
        if let Ok(key) =
            RegKey::predef(HKEY_CURRENT_USER).open_subkey(r"Software\YeahBouy\YeahBouy")
            && let Ok(folder) = key.get_value::<String, _>("logs_dir")
        {
            return Ok(Some(folder.into()));
        }
    }
    #[cfg(target_os = "linux")]
    {
        let path = dirs::config_dir()
            .context("Could not locate your configuration directory")?
            .join("YeahBouy/YeahBouy.conf");
        if let Some(content) = read_optional(&path)? {
            for line in content.lines() {
                if let Some(folder) = line.strip_prefix("logs_dir=") {
                    return Ok(Some(folder.into()));
                }
            }
        }
    }
    Ok(None)
}

pub fn save_folder(folder: &Path) -> Result<()> {
    let folder = folder
        .to_str()
        .context("The folder path must be valid UTF-8")?;
    ensure!(
        !folder.is_empty() && !folder.contains(['\n', '\r']),
        "Invalid log folder"
    );
    write_markdown(
        &data_directory()?.join("settings.md"),
        &format!("# YeahBouy settings\n\n## Log folder\n{folder}\n"),
    )
}

pub fn write_markdown(path: &Path, content: &str) -> Result<()> {
    // ponytail: one writer per folder; add optimistic file revisions if concurrent editors need safe saves.
    let parent = path
        .parent()
        .context("The Markdown path needs a parent folder")?;
    fs::create_dir_all(parent)?;
    let mut file = tempfile::NamedTempFile::new_in(parent)?;
    file.write_all(content.as_bytes())?;
    file.as_file().sync_all()?;
    file.persist(path)
        .map_err(|error| error.error)
        .with_context(|| format!("Could not save {}", path.display()))?;
    Ok(())
}

#[cfg(test)]
mod tests;
