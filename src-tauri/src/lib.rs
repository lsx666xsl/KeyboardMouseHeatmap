//! KeyPulse application shell: window lifecycle, tray menu, keyshow/mini
//! overlay windows, data-location preferences and PK profile persistence.
//!
//! Module layout:
//! - `input`    — global keyboard/mouse hooks, repeat/injection filtering, live events
//! - `storage`  — SQLite aggregation (key/mouse/hour), dashboard queries, clear
//! - `pk`       — LAN typing-duel transport (UDP discovery + TCP relay)
//! - this file  — Tauri commands, overlay windows, tray, settings persistence

mod input;
mod pk;
mod storage;

use input::{InputListener, InputStatus, RecordingState};
use std::sync::{Arc, Mutex};
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

#[tauri::command]
fn set_keyshow_position(app: tauri::AppHandle, position: String) -> Result<(), String> {
    if app.try_state::<KeyshowPrefs>().is_none() { return Ok(()); }
    if !KEYSHOW_POSITIONS.contains(&position.as_str()) {
        return Err(format!("unsupported keyshow position: {position}"));
    }
    let prefs = app.state::<KeyshowPrefs>();
    *prefs
        .position
        .lock()
        .map_err(|_| "keyshow prefs poisoned".to_string())? = position;
    apply_keyshow_layout(&app)
}

#[tauri::command]
fn set_keyshow_size(app: tauri::AppHandle, size: String) -> Result<(), String> {
    if app.try_state::<KeyshowPrefs>().is_none() { return Ok(()); }
    if !KEYSHOW_SIZES.iter().any(|(id, _, _)| *id == size) {
        return Err(format!("unsupported keyshow size: {size}"));
    }
    let prefs = app.state::<KeyshowPrefs>();
    *prefs
        .size
        .lock()
        .map_err(|_| "keyshow prefs poisoned".to_string())? = size;
    apply_keyshow_layout(&app)
}

fn apply_window_opacity(window: &tauri::WebviewWindow, opacity: f64) -> Result<(), String> {
    #[cfg(windows)]
    {
        use windows::Win32::UI::WindowsAndMessaging::{
            SetLayeredWindowAttributes, LWA_ALPHA,
        };
        let hwnd = window.hwnd().map_err(|e| e.to_string())?;
        let alpha = (opacity.clamp(0.15, 1.0) * 255.0).round() as u8;
        unsafe {
            SetLayeredWindowAttributes(hwnd, windows::Win32::Foundation::COLORREF(0), alpha, LWA_ALPHA)
                .map_err(|e| e.to_string())?;
        }
    }
    Ok(())
}

#[tauri::command]
fn set_keyshow_opacity(app: tauri::AppHandle, opacity: f64) -> Result<(), String> {
    if app.try_state::<KeyshowPrefs>().is_none() { return Ok(()); }
    let window = app
        .get_webview_window("keys-overlay")
        .ok_or_else(|| "keyshow overlay window unavailable".to_string())?;
    let clamped = opacity.clamp(0.15, 1.0);
    *app.state::<KeyshowPrefs>()
        .opacity
        .lock()
        .map_err(|_| "keyshow prefs poisoned".to_string())? = clamped;
    apply_window_opacity(&window, clamped)
}

#[tauri::command]
fn set_keyshow_custom_position(app: tauri::AppHandle, x: i32, y: i32) -> Result<(), String> {
    if app.try_state::<KeyshowPrefs>().is_none() { return Ok(()); }
    let window = app
        .get_webview_window("keys-overlay")
        .ok_or_else(|| "keyshow overlay window unavailable".to_string())?;
    let prefs = app.state::<KeyshowPrefs>();
    let mut position = prefs
        .position
        .lock()
        .map_err(|_| "keyshow prefs poisoned".to_string())?;
    if *position != "custom" {
        *position = "custom".into();
    }
    *prefs
        .custom_position
        .lock()
        .map_err(|_| "keyshow prefs poisoned".to_string())? = Some((x, y));
    drop(position);
    window
        .set_position(Position::Physical(PhysicalPosition::new(x, y)))
        .map_err(|e| e.to_string())
}

