"""Requirement 1 (part A): multi-profile store + commands in lib.rs."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src-tauri\src\lib.rs")
t = p.read_text(encoding="utf-8")

start = t.find("/// Local PK profile persisted next to the dataLocation preference.")
end = t.find("/// Save a base64 PNG (from the footprint card canvas)")
assert start != -1, "pk profile section start missing"
assert end != -1, "footprint section start missing"

block = '''/// A local player profile. PK stats live per profile; the PK leaderboard
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

'''
t = t[:start] + block + t[end:]

# register commands in invoke handler
handler_old = """            get_pk_profile,
            pk_record_result,"""
handler_new = """            get_pk_profile,
            pk_record_result,
            profiles_get,
            profile_create,
            profile_switch,
            profile_rename,
            profile_delete,
            profile_set_color,"""
assert handler_old in t
t = t.replace(handler_old, handler_new)

# remove the old read/write pk profile helpers that are now superseded but still referenced:
# keep them (get_pk_profile uses old read) — rewire get_pk_profile to active profile
old_get = """#[tauri::command]
fn get_pk_profile(app: tauri::AppHandle) -> PkProfile {
    read_pk_profile(&app)
}"""
new_get = """#[tauri::command]
fn get_pk_profile(app: tauri::AppHandle) -> PlayerProfile {
    let state = load_profiles(&app);
    current_profile(&state)
}"""
assert old_get in t, "get_pk_profile not found"
t = t.replace(old_get, new_get)

p.write_text(t, encoding="utf-8")
print("profiles store + commands added")
