<script setup lang="ts">
/** MiniStat — a small always-on-top chip showing today's totals (keys, mouse,
 * top key). Lives in the "keys-mini" window; listens to the same events the
 * dashboard does and follows the shared theme through localStorage. */
import { onMounted, onUnmounted, ref } from "vue";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";

type Snapshot = {
  date: string;
  totalKeyPresses: number;
  totalMouseActions: number;
  keys: Array<{ keyId: string; label: string; count: number }>;
  activity: Array<{ hour: number; count: number }>;
};

const totalKeys = ref(0);
const totalMouse = ref(0);
const champion = ref("—");
const recording = ref(true);

function fmt(value: number) {
  return value.toLocaleString("zh-CN");
}

function apply(snapshot: Snapshot) {
  totalKeys.value = snapshot.totalKeyPresses;
  totalMouse.value = snapshot.totalMouseActions;
  const top = [...snapshot.keys].sort((a, b) => b.count - a.count)[0];
  champion.value = top && top.count > 0 ? `${top.label} ×${fmt(top.count)}` : "暂无";
}

function syncTheme() {
  const saved = localStorage.getItem("keypulse-theme");
  if (saved) document.documentElement.dataset.theme = saved;
}

let stopStats: UnlistenFn | undefined;
let stopRecording: UnlistenFn | undefined;
let pollTimer: ReturnType<typeof setInterval> | undefined;

onMounted(async () => {
  document.documentElement.classList.add("keyshow-window");
  syncTheme();
  try {
    stopStats = await listen<Snapshot>("stats-updated", (event) => apply(event.payload));
    stopRecording = await listen<boolean>("recording-changed", (event) => {
      recording.value = event.payload;
    });
  } catch {
    // overlay window without event permission falls back to polling the store
  }
  pollTimer = setInterval(() => {
    syncTheme();
    invoke<Snapshot>("get_dashboard", { range: "today" })
      .then((snapshot) => {
        if (snapshot.totalKeyPresses !== totalKeys.value || snapshot.totalMouseActions !== totalMouse.value) {
          apply(snapshot);
        }
      })
      .catch(() => undefined);
  }, 2000);
});

onUnmounted(() => {
  stopStats?.();
  stopRecording?.();
  if (pollTimer) clearInterval(pollTimer);
  document.documentElement.classList.remove("keyshow-window");
});
</script>

<template>
  <div class="mini-card" :data-recording="recording">
    <div class="mini-brand"><i class="mini-logo"></i><span>KeyPulse</span><i class="mini-live" :class="{ paused: !recording }"></i></div>
    <div class="mini-row"><span class="mini-key">KEY</span><b>{{ fmt(totalKeys) }}</b><span class="mini-key mouse">MOUSE</span><b>{{ fmt(totalMouse) }}</b></div>
    <div class="mini-foot">冠军键 <b>{{ champion }}</b></div>
  </div>
</template>

<style scoped>
.keyshow-root-mini { position: fixed; inset: 0; }
.mini-card { position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; gap: 5px; padding: 10px 14px; border: 1px solid rgba(var(--line-rgb), .4); border-radius: 16px; background: rgba(var(--pop-rgb), .78); backdrop-filter: blur(10px); box-shadow: 0 12px 34px rgba(0, 0, 0, .28), inset 0 1px rgba(255, 255, 255, .12); font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif; }
.mini-brand { display: flex; align-items: center; gap: 6px; color: var(--tx-dim); font-size: 9px; font-weight: 800; letter-spacing: .14em; }
.mini-logo { width: 10px; height: 10px; border-radius: 3px; background: linear-gradient(135deg, var(--acc-cyan), var(--acc-violet)); transform: rotate(-8deg); }
.mini-live { width: 6px; height: 6px; margin-left: auto; border-radius: 50%; background: var(--acc-green); box-shadow: 0 0 8px var(--acc-green); }
.mini-live.paused { background: var(--tx-mute); box-shadow: none; }
.mini-row { display: flex; align-items: baseline; gap: 7px; color: var(--tx-strong); }
.mini-key { color: var(--tx-faint); font-size: 8px; font-weight: 800; letter-spacing: .1em; }
.mini-key.mouse { margin-left: 6px; }
.mini-row b { font-size: 17px; font-variant-numeric: tabular-nums; letter-spacing: -.02em; }
.mini-foot { color: var(--tx-dim); font-size: 9px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mini-foot b { color: var(--acc-pink-soft); font-weight: 700; }
html[data-theme="starlight"] .mini-card { background: rgba(250, 250, 252, .85); }
</style>