/// Drag mode makes the overlay interactive (draggable by its handle) and turns
/// click-through off; locking it restores click-through.
#[tauri::command]
fn set_keyshow_drag_mode(app: tauri::AppHandle, enabled: bool) -> Result<(), String> {
    if app.try_state::<KeyshowPrefs>().is_none() { return Ok(()); }
    let window = app
        .get_webview_window("keys-overlay")
        .ok_or_else(|| "keyshow overlay window unavailable".to_string())?;
    *app.state::<KeyshowPrefs>()
        .drag_mode
        .lock()
        .map_err(|_| "keyshow prefs poisoned".to_string())? = enabled;
    window
        .set_ignore_cursor_events(!enabled)
        .map_err(|e| e.to_string())?;
    // Toggling click-through re-applies the window ex-style, which drops the
    // layered alpha set by SetLayeredWindowAttributes; replay the saved opacity.
    let opacity = *app
        .state::<KeyshowPrefs>()
        .opacity
        .lock()
        .map_err(|_| "keyshow prefs poisoned".to_string())?;
    apply_window_opacity(&window, opacity)?;
    let _ = app.emit("keyshow-dragmode", enabled);
    Ok(())
}

/// Built-in placements and sizes for the keyshow overlay window.
const KEYSHOW_POSITIONS: [&str; 6] = [
    "bottom-center",
    "bottom-left",
    "bottom-right",
    "top-center",
    "top-left",
    "top-right",
];
const KEYSHOW_SIZES: [(&str, f64, f64); 3] = [
    ("small", 860.0, 150.0),
    ("medium", 1080.0, 190.0),
    ("large", 1400.0, 250.0),
];

pub struct KeyshowPrefs {
    position: Mutex<String>,
    size: Mutex<String>,
    opacity: Mutex<f64>,
    drag_mode: Mutex<bool>,
    custom_position: Mutex<Option<(i32, i32)>>,
}

impl Default for KeyshowPrefs {
    fn default() -> Self {
        Self {
            position: Mutex::new("bottom-center".into()),
            size: Mutex::new("medium".into()),
            opacity: Mutex::new(1.0),
            drag_mode: Mutex::new(false),
            custom_position: Mutex::new(None),
        }
    }
}

fn keyshow_geometry(size: &str) -> (f64, f64) {
    KEYSHOW_SIZES
        .iter()
        .find(|(id, _, _)| *id == size)
        .map(|(_, w, h)| (*w, *h))
        .unwrap_or((1080.0, 190.0))
}

/// Compute the physical window bounds for the given placement inside the
/// monitor work area (the area excluding the taskbar).
fn keyshow_bounds(
    position: &str,
    area: &tauri::PhysicalRect<i32, u32>,
    scale: f64,
    width: f64,
    height: f64,
) -> (f64, f64) {
    // snug against the screen edge so corner presets feel truly cornered
    let margin = 10.0 * scale;
    let left = area.position.x as f64 + margin;
    let right = area.position.x as f64 + area.size.width as f64 - width - margin;
    let top = area.position.y as f64 + margin;
    let bottom = area.position.y as f64 + area.size.height as f64 - height - margin;
    let center_x = area.position.x as f64 + (area.size.width as f64 - width) / 2.0;
    match position {
        "bottom-left" => (left, bottom),
        "bottom-right" => (right, bottom),
        "top-center" => (center_x, top),
        "top-left" => (left, top),
        "top-right" => (right, top),
        _ => (center_x, bottom),
    }
}

