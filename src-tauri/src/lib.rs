mod input;
mod storage;

use input::{InputListener, InputStatus, RecordingState};
use std::sync::Arc;
use storage::{DashboardData, StatsStore};
use tauri::menu::{MenuBuilder, MenuItemBuilder, PredefinedMenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{
    Emitter, Manager, PhysicalPosition, PhysicalSize, Position, Size, State, WebviewUrl,
    WebviewWindowBuilder,
};

#[tauri::command]
fn get_dashboard(
    range: Option<String>,
    store: State<'_, Arc<StatsStore>>,
) -> Result<DashboardData, String> {
    store.dashboard_range(range.as_deref().unwrap_or("today"))
}

#[tauri::command]
fn get_dashboard_custom(
    start: String,
    end: String,
    store: State<'_, Arc<StatsStore>>,
) -> Result<DashboardData, String> {
    store.dashboard_custom(&start, &end)
}

#[tauri::command]
fn set_recording(enabled: bool, recording: State<'_, RecordingState>) -> Result<(), String> {
    recording
        .enabled
        .store(enabled, std::sync::atomic::Ordering::Relaxed);
    Ok(())
}

#[tauri::command]
fn get_recording(recording: State<'_, RecordingState>) -> bool {
    recording.enabled.load(std::sync::atomic::Ordering::Relaxed)
}

#[tauri::command]
fn get_input_status(status: State<'_, InputStatus>) -> bool {
    status.available.load(std::sync::atomic::Ordering::Relaxed)
}

#[tauri::command]
fn clear_stats(store: State<'_, Arc<StatsStore>>) -> Result<(), String> {
    store.clear()
}

#[tauri::command]
fn toggle_keyshow(app: tauri::AppHandle) -> Result<bool, String> {
    toggle_keyshow_window(&app)
}

const KEYSHOW_WIDTH: f64 = 1080.0;
const KEYSHOW_HEIGHT: f64 = 190.0;

fn toggle_keyshow_window(app: &tauri::AppHandle) -> Result<bool, String> {
    let window = app
        .get_webview_window("keys-overlay")
        .ok_or_else(|| "keyshow overlay window unavailable".to_string())?;
    let visible = window.is_visible().map_err(|error| error.to_string())?;
    if visible {
        window.hide().map_err(|error| error.to_string())?;
    } else {
        window.show().map_err(|error| error.to_string())?;
    }
    let _ = app.emit("keyshow-changed", !visible);
    Ok(!visible)
}

fn build_keyshow_overlay(app: &tauri::App) -> tauri::Result<()> {
    let overlay =
        WebviewWindowBuilder::new(app, "keys-overlay", WebviewUrl::App("index.html".into()))
            .title("KeyPulse Keyshow")
            .inner_size(KEYSHOW_WIDTH, KEYSHOW_HEIGHT)
            .decorations(false)
            .transparent(true)
            .always_on_top(true)
            .skip_taskbar(true)
            .resizable(false)
            .shadow(false)
            .focused(false)
            .visible(false)
            .build()?;
    overlay.set_ignore_cursor_events(true)?;

    if let Some(monitor) = overlay.primary_monitor()? {
        let area = monitor.work_area();
        let scale = monitor.scale_factor();
        let width = KEYSHOW_WIDTH * scale;
        let height = KEYSHOW_HEIGHT * scale;
        let margin = 24.0 * scale;
        let x = area.position.x as f64 + ((area.size.width as f64 - width) / 2.0).max(margin);
        let y = area.position.y as f64
            + (area.size.height as f64 - height - margin).max(area.position.y as f64);
        overlay.set_size(Size::Physical(PhysicalSize::new(
            width as u32,
            height as u32,
        )))?;
        overlay.set_position(Position::Physical(PhysicalPosition::new(
            x as i32, y as i32,
        )))?;
    }
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let data_dir = app
                .path()
                .app_data_dir()
                .map_err(|error| std::io::Error::other(error.to_string()))?;
            std::fs::create_dir_all(&data_dir)?;

            let store = StatsStore::open(&data_dir.join("keypulse.sqlite"))
                .map_err(std::io::Error::other)?;
            let recording = RecordingState::default();
            let input_status = InputStatus::default();
            let listener_store = Arc::clone(&store);
            let listener_recording = recording.clone();
            let listener_status = input_status.clone();
            app.manage(store);
            app.manage(recording);
            app.manage(input_status);
            match InputListener::start(app.handle().clone(), listener_store, listener_recording) {
                Ok(listener) => {
                    listener_status
                        .available
                        .store(true, std::sync::atomic::Ordering::Relaxed);
                    app.manage(listener);
                }
                Err(error) => {
                    eprintln!("KeyPulse input listener unavailable: {error}");
                }
            }

            build_keyshow_overlay(app)?;
            setup_tray(app)?;
            Ok(())
        })
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            get_dashboard,
            get_dashboard_custom,
            set_recording,
            get_recording,
            get_input_status,
            clear_stats,
            toggle_keyshow
        ])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn setup_tray(app: &mut tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    let show = MenuItemBuilder::with_id("show", "打开 KeyPulse").build(app)?;
    let toggle = MenuItemBuilder::with_id("toggle-recording", "暂停/继续记录").build(app)?;
    let keyshow = MenuItemBuilder::with_id("toggle-keyshow", "按键可视化：关").build(app)?;
    let clear = MenuItemBuilder::with_id("clear-stats", "清空本地统计").build(app)?;
    let separator = PredefinedMenuItem::separator(app)?;
    let quit = PredefinedMenuItem::quit(app, Some("退出 KeyPulse"))?;
    let menu = MenuBuilder::new(app)
        .items(&[&show, &toggle, &keyshow, &clear, &separator, &quit])
        .build()?;

    let mut tray = TrayIconBuilder::with_id("keypulse-tray")
        .menu(&menu)
        .tooltip("KeyPulse 键鼠热力图")
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                if let Some(window) = tray.app_handle().get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        })
        .on_menu_event({
            let keyshow_menu_item = keyshow.clone();
            move |app, event| match event.id.as_ref() {
                "show" => {
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
                "toggle-recording" => {
                    if let Some(recording) = app.try_state::<RecordingState>() {
                        let enabled = !recording.enabled.load(std::sync::atomic::Ordering::Relaxed);
                        recording
                            .enabled
                            .store(enabled, std::sync::atomic::Ordering::Relaxed);
                        let _ = app.emit("recording-changed", enabled);
                    }
                }
                "toggle-keyshow" => {
                    if let Ok(visible) = toggle_keyshow_window(app) {
                        let label = if visible {
                            "按键可视化：开"
                        } else {
                            "按键可视化：关"
                        };
                        let _ = keyshow_menu_item.set_text(label);
                    }
                }
                "clear-stats" => {
                    if let Some(store) = app.try_state::<Arc<StatsStore>>() {
                        if store.clear().is_ok() {
                            if let Ok(snapshot) = store.dashboard_today() {
                                let _ = app.emit("stats-updated", snapshot);
                            }
                        }
                    }
                }
                _ => {}
            }
        });

    if let Some(icon) = app.default_window_icon().cloned() {
        tray = tray.icon(icon);
    }
    app.manage(tray.build(app)?);
    Ok(())
}
