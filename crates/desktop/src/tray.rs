use crate::view::AppView;
use anyhow::Result;
use gpui_kit::*;
use tray_icon::{
    MouseButton, MouseButtonState, TrayIcon, TrayIconBuilder, TrayIconEvent,
    menu::{Menu, MenuEvent, MenuItem},
};

enum TrayCommand {
    Show,
    Quit,
}

struct TraySession {
    _icon: TrayIcon,
    _events: Task<()>,
}
impl Global for TraySession {}

pub fn install(window: AnyWindowHandle, view: Entity<AppView>, cx: &mut App) -> Result<()> {
    let menu = Menu::new();
    let show = MenuItem::new("Open YeahBouy", true, None);
    let quit = MenuItem::new("Quit YeahBouy", true, None);
    menu.append_items(&[&show, &quit])?;
    let (sender, receiver) = async_channel::unbounded();
    let tray_sender = sender.clone();
    TrayIconEvent::set_event_handler(Some(move |event| {
        if matches!(
            event,
            TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            }
        ) {
            let _ = tray_sender.try_send(TrayCommand::Show);
        }
    }));
    let show_id = show.id().clone();
    let quit_id = quit.id().clone();
    MenuEvent::set_event_handler(Some(move |event: MenuEvent| {
        if event.id == show_id {
            let _ = sender.try_send(TrayCommand::Show);
        } else if event.id == quit_id {
            let _ = sender.try_send(TrayCommand::Quit);
        }
    }));
    let svg = resvg::usvg::Tree::from_data(
        include_bytes!("../../../assets/yeahbouy-menubar.svg"),
        &Default::default(),
    )?;
    let mut pixmap = resvg::tiny_skia::Pixmap::new(18, 18).expect("18×18 icon");
    resvg::render(
        &svg,
        resvg::tiny_skia::Transform::identity(),
        &mut pixmap.as_mut(),
    );
    let icon = tray_icon::Icon::from_rgba(pixmap.take(), 18, 18)?;
    let builder = TrayIconBuilder::new()
        .with_tooltip("YeahBouy")
        .with_menu(Box::new(menu))
        .with_menu_on_left_click(false);
    #[cfg(target_os = "macos")]
    let builder = builder.with_icon_templated(icon);
    #[cfg(not(target_os = "macos"))]
    let builder = builder.with_icon(icon);
    let tray = builder.build()?;
    let position_tray = tray.clone();
    let startup_view = view.clone();
    let events = cx.spawn(async move |cx| {
        // AppKit lays out a newly inserted status item on a later native run-loop turn.
        cx.background_executor()
            .timer(std::time::Duration::from_millis(100))
            .await;
        cx.update(|cx| {
            let _ = window.update(cx, |_, window, cx| {
                position_panel(window, &position_tray);
                cx.activate(true);
                window.activate_window();
                startup_view.update(cx, |view, cx| view.focus_capture(window, cx));
            });
        });
        while let Ok(command) = receiver.recv().await {
            cx.update(|cx| match command {
                TrayCommand::Show => {
                    if let Err(error) = window.update(cx, |_, window, cx| {
                        position_panel(window, &position_tray);
                        cx.activate(true);
                        window.activate_window();
                        view.update(cx, |view, cx| {
                            view.refresh(cx);
                            view.focus_capture(window, cx);
                        });
                    }) {
                        eprintln!("Could not open panel: {error:#}");
                    }
                }
                TrayCommand::Quit => cx.quit(),
            });
        }
    });
    window.update(cx, |_, window, cx| {
        window.on_window_should_close(cx, |window, cx| {
            hide_panel(window, cx);
            false
        });
    })?;
    cx.set_global(TraySession {
        _icon: tray,
        _events: events,
    });
    Ok(())
}

pub fn hide_panel(window: &Window, cx: &App) {
    #[cfg(target_os = "macos")]
    {
        let _ = window;
        cx.hide();
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = cx;
        window.minimize_window();
    }
}