fn apply_keyshow_layout(app: &tauri::AppHandle) -> Result<(), String> {
    let window = app
        .get_webview_window("keys-overlay")
        .ok_or_else(|| "keyshow overlay window unavailable".to_string())?;
    let prefs = app.state::<KeyshowPrefs>();
    let position = prefs
        .position
        .lock()
        .map_err(|_| "keyshow prefs poisoned".to_string())?
        .clone();
    let size = prefs
        .size
        .lock()
        .map_err(|_| "keyshow prefs poisoned".to_string())?
        .clone();
    let (logical_w, logical_h) = keyshow_geometry(&size);
    let custom = prefs
        .custom_position
        .lock()
        .map_err(|_| "keyshow prefs poisoned".to_string())?
        .clone();
    if let Some(monitor) = window.primary_monitor().map_err(|e| e.to_string())? {
        let area = monitor.work_area();
        let scale = monitor.scale_factor();
        let width = logical_w * scale;
        let height = logical_h * scale;
        let (x, y) = if position == "custom" && custom.is_some() {
            let (cx, cy) = custom.unwrap();
            (cx as f64, cy as f64)
        } else {
            keyshow_bounds(&position, &area, scale, width, height)
        };
        window
            .set_size(Size::Physical(PhysicalSize::new(width as u32, height as u32)))
            .map_err(|e| e.to_string())?;
        window
            .set_position(Position::Physical(PhysicalPosition::new(x as i32, y as i32)))
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn build_mini_overlay(app: &tauri::App) -> tauri::Result<()> {
    let mini = WebviewWindowBuilder::new(app, "keys-mini", WebviewUrl::App("index.html".into()))
        .title("KeyPulse Mini")
        .inner_size(230.0, 92.0)
        .decorations(false)
        .transparent(true)
        .always_on_top(true)
        .skip_taskbar(true)
        .resizable(false)
        .shadow(false)
        .focused(false)
        .visible(false)
        .build()?;
    mini.set_ignore_cursor_events(true)?;
    if let Some(monitor) = mini.primary_monitor()? {
        let area = monitor.work_area();
        let scale = monitor.scale_factor();
        let margin = 10.0 * scale;
        let width = 230.0 * scale;
        let height = 92.0 * scale;
        let x = area.position.x as f64 + area.size.width as f64 - width - margin;
        let y = area.position.y as f64 + margin;
        mini.set_size(Size::Physical(PhysicalSize::new(width as u32, height as u32)))?;
        mini.set_position(Position::Physical(PhysicalPosition::new(x as i32, y as i32)))?;
    }
    Ok(())
}

#[tauri::command]
fn toggle_mini(app: tauri::AppHandle) -> Result<bool, String> {
    let window = app
        .get_webview_window("keys-mini")
        .ok_or_else(|| "mini overlay window unavailable".to_string())?;
    let visible = window.is_visible().map_err(|error| error.to_string())?;
    if visible {
        window.hide().map_err(|error| error.to_string())?;
    } else {
        window.show().map_err(|error| error.to_string())?;
    }
    let _ = app.emit("mini-changed", !visible);
    Ok(!visible)
}

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
            .inner_size(1080.0, 190.0)
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
    Ok(())
}

/// Where the SQLite database lives. `appdir` = a writable `keypulse-data`
/// folder next to the executable (default, keeps data local and off the
/// system drive); `appdata` = %APPDATA% fallback for installed builds whose
/// Program Files folder is read-only.
fn preferences_path(app: &impl tauri::Manager<tauri::Wry>) -> std::path::PathBuf {
    app.path()
        .app_config_dir()
        .map(|dir| dir.join("preferences.json"))
        .unwrap_or_else(|_| std::env::temp_dir().join("keypulse-preferences.json"))
}

fn read_data_location(app: &impl tauri::Manager<tauri::Wry>) -> String {
    let file = preferences_path(app);
    if let Ok(raw) = std::fs::read_to_string(&file) {
        if let Ok(value) = serde_json::from_str::<serde_json::Value>(&raw) {
            if let Some(kind) = value.get("dataLocation").and_then(|v| v.as_str()) {
                return kind.to_string();
            }
        }
    }
    // Default to the portable location next to the executable; it falls back
    // to %APPDATA% automatically when that folder is not writable.
    "appdir".into()
}

fn write_data_location(app: &impl tauri::Manager<tauri::Wry>, kind: &str) -> Result<(), String> {
    let file = preferences_path(app);
    if let Some(parent) = file.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let value = serde_json::json!({ "dataLocation": kind });
    std::fs::write(&file, serde_json::to_string_pretty(&value).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())
}

fn resolve_db_path(app: &impl tauri::Manager<tauri::Wry>) -> Result<std::path::PathBuf, String> {
    let location = read_data_location(app);
    if location == "appdir" {
        let exe_dir = std::env::current_exe()
            .map_err(|e| e.to_string())?
            .parent()
            .map(|p| p.to_path_buf())
            .ok_or_else(|| "cannot resolve executable directory".to_string())?;
        let candidate = exe_dir.join("keypulse-data");
        // Installed builds live under Program Files which is read-only for
        // normal users; fall back to AppData when the portable folder is not
        // writable.
        if std::fs::create_dir_all(&candidate).is_ok() {
            let probe = candidate.join(".write-test");
            if std::fs::write(&probe, b"1").is_ok() {
                let _ = std::fs::remove_file(&probe);
                return Ok(candidate.join("keypulse.sqlite"));
            }
        }
    }
    let appdata = app
        .path()
        .app_data_dir()
        .map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&appdata).map_err(|e| e.to_string())?;
    Ok(appdata.join("keypulse.sqlite"))
}

