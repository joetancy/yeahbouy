use chrono::{Datelike, Days, Local, NaiveDate};
use gpui_kit::component::{
    ActiveTheme, Disableable, Sizable, StyledExt,
    button::{Button, ButtonVariants},
    calendar::{Calendar, CalendarEvent, CalendarState, Date},
    checkbox::Checkbox,
    input::{Input, InputEvent, InputState},
    label::Label,
    tab::{Tab, TabBar},
};
use gpui_kit::*;
use gpui_kit::{assets::IconName, prelude::FluentBuilder};
use std::collections::BTreeMap;
use yeahbouy_core::{Activity, CATEGORIES, Store, Todo, activity_content, save_folder};

gpui_kit::actions!(yeahbouy, [HidePanel, Submit, SearchDay]);

struct ActivityRow {
    id: u64,
    time: SharedString,
    text: SharedString,
    raw: SharedString,
    categories: Vec<SharedString>,
}

impl From<Activity> for ActivityRow {
    fn from(activity: Activity) -> Self {
        let (text, categories) = activity_content(activity.text());
        Self {
            id: activity.offset(),
            time: activity.entered_at().format("%H:%M").to_string().into(),
            text: text.to_owned().into(),
            raw: activity.text().to_owned().into(),
            categories: categories
                .into_iter()
                .map(|name| name.to_owned().into())
                .collect(),
        }
    }
}

struct TodoRow {
    todo: Todo,
    label: SharedString,
    id: SharedString,
}

impl From<Todo> for TodoRow {
    fn from(todo: Todo) -> Self {
        Self {
            label: todo.title().to_owned().into(),
            id: format!("todo-{}", todo.id()).into(),
            todo,
        }
    }
}

pub struct AppView {
    store: Store,
    selected_day: NaiveDate,
    tab: usize,
    activity: Entity<InputState>,
    todo_input: Entity<InputState>,
    search: Entity<InputState>,
    searching: bool,
    categories: [bool; 3],
    logs: Vec<ActivityRow>,
    todos: Vec<TodoRow>,
    todos_readable: bool,
    error: Option<SharedString>,
    _subscriptions: Vec<Subscription>,
}

impl AppView {
    pub fn new(store: Store, window: &mut Window, cx: &mut Context<Self>) -> Self {
        window.set_window_title("YeahBouy");
        let activity = cx.new(|cx| InputState::new(window, cx).placeholder("Add activity…"));
        let todo_input = cx.new(|cx| InputState::new(window, cx).placeholder("Add a to-do…"));
        let search = cx.new(|cx| InputState::new(window, cx).placeholder("Search this day…"));
        let subscriptions = vec![
            cx.subscribe_in(&activity, window, |this, _, event, window, cx| {
                if matches!(event, InputEvent::PressEnter { .. }) {
                    this.add_activity(window, cx);
                }
            }),
            cx.subscribe_in(&todo_input, window, |this, _, event, window, cx| {
                if matches!(event, InputEvent::PressEnter { .. }) {
                    this.add_todo(window, cx);
                }
            }),
            cx.subscribe(&search, |_, _, _: &InputEvent, cx| cx.notify()),
        ];
        let mut view = Self {
            store,
            selected_day: Local::now().date_naive(),
            tab: 0,
            activity,
            todo_input,
            search,
            searching: false,
            categories: [false; 3],
            logs: vec![],
            todos: vec![],
            todos_readable: false,
            error: None,
            _subscriptions: subscriptions,
        };
        view.refresh(cx);
        view.focus_capture(window, cx);
        view
    }

    pub fn refresh(&mut self, cx: &mut Context<Self>) {
        self.selected_day = self.selected_day.min(Local::now().date_naive());
        self.error = None;
        // ponytail: small local Markdown files; move I/O to background tasks if cloud reads stall the UI.
        match self.store.activities(self.selected_day) {
            Ok(logs) => self.logs = logs.into_iter().map(Into::into).collect(),
            Err(error) => {
                self.logs.clear();
                self.error = Some(format!("Could not read activities: {error:#}").into());
            }
        }
        match self.store.todos() {
            Ok(todos) => {
                self.todos = todos.into_iter().map(Into::into).collect();
                self.todos_readable = true;
            }
            Err(error) => {
                self.todos_readable = false;
                self.error = Some(format!("Could not read to-dos: {error:#}").into());
            }
        }
        cx.notify();
    }

