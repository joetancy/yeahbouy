use super::AppView;
use gpui_kit::component::{Theme, ThemeMode};
use gpui_kit::test::TestWindowExt;
use gpui_kit::{
    AppContext, Bounds, SharedString, TestAppContext, WindowBounds, WindowOptions, px, size,
};
use yeahbouy_core::Store;

#[gpui_kit::test]
fn compact_panel_activity_and_checklist_flow(cx: &mut TestAppContext) {
    let temporary = tempfile::tempdir().unwrap();
    let store = Store::new(temporary.path());
    cx.update(|cx| {
        gpui_kit::init(cx);
        Theme::change(ThemeMode::Dark, None, cx);
        Theme::update(cx, |theme| theme.font_size = px(14.));
        cx.set_reduce_motion(true);
    });
    let (handle, view) = cx.update(|cx| {
        gpui_kit::open_window(
            WindowOptions {
                window_bounds: Some(WindowBounds::Windowed(Bounds::new(
                    Default::default(),
                    size(px(380.), px(480.)),
                ))),
                ..Default::default()
            },
            cx,
            |window, cx| cx.new(|cx| AppView::new(store.clone(), window, cx)),
        )
        .unwrap()
    });
    cx.update_window(handle, |_, window, cx| {
        window.render_frame(cx);
        window.click("activity-input", cx);
        window.input(
            "Review <release> & make long descriptions wrap without clipping",
            cx,
        );
        window.click("log", cx);
        assert_eq!(window.find("activity-input").value(), Some(""));
        assert!(window.find("folder").bounds().bottom() <= px(480.));
        assert!(window.find("quit").bounds().right() <= px(380.));
    })
    .unwrap();
    cx.run_until_parked();
    assert_eq!(
        store
            .activities(chrono::Local::now().date_naive())
            .unwrap()
            .len(),
        1
    );

    cx.update_window(handle, |_, window, cx| {
        window.within("main-tabs").click(1usize, cx);
        window.click("todo-input", cx);
        window.input("Plan next release", cx);
        window.press("enter", cx);
    })
    .unwrap();
    cx.run_until_parked();
    let todos = store.todos().unwrap();
    assert_eq!(todos.len(), 1);
    assert_eq!(todos[0].title(), "Plan next release");
    let row_id = SharedString::from(format!("todo-{}", todos[0].id()));
    cx.update_window(handle, |_, window, cx| {
        window.render_frame(cx);
        assert_eq!(window.find("todo-input").value(), Some(""));
        window.within(row_id.clone()).click("check", cx);
        assert_eq!(
            window.within(row_id.clone()).find("check").checked(),
            Some(true)
        );
    })
    .unwrap();
    assert!(store.todos().unwrap()[0].is_completed());
    cx.update_window(handle, |_, window, cx| {
        window.within(row_id.clone()).click("delete", cx);
        assert!(window.try_find("check").is_none());
    })
    .unwrap();
    assert!(store.todos().unwrap().is_empty());

    std::fs::write(store.todos_path(), "Unrecognized notes").unwrap();
    cx.update(|cx| view.update(cx, |view, cx| view.refresh(cx)));
    cx.update_window(handle, |_, window, cx| {
        window.render_frame(cx);
        window.click("todo-input", cx);
        window.input("Do not overwrite corrupt data", cx);
        assert_eq!(window.find("todo-input").value(), Some(""));
        window.click("add-todo", cx);
    })
    .unwrap();
    assert_eq!(
        std::fs::read_to_string(store.todos_path()).unwrap(),
        "Unrecognized notes"
    );
    cx.simulate_window_resize(handle, size(px(360.), px(440.)));
    cx.update_window(handle, |_, window, cx| {
        window.render_frame(cx);
        assert!(window.find("folder").bounds().bottom() <= px(440.));
        assert!(window.find("quit").bounds().right() <= px(360.));
    })
    .unwrap();
}