/// Move the SQLite file (plus WAL/SHM sidecars) to the requested location and
/// record the preference. Takes effect on the next launch.
#[tauri::command]
fn set_data_location(app: tauri::AppHandle, kind: String) -> Result<String, String> {
    if kind != "appdata" && kind != "appdir" {
        return Err(format!("unsupported data location: {kind}"));
    }
    let current = resolve_db_path(&app)?;
    let target_dir = if kind == "appdir" {
        let exe_dir = std::env::current_exe()
            .map_err(|e| e.to_string())?
            .parent()
            .map(|p| p.to_path_buf())
            .ok_or_else(|| "cannot resolve executable directory".to_string())?;
        exe_dir.join("keypulse-data")
    } else {
        app.path()
            .app_data_dir()
            .map_err(|e| e.to_string())?
    };
    std::fs::create_dir_all(&target_dir).map_err(|e| e.to_string())?;
    let target = target_dir.join("keypulse.sqlite");
    if current != target {
        if !target.exists() && current.exists() {
            for suffix in ["", "-wal", "-shm"] {
                let src = std::path::PathBuf::from(format!("{}{}", current.display(), suffix));
                if src.exists() {
                    std::fs::copy(&src, format!("{}{}", target.display(), suffix))
                        .map_err(|e| format!("copy failed: {e}"))?;
                }
            }
        }
        write_data_location(&app, &kind)?;
    }
    let dir = target.parent().map(|p| p.display().to_string()).unwrap_or_default();
    Ok(format!("数据位置已切换为：{dir}\\keypulse.sqlite（重启后生效）"))
}

/// Save a base64 PNG (from the footprint card canvas) under
/// %USERPROFILE%\Pictures\KeyPulse\ so no extra plugins are required.
/// A local player profile. PK stats live per profile; the PK leaderboard
/// advertises the currently active one.
#[derive(Clone, serde::Serialize, serde::Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct PlayerProfile {
    pub id: String,
    pub name: String,
    pub color: String,
    pub best: u64,
    pub wins: u64,
    pub losses: u64,
    pub games: u64,
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProfileState {
    pub current: String,
    pub list: Vec<PlayerProfile>,
}

fn load_profiles(app: &impl tauri::Manager<tauri::Wry>) -> ProfileState {
    let file = preferences_path(app);
    let mut state = ProfileState { current: "default".into(), list: vec![] };
    if let Ok(raw) = std::fs::read_to_string(&file) {
        if let Ok(value) = serde_json::from_str::<serde_json::Value>(&raw) {
            if let Some(profiles) = value.get("profiles") {
                if let Ok(parsed) = serde_json::from_value::<ProfileState>(profiles.clone()) {
                    if !parsed.list.is_empty() {
                        return parsed;
                    }
                }
            }
            // migrate the legacy single pkProfile into a "default" profile
            if let Some(old) = value.get("pkProfile") {
                state = ProfileState {
                    current: "default".into(),
                    list: vec![PlayerProfile {
                        id: "default".into(),
                        name: "玩家".into(),
                        color: "#34d9ff".into(),
                        best: old.get("best").and_then(|v| v.as_u64()).unwrap_or(0),
                        wins: old.get("wins").and_then(|v| v.as_u64()).unwrap_or(0),
                        losses: old.get("losses").and_then(|v| v.as_u64()).unwrap_or(0),
                        games: old.get("games").and_then(|v| v.as_u64()).unwrap_or(0),
                    }],
                };
            }
        }
    }
    if state.list.is_empty() {
        state = ProfileState {
            current: "default".into(),
            list: vec![PlayerProfile {
                id: "default".into(),
                name: "玩家".into(),
                color: "#34d9ff".into(),
                ..PlayerProfile::default()
            }],
        };
    }
    state
}

fn save_profiles(app: &impl tauri::Manager<tauri::Wry>, state: &ProfileState) -> Result<(), String> {
    let file = preferences_path(app);
    if let Some(parent) = file.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let mut value = if let Ok(raw) = std::fs::read_to_string(&file) {
        serde_json::from_str::<serde_json::Value>(&raw).unwrap_or_else(|_| serde_json::json!({}))
    } else {
        serde_json::json!({})
    };
    if let Some(obj) = value.as_object_mut() {
        obj.remove("pkProfile");
    }
    value["profiles"] = serde_json::to_value(state).map_err(|e| e.to_string())?;
    std::fs::write(&file, serde_json::to_string_pretty(&value).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())
}

fn current_profile(state: &ProfileState) -> PlayerProfile {
    state
        .list
        .iter()
        .find(|profile| profile.id == state.current)
        .cloned()
        .unwrap_or_else(|| {
            state.list.first().cloned().unwrap_or_else(|| PlayerProfile {
                id: "default".into(),
                name: "玩家".into(),
                color: "#34d9ff".into(),
                ..PlayerProfile::default()
            })
        })
}