    pub fn focus_capture(&self, window: &mut Window, cx: &mut App) {
        let input = if self.tab == 0 {
            &self.activity
        } else {
            &self.todo_input
        };
        input.focus_handle(cx).focus(window, cx);
    }

    fn add_activity(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let mut text = self.activity.read(cx).value().trim().to_owned();
        if text.is_empty() {
            return;
        }
        let tags: Vec<_> = CATEGORIES
            .iter()
            .zip(self.categories)
            .filter(|(_, selected)| *selected)
            .map(|(name, _)| format!("#{name}"))
            .collect();
        if !tags.is_empty() {
            text.push('\n');
            text.push_str(&tags.join(" "));
        }
        if let Err(error) = self.store.add_activity(&text) {
            self.error = Some(format!("Could not save activity: {error:#}").into());
            cx.notify();
            return;
        }
        self.activity
            .update(cx, |input, cx| input.set_value("", window, cx));
        self.search
            .update(cx, |input, cx| input.set_value("", window, cx));
        self.categories = [false; 3];
        self.selected_day = Local::now().date_naive();
        self.refresh(cx);
        self.focus_capture(window, cx);
    }

    fn commit_todos(&mut self, todos: Vec<Todo>, cx: &mut Context<Self>) -> bool {
        if let Err(error) = self.store.save_todos(&todos) {
            self.error = Some(format!("Could not save to-dos: {error:#}").into());
            cx.notify();
            return false;
        }
        self.todos = todos.into_iter().map(Into::into).collect();
        self.error = None;
        cx.notify();
        true
    }

    fn add_todo(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        let title = self.todo_input.read(cx).value();
        if title.trim().is_empty() || !self.todos_readable {
            return;
        }
        let todo = match Todo::new(title.to_string()) {
            Ok(todo) => todo,
            Err(error) => {
                self.error = Some(error.to_string().into());
                cx.notify();
                return;
            }
        };
        let mut todos: Vec<_> = self.todos.iter().map(|row| row.todo.clone()).collect();
        todos.push(todo);
        if self.commit_todos(todos, cx) {
            self.todo_input
                .update(cx, |input, cx| input.set_value("", window, cx));
        }
    }

    fn change_todo(&mut self, id: &str, completed: Option<bool>, cx: &mut Context<Self>) {
        if !self.todos_readable {
            return;
        }
        let mut todos: Vec<_> = self.todos.iter().map(|row| row.todo.clone()).collect();
        if let Some(completed) = completed {
            if let Some(todo) = todos.iter_mut().find(|todo| todo.id() == id) {
                todo.set_completed(completed);
            }
        } else {
            todos.retain(|todo| todo.id() != id);
        }
        self.commit_todos(todos, cx);
    }

    fn change_day(&mut self, day: NaiveDate, cx: &mut Context<Self>) {
        self.selected_day = day.min(Local::now().date_naive());
        self.refresh(cx);
    }

    fn toggle_search(&mut self, window: &mut Window, cx: &mut Context<Self>) {
        self.tab = 0;
        self.searching = !self.searching;
        if self.searching {
            self.search.focus_handle(cx).focus(window, cx);
        } else {
            self.search
                .update(cx, |input, cx| input.set_value("", window, cx));
            self.focus_capture(window, cx);
        }
        cx.notify();
    }

    fn choose_folder(&mut self, window: &Window, cx: &mut Context<Self>) {
        let prompt = cx.prompt_for_paths(PathPromptOptions {
            files: false,
            directories: true,
            multiple: false,
            prompt: Some("Choose Markdown folder".into()),
        });
        cx.spawn_in(window, async move |this, cx| {
            let result = prompt.await;
            let _ = this.update_in(cx, |this, _, cx| match result {
                Ok(Ok(Some(paths))) => {
                    if let Some(path) = paths.into_iter().next() {
                        match save_folder(&path) {
                            Ok(()) => {
                                this.store = Store::new(path);
                                this.refresh(cx);
                            }
                            Err(error) => {
                                this.error =
                                    Some(format!("Could not remember folder: {error:#}").into());
                                cx.notify();
                            }
                        }
                    }
                }
                Ok(Ok(None)) => (),
                Ok(Err(error)) => {
                    this.error = Some(format!("Could not choose folder: {error:#}").into());
                    cx.notify();
                }
                Err(error) => {
                    this.error = Some(format!("Folder picker closed: {error}").into());
                    cx.notify();
                }
            });
        })
        .detach();
    }

