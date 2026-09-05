"""Account center on main page (avatar popover); slim settings account pane; portal gains leaderboard."""
from pathlib import Path

# ---------- LoginPortal.vue: add cloud leaderboard after login ----------
p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\LoginPortal.vue")
t = p.read_text(encoding="utf-8")

old = 'const lanDevices = ref<LanDevice[]>([]);'
assert old in t
t = t.replace(old, """type BoardRow = { name: string; totalKeys: number; activeDays: number; streak: number; todayKeys: number };
const board = ref<BoardRow[]>([]);

async function refreshBoard() {
  if (!cloudToken.value) { board.value = []; return; }
  try {
    const res = await api("/api/leaderboard?sort=total");
    if (res.ok) board.value = res.list;
  } catch {
    // server offline
  }
}

const lanDevices = ref<LanDevice[]>([]);""")

old2 = """      window.dispatchEvent(new Event("kp-cloud-changed"));
      notice.value = mode.value === "register" ? "注册成功，已接入云端" : "已连接云端";
      formPass.value = "";"""
assert old2 in t
t = t.replace(old2, """      window.dispatchEvent(new Event("kp-cloud-changed"));
      notice.value = mode.value === "register" ? "注册成功，已接入云端" : "已连接云端";
      formPass.value = "";
      refreshBoard();""")

old3 = """            <button class="portal-submit ghost" @click="logout">断开连接</button>
          </template>"""
assert old3 in t
t = t.replace(old3, """            <button class="portal-submit ghost" @click="logout">断开连接</button>
            <div v-if="board.length" class="portal-board">
              <small>云端输入排行 · 按累计按键</small>
              <div v-for="(row, index) in board.slice(0, 8)" :key="row.name" class="portal-board-row" :class="{ me: row.name === cloudName }">
                <span class="portal-rank">{{ index + 1 }}</span>
                <span class="portal-board-name">{{ row.name }}{{ row.name === cloudName ? "（我）" : "" }}</span>
                <span class="portal-board-keys">{{ row.totalKeys.toLocaleString() }} 键</span>
              </div>
            </div>
          </template>""")

old4 = "onMounted(() => {\n  refreshProfile();"
assert old4 in t
t = t.replace(old4, "onMounted(() => {\n  refreshProfile();\n  refreshBoard();")

old5 = '.portal-device-keys { font-variant-numeric: tabular-nums; color: var(--tx-dim); }'
assert old5 in t
t = t.replace(old5, old5 + """
.portal-board { margin-top: 4px; }
.portal-board small { display: block; margin-bottom: 5px; color: var(--tx-faint); font-size: 8px; font-weight: 800; letter-spacing: .1em; }
.portal-board-row { display: grid; grid-template-columns: 20px 1fr auto; gap: 7px; align-items: center; padding: 4px 8px; border-radius: 8px; color: var(--tx-soft); font-size: 10px; }
.portal-board-row.me { background: rgba(var(--cyan-rgb), .12); }
.portal-rank { color: var(--tx-faint); font-weight: 900; }
.portal-board-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--tx-strong); font-weight: 700; }
.portal-board-keys { font-variant-numeric: tabular-nums; color: var(--tx-dim); }""")
p.write_text(t, encoding="utf-8")
print("portal leaderboard added")

# ---------- App.vue ----------
p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

# remove CloudAccount import + usage (portal now owns cloud auth UI)
t = t.replace('import CloudAccount from "./CloudAccount.vue";\n', "")
old_host = '<CloudAccount :key="cloudRefreshKey" />\n              '
assert old_host in t
t = t.replace(old_host, "")

# account popover state + summary refs (near showPkDuel)
anchor = "const showPkDuel = ref(false);"
assert anchor in t
t = t.replace(anchor, anchor + """
const showAccountPanel = ref(false);
const accountCloud = ref<{ name: string } | null>(null);

function refreshAccountSummary() {
  const token = localStorage.getItem("kp-cloud-token");
  const name = localStorage.getItem("kp-cloud-name");
  accountCloud.value = token && name ? { name } : null;
}

function toggleAccountPanel() {
  if (!showAccountPanel.value) refreshAccountSummary();
  showAccountPanel.value = !showAccountPanel.value;
}

function openPrivacyFromAccount() {
  showAccountPanel.value = false;
  showPrivacyPanel.value = true;
}

function openPortalFromAccount() {
  showAccountPanel.value = false;
  showLoginPortal.value = true;
}""")

# outside-click close for account popover
old_out = '  if (showSettingsPanel.value && !target.closest(".settings-control") && !target.closest(".settings-button")) showSettingsPanel.value = false;'
assert old_out in t
t = t.replace(old_out, old_out + '\n  if (showAccountPanel.value && !target.closest(".account-control")) showAccountPanel.value = false;')

