#![cfg_attr(target_os = "windows", windows_subsystem = "windows")]

extern crate gpui_kit as gpui;
mod tray;
mod view;

use gpui_kit::component::{Theme, ThemeMode};
use gpui_kit::*;
use view::{AppView, HidePanel, SearchDay, Submit};
use yeahbouy_core::{Store, default_folder};

gpui_kit::actions!(yeahbouy, [Quit]);

fn main() {
    let folder = match default_folder() {
        Ok(folder) => folder,
        Err(error) => {
            eprintln!("Could not read YeahBouy preferences: {error:#}");
            std::process::exit(1);
        }
    };
    gpui_kit::application()
        .with_assets(gpui_kit::assets::Assets)
        .run(move |cx| {
            gpui_kit::init(cx);
            Theme::change(ThemeMode::Dark, None, cx);
            // Base font sets the shared rem scale; the compact panel uses small Kit controls throughout.
            Theme::update(cx, |theme| theme.font_size = px(14.));
            let modifier = if cfg!(target_os = "macos") {
                "cmd"
            } else {
                "ctrl"
            };
            cx.bind_keys([
                KeyBinding::new("escape", HidePanel, Some("YeahBouy")),
                KeyBinding::new(&format!("{modifier}-enter"), Submit, Some("YeahBouy")),
                KeyBinding::new(&format!("{modifier}-f"), SearchDay, Some("YeahBouy")),
                KeyBinding::new(&format!("{modifier}-q"), Quit, None),
            ]);
            cx.on_action(|_: &Quit, cx| cx.quit());
            cx.set_menus(vec![Menu {
                name: "YeahBouy".into(),
                items: vec![MenuItem::action("Quit YeahBouy", Quit)],
                disabled: false,
            }]);
            let options = WindowOptions {
                window_bounds: Some(WindowBounds::centered(size(px(380.), px(480.)), cx)),
                titlebar: None,
                kind: if cfg!(target_os = "macos") {
                    WindowKind::PopUp
                } else {
                    WindowKind::Normal
                },
                is_resizable: false,
                is_minimizable: !cfg!(target_os = "macos"),
                show: false,
                focus: false,
                app_id: Some("com.yeahbouy.app".into()),
                ..Default::default()
            };
            let (window, view) = gpui_kit::open_window(options, cx, |window, cx| {
                cx.new(|cx| AppView::new(Store::new(folder), window, cx))
            })
            .expect("Could not open YeahBouy");
            if let Err(error) = tray::install(window, view, cx) {
                eprintln!("Could not create tray icon: {error:#}");
                let _ = window.update(cx, |_, window, cx| {
                    cx.activate(true);
                    window.activate_window();
                });
            }
        });
}