    fn open_history(&self, cx: &mut App) {
        let store = self.store.clone();
        let options = WindowOptions {
            window_bounds: Some(WindowBounds::centered(size(px(360.), px(600.)), cx)),
            ..Default::default()
        };
        if let Err(error) = gpui_kit::open_window(options, cx, |window, cx| {
            cx.new(|cx| HistoryView::new(store, window, cx))
        }) {
            eprintln!("Could not open history: {error:#}");
        }
    }

    fn render_activity(&self, cx: &mut Context<Self>) -> AnyElement {
        let query = self.search.read(cx).value().trim().to_lowercase();
        let logs: Vec<_> = self
            .logs
            .iter()
            .filter(|log| log.raw.to_lowercase().contains(&query))
            .collect();
        div()
            .v_flex()
            .flex_1()
            .min_h_0()
            .gap_2()
            .child(
                div()
                    .h_flex()
                    .gap_2()
                    .child(
                        div()
                            .flex_1()
                            .min_w_0()
                            .child(Input::new(&self.activity).id("activity-input").small()),
                    )
                    .child(
                        Button::new("log")
                            .outline()
                            .icon(IconName::Plus)
                            .label("Add")
                            .on_click(
                                cx.listener(|this, _, window, cx| this.add_activity(window, cx)),
                            ),
                    ),
            )
            .child(
                div()
                    .h_flex()
                    .gap_3()
                    .children(CATEGORIES.iter().enumerate().map(|(ix, name)| {
                        Checkbox::new(("category", ix))
                            .small()
                            .checked(self.categories[ix])
                            .child(*name)
                            .on_click(cx.listener(move |this, checked, _, cx| {
                                this.categories[ix] = *checked;
                                cx.notify();
                            }))
                    })),
            )
            .child(
                div()
                    .h_flex()
                    .justify_between()
                    .gap_3()
                    .pt_2()
                    .border_t_1()
                    .border_color(cx.theme().border)
                    .child(
                        div()
                            .h_flex()
                            .gap_1()
                            .child(
                                Button::new("previous-day")
                                    .small()
                                    .ghost()
                                    .icon(IconName::ChevronLeft)
                                    .tooltip("Previous day")
                                    .on_click(cx.listener(|this, _, _, cx| {
                                        if let Some(day) =
                                            this.selected_day.checked_sub_days(Days::new(1))
                                        {
                                            this.change_day(day, cx);
                                        }
                                    })),
                            )
                            .child(
                                Button::new("next-day")
                                    .small()
                                    .ghost()
                                    .icon(IconName::ChevronRight)
                                    .tooltip("Next day")
                                    .disabled(self.selected_day >= Local::now().date_naive())
                                    .on_click(cx.listener(|this, _, _, cx| {
                                        if let Some(day) =
                                            this.selected_day.checked_add_days(Days::new(1))
                                        {
                                            this.change_day(day, cx);
                                        }
                                    })),
                            ),
                    )
                    .child(
                        div()
                            .v_flex()
                            .items_center()
                            .text_xs()
                            .child(if self.selected_day == Local::now().date_naive() {
                                "Today".into()
                            } else {
                                SharedString::from(
                                    self.selected_day.format("%a, %b %-d").to_string(),
                                )
                            })
                            .child(
                                div()
                                    .text_color(cx.theme().muted_foreground)
                                    .child(format!("{} activities", self.logs.len())),
                            ),
                    )
                    .child(
                        Button::new("today")
                            .outline()
                            .icon(IconName::Calendar)
                            .label("Today")
                            .on_click(cx.listener(|this, _, _, cx| {
                                this.change_day(Local::now().date_naive(), cx)
                            })),
                    ),
            )
            .when(self.searching, |panel| {
                panel.child(
                    Input::new(&self.search)
                        .id("day-search")
                        .small()
                        .cleanable(true),
                )
            })
            .child(
                div()
                    .id("activity-list")
                    .v_flex()
                    .flex_1()
                    .min_h_0()
                    .overflow_y_scroll()
                    .gap_2()
                    .py_1()
                    .when(logs.is_empty(), |list| {
                        list.child(empty_state(
                            if query.is_empty() {
                                "No activities for this day yet"
                            } else {
                                "No matching activities"
                            },
                            cx,
                        ))
                    })
                    .children(logs.into_iter().map(|log| render_activity_row(log, cx))),
            )
            .into_any_element()
    }