fn random_profile_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let stamp = SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_millis();
    format!("p{}", stamp % 100_000_000)
}

/// Frontend view: full state plus the active profile for convenience.
#[derive(Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
struct ProfilesView {
    current: String,
    list: Vec<PlayerProfile>,
    active: PlayerProfile,
}

/// Custom key sounds live in %USERPROFILE%\KeyPulseSounds (*.mp3/*.wav/*.ogg).
const CUSTOM_SOUNDS_DIR: &str = "KeyPulseSounds";

#[tauri::command]
fn custom_sounds_dir() -> String {
    std::env::var("USERPROFILE")
        .or_else(|_| std::env::var("HOME"))
        .unwrap_or_else(|_| ".".into())
        + "\\KeyPulseSounds"
}

#[tauri::command]
fn list_custom_sounds() -> Vec<String> {
    let dir = custom_sounds_dir();
    let Ok(entries) = std::fs::read_dir(&dir) else { return vec![] };
    let mut names = vec![];
    for entry in entries.flatten() {
        let name = entry.file_name().to_string_lossy().to_string();
        let lower = name.to_lowercase();
        if lower.ends_with(".mp3") || lower.ends_with(".wav") || lower.ends_with(".ogg") {
            names.push(name);
        }
    }
    names.sort();
    names
}

#[tauri::command]
fn read_custom_sound_base64(file_name: String) -> Result<String, String> {
    use base64::{engine::general_purpose, Engine as _};
    let dir = custom_sounds_dir();
    let path = std::path::Path::new(&dir).join(&file_name);
    let meta = std::fs::metadata(&path).map_err(|e| e.to_string())?;
    if meta.len() > 3 * 1024 * 1024 {
        return Err("音频超过 3MB，请换小一点的文件".into());
    }
    let bytes = std::fs::read(&path).map_err(|e| e.to_string())?;
    let ext = file_name
        .rsplit('.')
        .next()
        .unwrap_or("mp3")
        .to_lowercase();
    let mime = match ext.as_str() {
        "wav" => "audio/wav",
        "ogg" => "audio/ogg",
        _ => "audio/mpeg",
    };
    Ok(format!(
        "data:{};base64,{}",
        mime,
        general_purpose::STANDARD.encode(&bytes)
    ))
}

#[tauri::command]
fn get_local_stats(store: State<'_, Arc<StatsStore>>) -> Result<storage::ProfileStats, String> {
    store.input_profile_stats()
}

#[tauri::command]
fn get_pk_profile(app: tauri::AppHandle) -> PlayerProfile {
    let state = load_profiles(&app);
    current_profile(&state)
}

#[tauri::command]
fn profiles_get(app: tauri::AppHandle) -> ProfilesView {
    let state = load_profiles(&app);
    ProfilesView { active: current_profile(&state), current: state.current, list: state.list }
}

#[tauri::command]
fn profile_create(app: tauri::AppHandle, name: String) -> Result<ProfilesView, String> {
    let mut state = load_profiles(&app);
    let cleaned = name.trim();
    let final_name = if cleaned.is_empty() { "玩家".into() } else { cleaned.to_string() };
    let id = random_profile_id();
    state.list.push(PlayerProfile {
        id: id.clone(),
        name: final_name,
        color: "#34d9ff".into(),
        ..PlayerProfile::default()
    });
    state.current = id;
    save_profiles(&app, &state)?;
    Ok(ProfilesView { active: current_profile(&state), current: state.current, list: state.list })
}

#[tauri::command]
fn profile_switch(app: tauri::AppHandle, id: String) -> Result<ProfilesView, String> {
    let mut state = load_profiles(&app);
    if !state.list.iter().any(|profile| profile.id == id) {
        return Err("档案不存在".into());
    }
    state.current = id;
    save_profiles(&app, &state)?;
    Ok(ProfilesView { active: current_profile(&state), current: state.current, list: state.list })
}

#[tauri::command]
fn profile_rename(app: tauri::AppHandle, id: String, name: String) -> Result<ProfilesView, String> {
    let mut state = load_profiles(&app);
    let cleaned = name.trim();
    if cleaned.is_empty() {
        return Err("名字不能为空".into());
    }
    if let Some(profile) = state.list.iter_mut().find(|profile| profile.id == id) {
        profile.name = cleaned.to_string();
    }
    save_profiles(&app, &state)?;
    Ok(ProfilesView { active: current_profile(&state), current: state.current, list: state.list })
}

