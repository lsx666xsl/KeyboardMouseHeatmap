<script setup lang="ts">
/** CloudAccount — register/login/logout against a self-hosted KeyPulse server.
 * Session (server + token) is stored in localStorage so the PK duel can push
 * its result to the cloud afterwards. */
import { onMounted, ref } from "vue";

type CloudProfile = { name: string; best: number; wins: number; losses: number; games: number; totalKeys: number; totalMouse: number; activeDays: number; streak: number; todayKeys: number };

const server = ref(localStorage.getItem("kp-cloud-server") || "http://127.0.0.1:7788");
const cloudName = ref(localStorage.getItem("kp-cloud-name") || "");
const cloudToken = ref(localStorage.getItem("kp-cloud-token") || "");
const profile = ref<CloudProfile | null>(null);
const mode = ref<"login" | "register">("login");
const formName = ref("");
const formPass = ref("");
const notice = ref("");
const busy = ref(false);

async function api(path: string, body?: unknown) {
  const res = await fetch(server.value + path, {
    method: body ? "POST" : "GET",
    headers: { "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

function saveSession(name: string, token: string) {
  cloudName.value = name;
  cloudToken.value = token;
  localStorage.setItem("kp-cloud-server", server.value);
  localStorage.setItem("kp-cloud-name", name);
  localStorage.setItem("kp-cloud-token", token);
}

async function refreshProfile() {
  if (!cloudToken.value) { profile.value = null; return; }
  try {
    const res = await api("/api/me?token=" + encodeURIComponent(cloudToken.value));
    if (res.ok && res.profile) {
      profile.value = res.profile;
      return;
    }
  } catch {
    // server unreachable
  }
  // session expired or server down -> keep name, drop profile
  profile.value = null;
  if (!navigator.onLine) return;
  notice.value = "登录已失效，请重新登录";
  cloudToken.value = "";
  localStorage.removeItem("kp-cloud-token");
}

async function submitAuth() {
  notice.value = "";
  const name = formName.value.trim();
  const pass = formPass.value;
  if (!name || !pass) { notice.value = "请填写昵称和密码"; return; }
  busy.value = true;
  try {
    const res = await api(mode.value === "register" ? "/api/register" : "/api/login", { name, pass });
    if (res.ok && res.token) {
      saveSession(res.profile?.name || name, res.token);
      profile.value = res.profile ?? null;
      formPass.value = "";
      notice.value = mode.value === "register" ? "注册成功，已登录" : "登录成功";
      await refreshBoard();
    } else {
      notice.value = res.error || "请求失败";
    }
  } catch {
    notice.value = "无法连接服务器，请检查地址";
  }
  busy.value = false;
}

async function logout() {
  try { await api("/api/logout", { token: cloudToken.value }); } catch { /* ignore */ }
  cloudToken.value = "";
  profile.value = null;
  localStorage.removeItem("kp-cloud-token");
  notice.value = "已退出登录";
}

type BoardRow = { name: string; totalKeys: number; totalMouse: number; activeDays: number; streak: number; todayKeys: number };
const boardSorts = [
  { id: "total", name: "总按键" },
  { id: "today", name: "今日" },
  { id: "days", name: "活跃" },
  { id: "streak", name: "连击" },
];
const boardSort = ref("total");
const board = ref<BoardRow[]>([]);

async function refreshBoard() {
  if (!cloudToken.value) { board.value = []; return; }
  try {
    const res = await api("/api/leaderboard?sort=" + boardSort.value);
    if (res.ok) board.value = res.list;
  } catch {
    // server offline
  }
}

async function switchBoard(sortId: string) {
  boardSort.value = sortId;
  await refreshBoard();
}

onMounted(() => { refreshProfile(); refreshBoard(); });
</script>

<template>
  <div class="cloud-box">
    <div class="cloud-row">
      <label class="cloud-field"><span>服务器地址</span><input v-model="server" placeholder="http://127.0.0.1:7788" @change="refreshProfile" /></label>
    </div>

    <div v-if="!cloudToken" class="cloud-auth">
      <div class="cloud-tabs">
        <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
        <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
      </div>
      <div class="cloud-fields">
        <input v-model="formName" maxlength="16" placeholder="昵称（2-16 位）" />
        <input v-model="formPass" type="password" placeholder="密码（至少 4 位）" @keydown.enter="submitAuth" />
        <button class="cloud-submit" :disabled="busy" @click="submitAuth">{{ busy ? "处理中…" : mode === "register" ? "注册并登录" : "登录" }}</button>
      </div>
      <p v-if="notice" class="cloud-notice">{{ notice }}</p>
      <p class="cloud-tip">云端账号用于保存战绩排行与跨网络 PK；服务器请自行部署 server/pk-cloud-server.js</p>
    </div>

    <div v-else class="cloud-signed">
      <div class="cloud-me"><span class="cloud-avatar">{{ cloudName.slice(0, 1) }}</span><div><b>{{ cloudName }}</b><small>{{ profile ? `累计 ${profile.totalKeys} 键 · 今日 ${profile.todayKeys} · 活跃 ${profile.activeDays} 天 · 连击 ${profile.streak} 天` : "加载数据中…" }}</small></div></div>
      <div class="cloud-actions">
        <button class="cloud-submit ghost" @click="refreshProfile">刷新</button>
        <button class="cloud-submit ghost danger" @click="logout">退出登录</button>
      </div>
      <div class="cloud-board">
        <div class="cloud-board-head"><span>云端输入排行</span><span class="cloud-board-sorts"><button v-for="opt in boardSorts" :key="opt.id" :class="{ active: boardSort === opt.id }" @click="switchBoard(opt.id)">{{ opt.name }}</button></span></div>
        <div v-if="board.length === 0" class="cloud-board-empty">还没有数据，正在同步本机统计…</div>
        <div v-for="(row, index) in board" :key="row.name" class="cloud-board-row" :class="{ me: row.name === cloudName }">
          <span class="board-rank">{{ index + 1 }}</span>
          <span class="board-name">{{ row.name }}{{ row.name === cloudName ? "（我）" : "" }}</span>
          <span class="board-value">{{ row.totalKeys.toLocaleString() }} 键</span>
          <span class="board-sub">{{ boardSort === "today" ? "今日" : boardSort === "days" ? "活跃" : boardSort === "streak" ? "连击" : "累计" }} {{ boardSort === "today" ? row.todayKeys.toLocaleString() + " 键" : boardSort === "days" ? row.activeDays + " 天" : boardSort === "streak" ? row.streak + " 天" : row.totalMouse.toLocaleString() + " 鼠标" }}</span>
        </div>
      </div>
      <p v-if="notice" class="cloud-notice">{{ notice }}</p>
    </div>
  </div>
</template>

<style scoped>
.cloud-box { display: grid; gap: 8px; }
.cloud-field { display: grid; gap: 4px; color: var(--tx-faint); font-size: 9px; }
.cloud-field input, .cloud-fields input { padding: 7px 9px; border: 1px solid rgba(var(--line-rgb), .22); border-radius: 9px; color: var(--tx-strong); background: rgba(var(--ink-rgb), .3); font-size: 11px; }
.cloud-tabs { display: flex; gap: 6px; }
.cloud-tabs button { flex: 1; padding: 6px 0; border: 1px solid rgba(var(--line-rgb), .2); border-radius: 9px; color: var(--tx-soft); background: transparent; cursor: pointer; font-size: 10px; }
.cloud-tabs button.active { color: #fff; border-color: rgba(var(--cyan-rgb), .6); background: rgba(var(--cyan-rgb), .16); }
html[data-theme="starlight"] .cloud-tabs button.active, html[data-theme="latte"] .cloud-tabs button.active, html[data-theme="sage"] .cloud-tabs button.active, html[data-theme="matcha"] .cloud-tabs button.active { color: #1d1d1f; }
.cloud-fields { display: grid; gap: 6px; margin-top: 8px; }
.cloud-submit { padding: 7px 0; border: 0; border-radius: 9px; color: #fff; background: linear-gradient(135deg, var(--acc-cyan), var(--acc-violet)); font-size: 11px; font-weight: 800; cursor: pointer; }
.cloud-submit:disabled { opacity: .6; cursor: default; }
.cloud-submit.ghost { background: transparent; border: 1px solid rgba(var(--line-rgb), .22); color: var(--tx-soft); }
.cloud-submit.ghost.danger:hover { border-color: rgba(var(--pink-rgb), .6); color: var(--acc-pink-soft); }
.cloud-me { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border: 1px solid rgba(var(--line-rgb), .18); border-radius: 11px; }
.cloud-avatar { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; color: #fff; font-weight: 900; background: linear-gradient(135deg, var(--acc-pink), var(--acc-violet)); }
.cloud-me b, .cloud-me small { display: block; }
.cloud-me b { color: var(--tx-strong); font-size: 12px; }
.cloud-me small { margin-top: 2px; color: var(--tx-faint); font-size: 9px; }
.cloud-actions { display: flex; gap: 6px; }
.cloud-actions .cloud-submit { flex: 1; }
.cloud-notice { margin: 0; color: var(--acc-amber); font-size: 10px; }
.cloud-tip { margin: 0; color: var(--tx-faint); font-size: 8px; line-height: 1.6; }
.cloud-board { margin-top: 10px; }
.cloud-board-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px; color: var(--tx-faint); font-size: 9px; font-weight: 800; letter-spacing: .08em; }
.cloud-board-sorts { display: flex; gap: 4px; }
.cloud-board-sorts button { padding: 3px 7px; border: 1px solid rgba(var(--line-rgb), .2); border-radius: 7px; color: var(--tx-faint); background: transparent; cursor: pointer; font-size: 8px; }
.cloud-board-sorts button.active { color: #fff; border-color: rgba(var(--cyan-rgb), .55); background: rgba(var(--cyan-rgb), .14); }
html[data-theme="starlight"] .cloud-board-sorts button.active { color: #1d1d1f; }
.cloud-board-row { display: grid; grid-template-columns: 24px 1fr auto auto; gap: 8px; align-items: center; padding: 5px 8px; border-radius: 8px; color: var(--tx-soft); font-size: 10px; }
.cloud-board-row.me { background: rgba(var(--cyan-rgb), .1); }
.board-rank { color: var(--tx-faint); font-weight: 900; }
.board-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 700; color: var(--tx-strong); }
.board-value { font-variant-numeric: tabular-nums; }
.board-sub { color: var(--tx-faint); font-size: 8px; }
.cloud-board-empty { padding: 8px; color: var(--tx-faint); font-size: 9px; text-align: center; }

</style>