# avatar button becomes account center (privacy moves into popover)
old_avatar = '<button class="avatar-button" aria-label="打开隐私与权限说明" :aria-expanded="showPrivacyPanel" @click="showPrivacyPanel = true">KP</button>'
assert old_avatar in t
new_avatar = '''<div class="account-control">
          <button class="avatar-button" aria-label="账号与连接" :aria-expanded="showAccountPanel" @click="toggleAccountPanel">KP</button>
          <div v-if="showAccountPanel" class="account-popover">
            <div class="account-head">
              <span class="account-avatar">KP</span>
              <div class="account-head-text"><b>{{ activeProfile?.name ?? "玩家" }}</b><small v-if="activeProfile">最佳 {{ activeProfile.best }} · {{ activeProfile.wins }}胜 {{ activeProfile.losses }}负</small></div>
            </div>
            <div class="account-cloud" :class="{ on: !!accountCloud }">
              <span class="account-cloud-dot"></span>
              <small>{{ accountCloud ? `云端已连接 · ${accountCloud.name}` : "未连接云端服务器" }}</small>
            </div>
            <button class="account-btn primary" @click="openPortalFromAccount"><i>⚡</i>登录 / 连接服务器</button>
            <button class="account-btn" @click="openPrivacyFromAccount"><i>🛡</i>隐私与权限说明</button>
            <button class="account-btn" @click="showAccountPanel = false; showSettingsPanel = true; settingsTab = 'account'"><i>§</i>管理本地档案</button>
          </div>
        </div>
        <button class="avatar-button hidden-slot" aria-hidden="true" tabindex="-1" style="display: none"></button>
        <div hidden></div>
        <button class="avatar-button" aria-label="打开隐私与权限说明" :aria-expanded="showPrivacyPanel" @click="showPrivacyPanel = true" style="display: none">KP</button>'''
# cleaner: just replace avatar with wrapper (no hidden leftovers)
new_avatar = '''<div class="account-control">
          <button class="avatar-button" aria-label="账号与连接" :aria-expanded="showAccountPanel" @click="toggleAccountPanel">KP</button>
          <div v-if="showAccountPanel" class="account-popover">
            <div class="account-head">
              <span class="account-avatar">KP</span>
              <div class="account-head-text"><b>{{ activeProfile?.name ?? "玩家" }}</b><small v-if="activeProfile">最佳 {{ activeProfile.best }} · {{ activeProfile.wins }}胜 {{ activeProfile.losses }}负</small></div>
            </div>
            <div class="account-cloud" :class="{ on: !!accountCloud }">
              <span class="account-cloud-dot"></span>
              <small>{{ accountCloud ? `云端已连接 · ${accountCloud.name}` : "未连接云端服务器" }}</small>
            </div>
            <button class="account-btn primary" @click="openPortalFromAccount"><i>⚡</i>登录 / 连接服务器</button>
            <button class="account-btn" @click="openPrivacyFromAccount"><i>🛡</i>隐私与权限说明</button>
            <button class="account-btn" @click="showAccountPanel = false; showSettingsPanel = true; settingsTab = 'account'"><i>§</i>管理本地档案</button>
          </div>
        </div>'''
t = t.replace(old_avatar, new_avatar)

# settings 改名 button: proper width
old_rename = '<button class="ks-radio small" @click="promptRename(activeProfile)">改名</button>'
assert old_rename in t
t = t.replace(old_rename, '<button class="profile-action" style="min-width: 52px; text-align: center;" @click="promptRename(activeProfile)">改名</button>')

# account popover styles
anchor_css = ".ks-modal-close:hover { color: #fff; border-color: rgba(var(--cyan-rgb), .6); }"
assert anchor_css in t
t = t.replace(anchor_css, anchor_css + """
.account-control { position: relative; }
.account-popover { position: absolute; z-index: 12; top: calc(100% + 10px); right: 0; width: 240px; padding: 14px; border: 1px solid rgba(var(--cyan-rgb), .25); border-radius: 16px; background: rgba(var(--pop-rgb), .98); box-shadow: 0 18px 42px rgba(0, 0, 0, .35); }
.account-head { display: flex; align-items: center; gap: 10px; margin-bottom: 9px; }
.account-avatar { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 50%; color: #fff; font-size: 11px; font-weight: 900; background: linear-gradient(135deg, var(--acc-cyan), var(--acc-violet)); }
.account-head-text b, .account-head-text small { display: block; }
.account-head-text b { color: var(--tx-strong); font-size: 12px; }
.account-head-text small { margin-top: 2px; color: var(--tx-faint); font-size: 9px; }
.account-cloud { display: flex; align-items: center; gap: 7px; padding: 7px 10px; margin-bottom: 8px; border: 1px solid rgba(var(--line-rgb), .18); border-radius: 10px; color: var(--tx-faint); }
.account-cloud-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--tx-mute); }
.account-cloud.on { color: var(--tx-soft); border-color: rgba(var(--green-rgb), .35); }
.account-cloud.on .account-cloud-dot { background: var(--acc-green); box-shadow: 0 0 8px var(--acc-green); }
.account-btn { display: flex; align-items: center; gap: 8px; width: 100%; padding: 8px 11px; margin-top: 5px; border: 1px solid rgba(var(--line-rgb), .18); border-radius: 10px; color: var(--tx-soft); background: rgba(var(--ink-rgb), .25); cursor: pointer; font-size: 11px; text-align: left; transition: all .15s ease; }
.account-btn i { font-style: normal; width: 14px; text-align: center; }
.account-btn:hover { border-color: rgba(var(--cyan-rgb), .55); color: var(--text-main); }
.account-btn.primary { border-color: rgba(var(--cyan-rgb), .5); background: rgba(var(--cyan-rgb), .1); color: var(--text-main); font-weight: 700; }
.account-btn.primary:hover { border-color: rgba(var(--cyan-rgb), .8); box-shadow: 0 0 14px rgba(var(--cyan-rgb), .15); }""")

p.write_text(t, encoding="utf-8")
print("account center popover added to main page")
