<script setup lang="ts">
/** LoginPortal — futuristic full-screen gateway: cloud account auth and LAN
 * device discovery in one place. Writes the same localStorage session keys as
 * the settings cloud panel, so the duel/leaderboard sync picks it up. */
import { onMounted, onUnmounted, ref } from "vue";
import { invoke } from "@tauri-apps/api/core";

const emit = defineEmits<{ (e: "close"): void; (e: "open-pk"): void }>();

type CloudProfile = {
  name: string; best: number; wins: number; losses: number; games: number;
  totalKeys: number; totalMouse: number; activeDays: number; streak: number; todayKeys: number;
};
type LanDevice = { name: string; host: string; port: number; totalKeys?: number; todayKeys?: number; activeDays?: number; streak?: number };

const server = ref(localStorage.getItem("kp-cloud-server") || "http://127.0.0.1:7788");
const cloudName = ref(localStorage.getItem("kp-cloud-name") || "");
const cloudToken = ref(localStorage.getItem("kp-cloud-token") || "");
const profile = ref<CloudProfile | null>(null);
const tab = ref<"cloud" | "lan">("cloud");
const mode = ref<"login" | "register">("login");
const formName = ref("");
const formPass = ref("");
const notice = ref("");
const busy = ref(false);

const lanDevices = ref<LanDevice[]>([]);
const scanning = ref(false);
const lanNotice = ref("");

