"""Requirement 1 (part B): profile management UI in the settings modal."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

# ---- script state & actions (place near PK state) ----
anchor = "const showPkDuel = ref(false);"
assert anchor in t
block = anchor + """
type PlayerProfile = {
  id: string; name: string; color: string; best: number; wins: number; losses: number; games: number;
};
const profiles = ref<PlayerProfile[]>([]);
const activeProfile = ref<PlayerProfile | null>(null);
const profileColors = ["#34d9ff", "#ff5c7a", "#2de2a6", "#ffd166", "#a78bfa", "#ff9f0a", "#ff2e88", "#7ba889"];
const newProfileName = ref("");

function applyProfiles(view: { current: string; list: PlayerProfile[]; active: PlayerProfile }) {
  profiles.value = view.list;
  activeProfile.value = view.active;
}

async function refreshProfiles() {
  try {
    applyProfiles(await invoke("profiles_get"));
  } catch {
    // older runtime
  }
}

async function createProfile() {
  try {
    applyProfiles(await invoke("profile_create", { name: newProfileName.value }));
    newProfileName.value = "";
  } catch (error) {
    console.info(String(error));
  }
}

async function switchProfile(id: string) {
  try {
    applyProfiles(await invoke("profile_switch", { id }));
  } catch (error) {
    console.info(String(error));
  }
}

async function renameProfile(id: string, name: string) {
  try {
    applyProfiles(await invoke("profile_rename", { id, name }));
  } catch (error) {
    console.info(String(error));
  }
}

async function deleteProfile(id: string) {
  try {
    applyProfiles(await invoke("profile_delete", { id }));
  } catch (error) {
    console.info(String(error));
  }
}

async function setProfileColor(id: string, color: string) {
  try {
    applyProfiles(await invoke("profile_set_color", { id, color }));
  } catch (error) {
    console.info(String(error));
  }
}"""
t = t.replace(anchor, block)

# refresh on settings open
old_open = """  refreshDataInfo();
  refreshBehavior();
  showSettingsPanel.value = true;"""
assert old_open in t
t = t.replace(old_open, """  refreshDataInfo();
  refreshBehavior();
  refreshProfiles();
  showSettingsPanel.value = true;""")

# ---- template group before 启动与关闭 ----
old_section = """              <div class="ks-section-title">启动与关闭</div>"""
assert old_section in t
group = """              <div class="ks-section-title">我的档案</div>
              <div v-if="activeProfile" class="profile-current">
                <i class="profile-avatar" :style="{ background: activeProfile.color }"></i>
                <span class="profile-meta"><b>{{ activeProfile.name }}</b><small>最佳 {{ activeProfile.best }} 键 · 胜 {{ activeProfile.wins }} 负 {{ activeProfile.losses }} · {{ activeProfile.games }} 局</small></span>
                <button class="ks-radio small" @click="renameProfile(activeProfile.id, prompt('新名字', activeProfile.name) || activeProfile.name)">改名</button>
              </div>
              <div class="profile-colors" role="radiogroup" aria-label="档案颜色">
                <button v-for="color in profileColors" :key="color" class="profile-color" :class="{ active: activeProfile?.color === color }" :style="{ background: color }" :aria-checked="activeProfile?.color === color" role="radio" @click="setProfileColor(activeProfile?.id ?? '', color)"></button>
              </div>
              <div class="profile-list">
                <div v-for="profile in profiles" :key="profile.id" class="profile-row" :class="{ active: profile.id === activeProfile?.id }">
                  <i class="profile-avatar" :style="{ background: profile.color }"></i>
                  <span class="profile-meta"><b>{{ profile.name }}</b><small>最佳 {{ profile.best }} · {{ profile.wins }}胜 / {{ profile.losses }}负</small></span>
                  <button v-if="profile.id !== activeProfile?.id" class="profile-action" @click="switchProfile(profile.id)">切换</button>
                  <button v-if="profile.id !== activeProfile?.id" class="profile-action danger" @click="deleteProfile(profile.id)">删除</button>
                  <span v-else class="profile-action current-tag">当前</span>
                </div>
              </div>
              <div class="profile-create">
                <input v-model="newProfileName" maxlength="16" placeholder="新档案昵称…" @keydown.enter="createProfile" />
                <button class="profile-action add" @click="createProfile">＋ 新建档案</button>
              </div>
              <div class="ks-section-title">启动与关闭</div>"""
t = t.replace(old_section, group)

# ---- css ----
anchor_css = ".ks-behavior-row { margin-bottom: 8px; }"
assert anchor_css in t
css = anchor_css + """
.profile-current { display: flex; align-items: center; gap: 10px; padding: 10px 11px; border: 1px solid rgba(var(--line-rgb), .2); border-radius: 12px; background: rgba(var(--ink-rgb), .3); }
.profile-avatar { flex: 0 0 auto; width: 26px; height: 26px; border-radius: 50%; box-shadow: inset 0 0 0 2px rgba(255,255,255,.25); }
.profile-meta { flex: 1; min-width: 0; }
.profile-meta b, .profile-meta small { display: block; }
.profile-meta b { color: var(--tx-strong); font-size: 12px; }
.profile-meta small { margin-top: 2px; color: var(--tx-faint); font-size: 9px; }
.profile-colors { display: flex; gap: 6px; margin: 8px 0 2px; }
.profile-color { width: 18px; height: 18px; border-radius: 50%; border: 2px solid transparent; cursor: pointer; }
.profile-color.active { border-color: var(--text-main); box-shadow: 0 0 0 2px rgba(var(--line-rgb), .4); }
.profile-list { display: grid; gap: 5px; margin-top: 6px; }
.profile-row { display: flex; align-items: center; gap: 8px; padding: 6px 9px; border: 1px solid rgba(var(--line-rgb), .14); border-radius: 10px; }
.profile-row.active { border-color: rgba(var(--cyan-rgb), .5); background: rgba(var(--cyan-rgb), .07); }
.profile-action { padding: 4px 9px; border: 1px solid rgba(var(--line-rgb), .2); border-radius: 8px; color: var(--tx-soft); background: transparent; cursor: pointer; font-size: 9px; }
.profile-action:hover { border-color: rgba(var(--cyan-rgb), .6); color: var(--text-main); }
.profile-action.danger:hover { border-color: rgba(var(--pink-rgb), .6); color: var(--acc-pink-soft); }
.profile-action.current-tag { border: none; color: var(--tx-faint); cursor: default; }
.profile-action.add { color: var(--acc-cyan-bright); border-color: rgba(var(--cyan-rgb), .4); }
.profile-create { display: flex; gap: 6px; margin-top: 8px; }
.profile-create input { flex: 1; min-width: 0; padding: 7px 9px; border: 1px solid rgba(var(--line-rgb), .22); border-radius: 9px; color: var(--tx-strong); background: rgba(var(--ink-rgb), .3); font-size: 11px; }
"""
t = t.replace(anchor_css, css)
p.write_text(t, encoding="utf-8")
print("profile UI added")
