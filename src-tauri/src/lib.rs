mod input;
mod storage;

use input::{InputListener, RecordingState};
use std::sync::Arc;
use storage::{DashboardData, StatsStore};
use tauri::{Manager, State};

#[tauri::command]
fn get_dashboard(
    range: Option<String>,
    store: State<'_, Arc<StatsStore>>,
) -> Result<DashboardData, String> {
    store.dashboard_range(range.as_deref().unwrap_or("today"))
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
fn clear_stats(store: State<'_, Arc<StatsStore>>) -> Result<(), String> {
    store.clear()
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
            let listener_store = Arc::clone(&store);
            let listener_recording = recording.clone();
            app.manage(store);
            app.manage(recording);
            match InputListener::start(app.handle().clone(), listener_store, listener_recording) {
                Ok(listener) => {
                    app.manage(listener);
                }
                Err(error) => {
                    eprintln!("KeyPulse input listener unavailable: {error}");
                }
            }
            Ok(())
        })
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            get_dashboard,
            set_recording,
            get_recording,
            clear_stats
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