    fn render_todos(&self, cx: &mut Context<Self>) -> AnyElement {
        let completed = self
            .todos
            .iter()
            .filter(|row| row.todo.is_completed())
            .count();
        div()
            .v_flex()
            .flex_1()
            .min_h_0()
            .gap_2()
            .child(
                div()
                    .h_flex()
                    .gap_2()
                    .child(
                        div().flex_1().min_w_0().child(
                            Input::new(&self.todo_input)
                                .id("todo-input")
                                .small()
                                .disabled(!self.todos_readable),
                        ),
                    )
                    .child(
                        Button::new("add-todo")
                            .outline()
                            .icon(IconName::Plus)
                            .label("Add")
                            .disabled(!self.todos_readable)
                            .on_click(cx.listener(|this, _, window, cx| this.add_todo(window, cx))),
                    ),
            )
            .child(
                div()
                    .text_xs()
                    .text_color(cx.theme().muted_foreground)
                    .child(format!(
                        "{} remaining · {completed} completed",
                        self.todos.len() - completed
                    )),
            )
            .child(
                div()
                    .id("todo-list")
                    .v_flex()
                    .flex_1()
                    .min_h_0()
                    .overflow_y_scroll()
                    .gap_2()
                    .py_1()
                    .when(self.todos.is_empty() && self.todos_readable, |list| {
                        list.child(empty_state("No to-dos yet. Add one above.", cx))
                    })
                    .children(self.todos.iter().map(|row| {
                        let check_id = row.todo.id().to_owned();
                        let delete_id = check_id.clone();
                        div()
                            .id(row.id.clone())
                            .h_flex()
                            .gap_2()
                            .p_2()
                            .border_1()
                            .border_color(cx.theme().border)
                            .rounded(cx.theme().radius)
                            .child(
                                Checkbox::new("check")
                                    .small()
                                    .flex_1()
                                    .min_w_0()
                                    .checked(row.todo.is_completed())
                                    .disabled(!self.todos_readable)
                                    .accessibility_label(row.label.clone())
                                    .child(
                                        div()
                                            .text_sm()
                                            .when(row.todo.is_completed(), |text| {
                                                text.text_color(cx.theme().muted_foreground)
                                                    .line_through()
                                            })
                                            .child(row.label.clone()),
                                    )
                                    .on_click(cx.listener(move |this, completed, _, cx| {
                                        this.change_todo(&check_id, Some(*completed), cx)
                                    })),
                            )
                            .child(
                                Button::new("delete")
                                    .small()
                                    .ghost()
                                    .icon(IconName::Delete)
                                    .tooltip(format!("Delete {}", row.label))
                                    .disabled(!self.todos_readable)
                                    .on_click(cx.listener(move |this, _, _, cx| {
                                        this.change_todo(&delete_id, None, cx)
                                    })),
                            )
                    })),
            )
            .into_any_element()
    }
}