#[tauri::command]
fn profile_delete(app: tauri::AppHandle, id: String) -> Result<ProfilesView, String> {
    let mut state = load_profiles(&app);
    if state.list.len() <= 1 {
        return Err("至少保留一个档案".into());
    }
    if state.current == id {
        return Err("请先切换到其他档案再删除".into());
    }
    state.list.retain(|profile| profile.id != id);
    save_profiles(&app, &state)?;
    Ok(ProfilesView { active: current_profile(&state), current: state.current, list: state.list })
}

#[tauri::command]
fn profile_set_color(app: tauri::AppHandle, id: String, color: String) -> Result<ProfilesView, String> {
    let mut state = load_profiles(&app);
    if let Some(profile) = state.list.iter_mut().find(|profile| profile.id == id) {
        profile.color = color;
    }
    save_profiles(&app, &state)?;
    Ok(ProfilesView { active: current_profile(&state), current: state.current, list: state.list })
}

/// Record a PK result onto the active profile.
#[tauri::command]
fn pk_record_result(app: tauri::AppHandle, win: bool, score: u64) -> Result<PlayerProfile, String> {
    let mut state = load_profiles(&app);
    let mut profile = current_profile(&state);
    profile.games += 1;
    if win { profile.wins += 1 } else { profile.losses += 1 }
    if score > profile.best { profile.best = score; }
    if let Some(slot) = state.list.iter_mut().find(|slot| slot.id == profile.id) {
        *slot = profile.clone();
    }
    save_profiles(&app, &state)?;
    Ok(profile)
}

/// Save a base64 PNG (from the footprint card canvas) under
/// %USERPROFILE%\Pictures\KeyPulse\ so no extra plugins are required.

#[tauri::command]
fn save_footprint_png(app: tauri::AppHandle, data_url: String, file_name: String) -> Result<String, String> {
    use base64::{engine::general_purpose, Engine as _};
    let encoded = data_url
        .strip_prefix("data:image/png;base64,")
        .ok_or_else(|| "expected a PNG data URL".to_string())?;
    let bytes = general_purpose::STANDARD
        .decode(encoded)
        .map_err(|e| format!("base64 decode failed: {e}"))?;
    let pictures = std::env::var("USERPROFILE")
        .or_else(|_| std::env::var("HOME"))
        .map_err(|_| "cannot resolve user profile".to_string())?
        + "\\Pictures\\KeyPulse";
    std::fs::create_dir_all(&pictures).map_err(|e| e.to_string())?;
    let safe_name: String = file_name
        .chars()
        .map(|c| if c.is_alphanumeric() || c == '-' || c == '_' { c } else { '-' })
        .collect();
    let path = format!("{pictures}\\{safe_name}.png");
    std::fs::write(&path, &bytes).map_err(|e| e.to_string())?;
    let _ = app.path();
    Ok(path)
}

#[tauri::command]
fn get_data_location(app: tauri::AppHandle) -> Result<String, String> {
    let path = resolve_db_path(&app)?;
    Ok(format!(
        "{}|{}",
        read_data_location(&app),
        path.display().to_string()
    ))
}

/// Launch & close preferences shared with the frontend.
/// start: "normal" | "minimized" | "tray"   (tray hides the main window)
/// close: "tray" | "minimize" | "quit"
pub struct AppBehavior {
    pub start: Mutex<String>,
    pub close: Mutex<String>,
}

impl Default for AppBehavior {
    fn default() -> Self {
        Self {
            start: Mutex::new("normal".into()),
            close: Mutex::new("tray".into()),
        }
    }
}

impl AppBehavior {
    fn load(app: &impl tauri::Manager<tauri::Wry>) -> Self {
        let file = preferences_path(app);
        let mut behavior = Self::default();
        if let Ok(raw) = std::fs::read_to_string(&file) {
            if let Ok(value) = serde_json::from_str::<serde_json::Value>(&raw) {
                if let Some(b) = value.get("appBehavior") {
                    if let Some(v) = b.get("start").and_then(|x| x.as_str()) {
                        *behavior.start.lock().unwrap() = v.to_string();
                    }
                    if let Some(v) = b.get("close").and_then(|x| x.as_str()) {
                        *behavior.close.lock().unwrap() = v.to_string();
                    }
                }
            }
        }
        behavior
    }