async function api(path: string, body?: unknown) {
  const res = await fetch(server.value + path, {
    method: body ? "POST" : "GET",
    headers: { "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

async function refreshProfile() {
  if (!cloudToken.value) { profile.value = null; return; }
  try {
    const res = await api("/api/me?token=" + encodeURIComponent(cloudToken.value));
    profile.value = res.ok ? res.profile : null;
  } catch {
    profile.value = null;
  }
}

async function submitAuth() {
  notice.value = "";
  const name = formName.value.trim();
  if (!name || !formPass.value) { notice.value = "请填写昵称和密码"; return; }
  busy.value = true;
  try {
    const res = await api(mode.value === "register" ? "/api/register" : "/api/login", { name, pass: formPass.value });
    if (res.ok && res.token) {
      cloudName.value = res.profile?.name || name;
      cloudToken.value = res.token;
      profile.value = res.profile ?? null;
      localStorage.setItem("kp-cloud-server", server.value);
      localStorage.setItem("kp-cloud-name", cloudName.value);
      localStorage.setItem("kp-cloud-token", res.token);
      window.dispatchEvent(new Event("kp-cloud-changed"));
      notice.value = mode.value === "register" ? "注册成功，已接入云端" : "已连接云端";
      formPass.value = "";
    } else {
      notice.value = res.error || "请求失败";
    }
  } catch {
    notice.value = "无法连接服务器，请检查地址与网络";
  }
  busy.value = false;
}

async function logout() {
  try { await api("/api/logout", { token: cloudToken.value }); } catch { /* offline */ }
  cloudToken.value = "";
  profile.value = null;
  localStorage.removeItem("kp-cloud-token");
  window.dispatchEvent(new Event("kp-cloud-changed"));
  notice.value = "已断开云端连接";
}

/** Brief discovery burst: advertise for 4s, then collect found peers. */
async function scanLan() {
  if (scanning.value) return;
  scanning.value = true;
  lanNotice.value = "正在扫描同网段设备…";
  try {
    const profile = await invoke<{ name: string }>("get_pk_profile").catch(() => null);
    const stats = await invoke<{ totalKeys: number; todayKeys: number; activeDays: number; streak: number }>("get_local_stats").catch(() => null);
    await invoke("pk_start", {
      name: profile?.name || "扫描中",
      best: 0, wins: 0, losses: 0, games: 0,
      totalKeys: stats?.totalKeys || 0, todayKeys: stats?.todayKeys || 0,
      activeDays: stats?.activeDays || 0, streak: stats?.streak || 0,
    }).catch(() => undefined);
    await new Promise((r) => setTimeout(r, 4200));
    await invoke("pk_stop").catch(() => undefined);
    lanDevices.value = await invoke<LanDevice[]>("pk_peers").catch(() => []);
    lanNotice.value = lanDevices.value.length
      ? `发现 ${lanDevices.value.length} 台设备`
      : "未发现设备——请确认对方也打开了 KeyPulse 并保持同一网络";
  } catch (error) {
    lanNotice.value = String(error);
  }
  scanning.value = false;
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") emit("close");
}

onMounted(() => {
  refreshProfile();
  document.addEventListener("keydown", onKeydown);
});
onUnmounted(() => document.removeEventListener("keydown", onKeydown));
</script>

<template>
  <div class="portal-page" role="dialog" aria-label="登录与连接">
    <button class="portal-back" @click="emit('close')">← 返回仪表盘</button>
    <div class="portal-grid" aria-hidden="true"></div>
    <section class="portal-card">
      <button class="portal-close" aria-label="关闭登录界面" @click="emit('close')">×</button>

      <div class="portal-brand">
        <p class="portal-eyebrow">KEYPULSE NETWORK</p>
        <h2>接入你的<br /><em>输入网络</em></h2>
        <p class="portal-copy">登录云端保存战绩排行，或直接发现同网段的 KeyPulse 设备。</p>
        <ul class="portal-points">
          <li><i>◈</i>云端数据排行 · 累计/今日/活跃/连击</li>
          <li><i>◈</i>局域网发现 · 无需服务器即可互见</li>
          <li><i>◈</i>本机优先 · 不登录也完整可用</li>
        </ul>
        <div class="portal-status">
          <template v-if="cloudToken && profile">
            <span class="portal-dot on"></span>已连接 <b>{{ cloudName }}</b>
          </template>
          <template v-else>
            <span class="portal-dot"></span>未连接云端
          </template>
        </div>
      </div>

      <div class="portal-main">
        <div class="portal-tabs" role="tablist">
          <button role="tab" :aria-selected="tab === 'cloud'" :class="{ active: tab === 'cloud' }" @click="tab = 'cloud'">云端账号</button>
          <button role="tab" :aria-selected="tab === 'lan'" :class="{ active: tab === 'lan' }" @click="tab = 'lan'">局域网连接</button>
        </div>

        <div v-if="tab === 'cloud'" class="portal-pane">
          <label class="portal-field"><span>服务器地址</span>
            <input v-model="server" placeholder="http://127.0.0.1:7788" @change="refreshProfile" />
          </label>
          <template v-if="!cloudToken">
            <div class="portal-modes">
              <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
              <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
            </div>
            <input v-model="formName" maxlength="16" placeholder="昵称（2-16 位）" />
            <input v-model="formPass" type="password" placeholder="密码（至少 4 位）" @keydown.enter="submitAuth" />
            <button class="portal-submit" :disabled="busy" @click="submitAuth">{{ busy ? "连接中…" : mode === "register" ? "注册并接入" : "接入云端" }}</button>
          </template>
          <template v-else>
            <div class="portal-me">
              <span class="portal-avatar">{{ cloudName.slice(0, 1) }}</span>
              <div><b>{{ cloudName }}</b><small v-if="profile">累计 {{ profile.totalKeys.toLocaleString() }} 键 · 活跃 {{ profile.activeDays }} 天 · 连击 {{ profile.streak }} 天</small><small v-else>云端数据加载中…</small></div>
            </div>
            <button class="portal-submit ghost" @click="logout">断开连接</button>
          </template>
          <p v-if="notice" class="portal-notice">{{ notice }}</p>
        </div>

        <div v-else class="portal-pane">
          <p class="portal-lan-copy">局域网模式无需服务器：同一 WiFi 下的 KeyPulse 会互相广播，直接在 PK 面板查看彼此的数据排行。</p>
          <button class="portal-submit" :disabled="scanning" @click="scanLan">{{ scanning ? "扫描中…" : "◎ 扫描局域网设备" }}</button>
          <p v-if="lanNotice" class="portal-notice">{{ lanNotice }}</p>
          <div class="portal-devices">
            <div v-for="device in lanDevices" :key="device.host + device.port" class="portal-device">
              <span class="portal-device-dot"></span>
              <b>{{ device.name }}</b>
              <small>{{ device.host }}</small>
              <span class="portal-device-keys">{{ (device.totalKeys || 0).toLocaleString() }} 键</span>
            </div>
          </div>
          <button class="portal-submit ghost" @click="emit('open-pk')">⚔ 打开局域网排行 / 对战面板</button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.portal-page { position: relative; display: grid; place-items: start center; padding: 6px 0 26px; }
.portal-back { position: relative; z-index: 2; justify-self: start; margin: 0 0 10px; padding: 8px 15px; border: 1px solid rgba(var(--line-rgb), .22); border-radius: 999px; color: var(--tx-soft); background: rgba(var(--panel-rgb), .6); cursor: pointer; font-size: 11px; font-weight: 700; transition: all .15s ease; }
.portal-back:hover { color: var(--text-main); border-color: rgba(var(--cyan-rgb), .65); }
.portal-grid { position: absolute; inset: -10px 0 0; pointer-events: none; opacity: .5; background-image: linear-gradient(rgba(var(--cyan-rgb), .05) 1px, transparent 1px), linear-gradient(90deg, rgba(var(--cyan-rgb), .05) 1px, transparent 1px); background-size: 44px 44px; animation: grid-drift 24s linear infinite; }
@keyframes grid-drift { to { background-position: 44px 44px; } }
.portal-card { position: relative; display: grid; grid-template-columns: minmax(210px, 250px) 1fr; width: min(100%, 720px); border-radius: 22px; background: linear-gradient(150deg, rgba(var(--panel-rgb), .97), rgba(var(--pop-rgb), .97)); box-shadow: 0 40px 120px rgba(0, 0, 0, .5), inset 0 0 0 1px rgba(var(--line-rgb), .18); overflow: hidden; }
.portal-card::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent, var(--acc-cyan), var(--acc-violet), transparent); animation: portal-sweep 3.2s ease infinite; }
@keyframes portal-sweep { 0% { opacity: .4; } 50% { opacity: 1; } 100% { opacity: .4; } }
.portal-close { position: absolute; z-index: 2; top: 14px; right: 14px; width: 32px; height: 32px; border: 1px solid rgba(var(--line-rgb), .25); border-radius: 50%; color: var(--tx-soft); background: rgba(var(--ink-rgb), .3); cursor: pointer; font-size: 20px; line-height: 1; }
.portal-close:hover { color: var(--text-main); border-color: rgba(var(--cyan-rgb), .7); }
.portal-brand { padding: 30px 24px; background: linear-gradient(165deg, rgba(var(--cyan-rgb), .12), rgba(var(--violet-rgb), .14) 70%, transparent); border-right: 1px solid rgba(var(--line-rgb), .16); }
.portal-eyebrow { margin: 0; color: var(--acc-cyan-bright); font-size: 9px; font-weight: 900; letter-spacing: .3em; }
.portal-brand h2 { margin: 12px 0 0; font-size: 27px; line-height: 1.2; letter-spacing: -.04em; }
.portal-brand h2 em { color: var(--acc-pink-soft); font-style: normal; }
.portal-copy { margin: 12px 0 0; color: var(--tx-soft); font-size: 11px; line-height: 1.7; }
.portal-points { margin: 16px 0 0; padding: 0; list-style: none; display: grid; gap: 8px; }
.portal-points li { display: flex; align-items: center; gap: 8px; color: var(--tx-soft); font-size: 10px; }
.portal-points i { color: var(--acc-cyan); font-style: normal; font-size: 9px; }
.portal-status { display: flex; align-items: center; gap: 8px; margin-top: 22px; padding: 9px 12px; border: 1px solid rgba(var(--line-rgb), .2); border-radius: 11px; color: var(--tx-faint); font-size: 10px; }
.portal-status b { color: var(--tx-strong); }
.portal-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--tx-mute); }
.portal-dot.on { background: var(--acc-green); box-shadow: 0 0 10px var(--acc-green); }
.portal-main { padding: 24px; display: flex; flex-direction: column; gap: 10px; }
.portal-tabs { display: flex; gap: 6px; margin-bottom: 6px; }
.portal-tabs button { flex: 1; padding: 9px 0; border: 1px solid rgba(var(--line-rgb), .2); border-radius: 11px; color: var(--tx-soft); background: rgba(var(--ink-rgb), .25); cursor: pointer; font-size: 12px; font-weight: 700; transition: all .15s ease; }
.portal-tabs button.active { color: var(--text-main); border-color: rgba(var(--cyan-rgb), .65); background: rgba(var(--cyan-rgb), .12); box-shadow: 0 0 18px rgba(var(--cyan-rgb), .14); }
.portal-pane { display: flex; flex-direction: column; gap: 9px; }
.portal-field { display: grid; gap: 4px; color: var(--tx-faint); font-size: 9px; }
.portal-main input { padding: 10px 12px; border: 1px solid rgba(var(--line-rgb), .24); border-radius: 11px; color: var(--tx-strong); background: rgba(var(--ink-rgb), .3); font-size: 12px; }
.portal-main input:focus { outline: none; border-color: rgba(var(--cyan-rgb), .7); box-shadow: 0 0 0 3px rgba(var(--cyan-rgb), .12); }
.portal-modes { display: flex; gap: 6px; }
.portal-modes button { flex: 1; padding: 6px 0; border: 1px solid rgba(var(--line-rgb), .2); border-radius: 9px; color: var(--tx-faint); background: transparent; cursor: pointer; font-size: 10px; }
.portal-modes button.active { color: var(--text-main); border-color: rgba(var(--cyan-rgb), .55); background: rgba(var(--cyan-rgb), .1); }
.portal-submit { padding: 11px 0; border: 0; border-radius: 12px; color: #fff; background: linear-gradient(135deg, var(--acc-cyan), var(--acc-violet)); font-size: 12px; font-weight: 900; cursor: pointer; letter-spacing: .04em; box-shadow: 0 8px 24px rgba(var(--cyan-rgb), .25); }
.portal-submit:hover { filter: brightness(1.1); }
.portal-submit:disabled { opacity: .55; cursor: default; }
.portal-submit.ghost { background: transparent; border: 1px solid rgba(var(--line-rgb), .24); color: var(--tx-soft); box-shadow: none; }
.portal-submit.ghost:hover { border-color: rgba(var(--cyan-rgb), .6); color: var(--text-main); }
.portal-notice { margin: 0; color: var(--acc-amber); font-size: 10px; }
.portal-lan-copy { margin: 0; color: var(--tx-soft); font-size: 11px; line-height: 1.7; }
.portal-me { display: flex; align-items: center; gap: 11px; padding: 11px 13px; border: 1px solid rgba(var(--line-rgb), .2); border-radius: 13px; }
.portal-avatar { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 50%; color: #fff; font-weight: 900; font-size: 15px; background: linear-gradient(135deg, var(--acc-cyan), var(--acc-violet)); }
.portal-me b, .portal-me small { display: block; }
.portal-me b { color: var(--tx-strong); font-size: 13px; }
.portal-me small { margin-top: 2px; color: var(--tx-faint); font-size: 9px; }
.portal-devices { display: grid; gap: 5px; }
.portal-device { display: grid; grid-template-columns: 10px 1fr auto auto; gap: 8px; align-items: center; padding: 7px 10px; border: 1px solid rgba(var(--line-rgb), .16); border-radius: 10px; color: var(--tx-soft); font-size: 10px; }
.portal-device-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--acc-green); box-shadow: 0 0 8px var(--acc-green); }
.portal-device b { color: var(--tx-strong); font-size: 11px; }
.portal-device small { color: var(--tx-faint); }
.portal-device-keys { font-variant-numeric: tabular-nums; color: var(--tx-dim); }
@media (max-width: 720px) {
  .portal-card { grid-template-columns: 1fr; }
  .portal-brand { border-right: none; border-bottom: 1px solid rgba(var(--line-rgb), .16); padding: 22px 20px 16px; }
  .portal-points { display: none; }
  .portal-status { margin-top: 14px; }
}
</style>