impl Render for AppView {
    fn render(&mut self, _: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        div()
            .id("yeahbouy-panel")
            .key_context("YeahBouy")
            .tab_group()
            .size_full()
            .v_flex()
            .gap_4()
            .p_4()
            .bg(cx.theme().background)
            .text_color(cx.theme().foreground)
            .on_action(|_: &HidePanel, window, cx| crate::tray::hide_panel(window, cx))
            .on_action(cx.listener(|this, _: &Submit, window, cx| {
                if this.tab == 0 {
                    this.add_activity(window, cx);
                } else {
                    this.add_todo(window, cx);
                }
            }))
            .on_action(
                cx.listener(|this, _: &SearchDay, window, cx| this.toggle_search(window, cx)),
            )
            .child(
                div()
                    .h_flex()
                    .justify_between()
                    .gap_2()
                    .child(div().font_semibold().child("YeahBouy"))
                    .child(
                        div().h_flex().gap_1().child(
                            Button::new("search-day")
                                .small()
                                .ghost()
                                .icon(IconName::Search)
                                .tooltip("Search this day")
                                .on_click(cx.listener(|this, _, window, cx| {
                                    this.toggle_search(window, cx)
                                })),
                        ),
                    ),
            )
            .child(
                div()
                    .text_base()
                    .font_semibold()
                    .child(Local::now().format("%A, %B %-d").to_string()),
            )
            .child(
                TabBar::new("main-tabs")
                    .underline()
                    .selected_index(self.tab)
                    .child(Tab::new().label("Activity").flex_1())
                    .child(Tab::new().label("To-do").flex_1())
                    .on_click(cx.listener(|this, ix, window, cx| {
                        this.tab = *ix;
                        this.focus_capture(window, cx);
                        cx.notify();
                    })),
            )
            .child(if self.tab == 0 {
                self.render_activity(cx)
            } else {
                self.render_todos(cx)
            })
            .when_some(self.error.clone(), |panel, error| {
                panel.child(
                    div()
                        .id("panel-error")
                        .text_xs()
                        .text_color(cx.theme().danger)
                        .max_h_16()
                        .overflow_y_scroll()
                        .child(error),
                )
            })
            .child(
                div()
                    .h_flex()
                    .justify_between()
                    .gap_2()
                    .pt_2()
                    .border_t_1()
                    .border_color(cx.theme().border)
                    .child(
                        div()
                            .h_flex()
                            .gap_2()
                            .child(
                                Button::new("history")
                                    .outline()
                                    .icon(IconName::Calendar)
                                    .label("History")
                                    .on_click(cx.listener(|this, _, _, cx| this.open_history(cx))),
                            )
                            .child(
                                Button::new("folder")
                                    .outline()
                                    .icon(IconName::FolderOpen)
                                    .label("Folder")
                                    .tooltip(self.store.folder().display().to_string())
                                    .on_click(cx.listener(|this, _, window, cx| {
                                        this.choose_folder(window, cx)
                                    })),
                            ),
                    )
                    .child(
                        Button::new("quit")
                            .ghost()
                            .icon(IconName::WindowClose)
                            .label("Quit")
                            .on_click(|_, _, cx| cx.quit()),
                    ),
            )
    }
}

fn empty_state(text: &'static str, cx: &App) -> impl IntoElement {
    div()
        .p_4()
        .text_sm()
        .text_color(cx.theme().muted_foreground)
        .child(text)
}

fn render_activity_row(log: &ActivityRow, cx: &App) -> impl IntoElement {
    let raw = log.raw.clone();
    div()
        .id(("activity", log.id))
        .h_flex()
        .items_start()
        .gap_3()
        .p_3()
        .border_1()
        .border_color(cx.theme().border)
        .rounded(cx.theme().radius)
        .child(
            div()
                .w_10()
                .flex_shrink_0()
                .text_xs()
                .text_color(cx.theme().muted_foreground)
                .child(log.time.clone()),
        )
        .child(
            div()
                .v_flex()
                .flex_1()
                .min_w_0()
                .gap_2()
                .text_sm()
                .child(Label::new(log.text.clone()))
                .when(!log.categories.is_empty(), |body| {
                    body.child(div().h_flex().flex_wrap().gap_1().children(
                        log.categories.iter().map(|category| {
                            div()
                                .px_2()
                                .py_0p5()
                                .text_xs()
                                .bg(cx.theme().secondary)
                                .rounded(cx.theme().radius / 2.)
                                .child(category.clone())
                        }),
                    ))
                }),
        )
        .child(
            Button::new(("copy-activity", log.id))
                .xsmall()
                .ghost()
                .icon(IconName::Copy)
                .tooltip("Copy activity")
                .on_click(move |_, _, cx| {
                    cx.write_to_clipboard(ClipboardItem::new_string(raw.to_string()))
                }),
        )
}

struct HistoryView {
    store: Store,
    calendar: Entity<CalendarState>,
    selected_day: NaiveDate,
    logs: Vec<ActivityRow>,
    counts: BTreeMap<NaiveDate, usize>,
    error: Option<SharedString>,
    _subscriptions: Vec<Subscription>,
}