    fn save(app: &impl tauri::Manager<tauri::Wry>, start: &str, close: &str) -> Result<(), String> {
        let file = preferences_path(app);
        if let Some(parent) = file.parent() {
            std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        let mut value = if let Ok(raw) = std::fs::read_to_string(&file) {
            serde_json::from_str::<serde_json::Value>(&raw).unwrap_or_else(|_| serde_json::json!({}))
        } else {
            serde_json::json!({})
        };
        value["appBehavior"] = serde_json::json!({ "start": start, "close": close });
        std::fs::write(&file, serde_json::to_string_pretty(&value).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())
    }
}

#[tauri::command]
fn get_app_behavior(app: tauri::AppHandle) -> (String, String) {
    let state = app.state::<AppBehavior>();
    let start = state.start.lock().map(|s| s.clone()).unwrap_or_else(|_| "normal".into());
    let close = state.close.lock().map(|s| s.clone()).unwrap_or_else(|_| "tray".into());
    (start, close)
}

#[tauri::command]
fn set_app_behavior(app: tauri::AppHandle, start: String, close: String) -> Result<(), String> {
    if !["normal", "minimized", "tray"].contains(&start.as_str()) {
        return Err(format!("unsupported start behavior: {start}"));
    }
    if !["tray", "minimize", "quit"].contains(&close.as_str()) {
        return Err(format!("unsupported close behavior: {close}"));
    }
    let state = app.state::<AppBehavior>();
    *state.start.lock().map_err(|_| "poisoned".to_string())? = start.clone();
    *state.close.lock().map_err(|_| "poisoned".to_string())? = close.clone();
    AppBehavior::save(&app, &start, &close)
}

const AUTOSTART_REG_KEY: &str = r"Software\Microsoft\Windows\CurrentVersion\Run";
const AUTOSTART_VALUE: &str = "KeyPulse";

/// Register/unregister the Run key through the native registry API
/// (avoids shell/quoting pitfalls of spawning `reg.exe`).
fn set_autostart_registry(enabled: bool) -> Result<(), String> {
    use windows::core::PCWSTR;
    use windows::Win32::Foundation::WIN32_ERROR;
    use windows::Win32::System::Registry::{
        RegCloseKey, RegDeleteValueW, RegOpenKeyExW, RegSetValueExW, HKEY, HKEY_CURRENT_USER,
        KEY_SET_VALUE, REG_SZ,
    };

    fn wide(value: &str) -> Vec<u16> {
        value.encode_utf16().chain(std::iter::once(0)).collect()
    }

    let sub_key = wide(AUTOSTART_REG_KEY);
    let mut key: HKEY = HKEY::default();
    let opened = unsafe {
        RegOpenKeyExW(
            HKEY_CURRENT_USER,
            PCWSTR(sub_key.as_ptr()),
            None,
            KEY_SET_VALUE,
            &mut key,
        )
    };
    if opened != WIN32_ERROR(0) {
        return Err(format!("cannot open Run key (error {opened:?})"));
    }
    let name = wide(AUTOSTART_VALUE);
    let code = if enabled {
        let exe = std::env::current_exe().map_err(|e| e.to_string())?;
        let value = format!("\"{}\" --autostart", exe.display());
        let data = wide(&value);
        unsafe {
            RegSetValueExW(
                key,
                PCWSTR(name.as_ptr()),
                None,
                REG_SZ,
                Some(bytemuck_bytes_of_utf16(&data)),
            )
        }
    } else {
        unsafe { RegDeleteValueW(key, PCWSTR(name.as_ptr())) }
    };
    let _ = unsafe { RegCloseKey(key) };
    if code != WIN32_ERROR(0) {
        return Err(format!("registry update failed (error {code:?})"));
    }
    Ok(())
}

/// The Run value is stored as a UTF-16 byte slice for RegSetValueExW.
fn bytemuck_bytes_of_utf16(data: &[u16]) -> &[u8] {
    // SAFETY: u16 slice is 2-byte aligned; converting to bytes is sound.
    unsafe { std::slice::from_raw_parts(data.as_ptr() as *const u8, data.len() * 2) }
}

fn autostart_registry_enabled() -> bool {
    use windows::core::PCWSTR;
    use windows::Win32::System::Registry::{
        RegCloseKey, RegOpenKeyExW, RegQueryValueExW, HKEY, HKEY_CURRENT_USER, KEY_QUERY_VALUE,
    };

    fn wide(value: &str) -> Vec<u16> {
        value.encode_utf16().chain(std::iter::once(0)).collect()
    }

    let sub_key = wide(AUTOSTART_REG_KEY);
    let mut key: HKEY = HKEY::default();
    let opened = unsafe {
        RegOpenKeyExW(
            HKEY_CURRENT_USER,
            PCWSTR(sub_key.as_ptr()),
            None,
            KEY_QUERY_VALUE,
            &mut key,
        )
    };
    if opened.0 != 0 {
        return false;
    }
    let name = wide(AUTOSTART_VALUE);
    let mut buf = [0u16; 1024];
    let mut size = (buf.len() * 2) as u32;
    let result = unsafe {
        RegQueryValueExW(
            key,
            PCWSTR(name.as_ptr()),
            None,
            None,
            Some(buf.as_mut_ptr() as *mut u8),
            Some(&mut size),
        )
    };
    let _ = unsafe { RegCloseKey(key) };
    result.0 == 0
}

#[tauri::command]
fn set_autostart(_app: tauri::AppHandle, enabled: bool) -> Result<(), String> {
    set_autostart_registry(enabled)
}

#[tauri::command]
fn get_autostart() -> bool {
    autostart_registry_enabled()
}

/// One-time move of the legacy %APPDATA% store into the portable folder.
/// Only runs when no explicit dataLocation preference exists yet.
fn migrate_legacy_store_if_needed(app: &tauri::App) -> Result<(), String> {
    let prefs_file = preferences_path(app);
    if prefs_file.exists() {
        return Ok(());
    }
    let resolved = resolve_db_path(app)?;
    let is_appdir = resolved
        .parent()
        .and_then(|d| d.file_name())
        .map(|n| n == "keypulse-data")
        .unwrap_or(false);
    if !is_appdir || resolved.exists() {
        return Ok(());
    }
    let appdata = app.path().app_data_dir().map_err(|e| e.to_string())?;
    let source = appdata.join("keypulse.sqlite");
    if source.exists() {
        for suffix in ["", "-wal", "-shm"] {
            let src = std::path::PathBuf::from(format!("{}{}", source.display(), suffix));
            if src.exists() {
                let dst = std::path::PathBuf::from(format!("{}{}", resolved.display(), suffix));
                std::fs::copy(&src, &dst).map_err(|e| e.to_string())?;
            }
        }
    }
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            migrate_legacy_store_if_needed(app).map_err(std::io::Error::other)?;
            let db_path = resolve_db_path(app).map_err(std::io::Error::other)?;
            if let Some(parent) = db_path.parent() {
                std::fs::create_dir_all(parent)?;
            }

            let store = StatsStore::open(&db_path).map_err(std::io::Error::other)?;
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

            app.manage(KeyshowPrefs::default());
            app.manage(pk::PkState::default());
            let behavior = AppBehavior::load(app);
            let is_autostart = std::env::args().any(|arg| arg == "--autostart");
            let start_kind = if is_autostart { "tray".to_string() } else {
                behavior.start.lock().map(|s| s.clone()).unwrap_or_else(|_| "normal".into())
            };
            if start_kind != "normal" {
                if let Some(window) = app.get_webview_window("main") {
                    if start_kind == "tray" || is_autostart {
                        let _ = window.hide();
                    } else {
                        let _ = window.minimize();
                    }
                }
            }
            app.manage(behavior);
            build_keyshow_overlay(app)?;
            build_mini_overlay(app)?;
            apply_keyshow_layout(app.handle()).map_err(std::io::Error::other)?;
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
            toggle_keyshow,
            set_keyshow_position,
            set_keyshow_size,
            set_keyshow_opacity,
            set_keyshow_custom_position,
            set_keyshow_drag_mode,
            toggle_mini,
            set_data_location,
            get_data_location,
            save_footprint_png,
            get_pk_profile,
            get_local_stats,
            pk_record_result,
            custom_sounds_dir,
            list_custom_sounds,
            read_custom_sound_base64,
            profiles_get,
            profile_create,
            profile_switch,
            profile_rename,
            profile_delete,
            profile_set_color,
            get_app_behavior,
            set_app_behavior,
            set_autostart,
            get_autostart,
            pk::pk_start,
            pk::pk_challenge,
            pk::pk_report,
            pk::pk_stop,
            pk::pk_peers
        ])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                let behavior = window
                    .app_handle()
                    .try_state::<AppBehavior>()
                    .map(|state| {
                        state.close.lock().map(|c| c.clone()).unwrap_or_else(|_| "tray".into())
                    })
                    .unwrap_or_else(|| "tray".into());
                match behavior.as_str() {
                    "quit" => {
                        window.app_handle().exit(0);
                    }
                    "minimize" => {
                        api.prevent_close();
                        let _ = window.minimize();
                    }
                    _ => {
                        api.prevent_close();
                        let _ = window.hide();
                    }
                }
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