#[cfg(target_os = "macos")]
fn position_panel(window: &Window, tray: &TrayIcon) {
    use objc2::MainThreadMarker;
    use objc2_app_kit::{
        NSApplication, NSApplicationActivationPolicy, NSFloatingWindowLevel, NSScreen, NSView,
    };
    use objc2_foundation::NSPoint;
    use raw_window_handle::{HasWindowHandle, RawWindowHandle};

    let Some(main_thread) = MainThreadMarker::new() else {
        return;
    };
    NSApplication::sharedApplication(main_thread)
        .setActivationPolicy(NSApplicationActivationPolicy::Accessory);
    let Ok(handle) = HasWindowHandle::window_handle(window) else {
        return;
    };
    let RawWindowHandle::AppKit(handle) = handle.as_raw() else {
        return;
    };
    // SAFETY: GPUI owns this AppKit view for the lifetime of `window`; this runs on the main thread.
    let view = unsafe { handle.ns_view.cast::<NSView>().as_ref() };
    let Some(native_window) = view.window() else {
        return;
    };
    native_window.setHidesOnDeactivate(true);
    native_window.setLevel(NSFloatingWindowLevel);
    let Some(status) = tray.ns_status_item() else {
        return;
    };
    let Some(button) = status.button(main_thread) else {
        return;
    };
    let Some(status_window) = button.window() else {
        return;
    };
    let anchor =
        status_window.convertRectToScreen(button.convertRect_toView(button.bounds(), None));
    // Status-item windows can have no NSScreen, including when a menu-bar manager parks them offscreen.
    let distance = |screen: &NSScreen| {
        let frame = screen.frame();
        let x = anchor.origin.x + anchor.size.width / 2.;
        let y = anchor.origin.y + anchor.size.height / 2.;
        (x - x.clamp(frame.origin.x, frame.origin.x + frame.size.width)).powi(2)
            + (y - y.clamp(frame.origin.y, frame.origin.y + frame.size.height)).powi(2)
    };
    let Some(screen) = status_window.screen().or_else(|| {
        NSScreen::screens(main_thread)
            .iter()
            .min_by(|a, b| distance(a).total_cmp(&distance(b)))
    }) else {
        return;
    };
    let bounds = screen.visibleFrame();
    let frame = native_window.frame();
    let (x, y) = panel_origin(
        (
            anchor.origin.x + anchor.size.width / 2.,
            anchor.origin.y - 8.,
        ),
        (frame.size.width, frame.size.height),
        (
            bounds.origin.x,
            bounds.origin.y,
            bounds.size.width,
            bounds.size.height,
        ),
    );
    native_window.setFrameOrigin(NSPoint::new(x, y));
}

#[cfg(not(target_os = "macos"))]
fn position_panel(_: &Window, _: &TrayIcon) {}

#[cfg(any(target_os = "macos", test))]
fn panel_origin(anchor: (f64, f64), size: (f64, f64), bounds: (f64, f64, f64, f64)) -> (f64, f64) {
    let (left, bottom, width, height) = bounds;
    let right = (left + width - size.0).max(left);
    let top = (bottom + height - size.1).max(bottom);
    (
        (anchor.0 - size.0 / 2.).clamp(left, right),
        (anchor.1 - size.1).clamp(bottom, top),
    )
}

#[cfg(test)]
mod tests {
    use super::panel_origin;
    #[test]
    fn panel_stays_inside_screen_at_both_edges_and_on_secondary_display() {
        assert_eq!(
            panel_origin((10., 1000.), (380., 480.), (0., 0., 1440., 1000.)),
            (0., 520.)
        );
        assert_eq!(
            panel_origin((1430., 1000.), (380., 480.), (0., 0., 1440., 1000.)),
            (1060., 520.)
        );
        assert_eq!(
            panel_origin((-10., 1000.), (380., 480.), (-1440., 0., 1440., 1000.)),
            (-380., 520.)
        );
    }
}