impl HistoryView {
    fn new(store: Store, window: &mut Window, cx: &mut Context<Self>) -> Self {
        window.set_window_title("History");
        let selected_day = Local::now().date_naive();
        let calendar = cx.new(|cx| {
            let mut calendar = CalendarState::new(window, cx);
            calendar.set_date(selected_day, window, cx);
            calendar
        });
        let subscriptions = vec![
            cx.subscribe(&calendar, |this, _, event, cx| {
                if let CalendarEvent::Selected(Date::Single(Some(day))) = event {
                    this.selected_day = *day;
                    this.refresh(cx);
                }
            }),
            cx.observe(&calendar, |this, _, cx| this.refresh(cx)),
        ];
        let mut view = Self {
            store,
            calendar,
            selected_day,
            logs: vec![],
            counts: BTreeMap::new(),
            error: None,
            _subscriptions: subscriptions,
        };
        view.refresh(cx);
        view
    }

    fn refresh(&mut self, cx: &mut Context<Self>) {
        self.error = None;
        match self.store.activities(self.selected_day) {
            Ok(logs) => self.logs = logs.into_iter().map(Into::into).collect(),
            Err(error) => {
                self.logs.clear();
                self.error = Some(error.to_string().into());
            }
        }
        let calendar = self.calendar.read(cx);
        match self
            .store
            .month_counts(calendar.current_year(), calendar.current_month() as u32)
        {
            Ok(counts) => self.counts = counts,
            Err(error) => {
                self.counts.clear();
                self.error = Some(error.to_string().into());
            }
        }
        cx.notify();
    }
}

impl Render for HistoryView {
    fn render(&mut self, _: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        div()
            .v_flex()
            .size_full()
            .p_4()
            .gap_3()
            .bg(cx.theme().background)
            .text_color(cx.theme().foreground)
            .child(
                div()
                    .w_full()
                    .text_center()
                    .font_semibold()
                    .text_lg()
                    .child("History"),
            )
            .child(Calendar::new(&self.calendar).small().w_full())
            .child(
                div()
                    .w_full()
                    .text_center()
                    .text_xs()
                    .text_color(cx.theme().muted_foreground)
                    .child(format!(
                        "{} activities · {} active days this month",
                        self.counts.values().sum::<usize>(),
                        self.counts.len()
                    )),
            )
            .child(
                div()
                    .h_flex()
                    .justify_center()
                    .flex_wrap()
                    .gap_2()
                    .children(self.counts.keys().map(|day| {
                        let day = *day;
                        Button::new(SharedString::from(format!("logged-{day}")))
                            .xsmall()
                            .outline()
                            .label(day.day().to_string())
                            .tooltip(format!("{}: {} activities", day, self.counts[&day]))
                            .on_click(cx.listener(move |this, _, window, cx| {
                                this.selected_day = day;
                                this.calendar
                                    .update(cx, |state, cx| state.set_date(day, window, cx));
                                this.refresh(cx);
                            }))
                    })),
            )
            .child(
                div()
                    .w_full()
                    .text_center()
                    .text_sm()
                    .font_medium()
                    .child(format!(
                        "{} · {} activities",
                        self.selected_day.format("%A, %B %-d"),
                        self.logs.len()
                    )),
            )
            .child(
                div()
                    .id("history-list")
                    .v_flex()
                    .flex_1()
                    .min_h_0()
                    .overflow_y_scroll()
                    .gap_3()
                    .when(self.logs.is_empty(), |list| {
                        list.child(
                            div()
                                .w_full()
                                .text_center()
                                .child(empty_state("No activities recorded for this day", cx)),
                        )
                    })
                    .children(self.logs.iter().map(|log| render_activity_row(log, cx))),
            )
            .when_some(self.error.clone(), |panel, error| {
                panel.child(
                    div()
                        .w_full()
                        .text_center()
                        .text_sm()
                        .text_color(cx.theme().danger)
                        .child(error),
                )
            })
            .child(
                div().w_full().h_flex().justify_center().child(
                    Button::new("open-markdown")
                        .outline()
                        .icon(IconName::FileText)
                        .label("Open Markdown")
                        .disabled(!self.store.day_path(self.selected_day).exists())
                        .on_click(cx.listener(|this, _, _, cx| {
                            cx.open_with_system(&this.store.day_path(this.selected_day))
                        })),
                ),
            )
    }
}

#[cfg(test)]
mod tests;
