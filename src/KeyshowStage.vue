<script setup lang="ts">
/**
 * KeyshowStage — the transparent always-on-top overlay shown at the bottom of
 * the screen. Renders accepted physical key/mouse presses in one of three
 * switchable styles: capsule stream, particle trail, or a mini keyboard mirror.
 * Style and theme are shared with the main window through localStorage.
 */
import { onMounted, onUnmounted, ref } from "vue";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

type KeyShowEvent = { kind: "key" | "mouse"; label: string; keyId: string; action: "down" | "up" };

const MOD_KEYS = new Set([
  "ctrl-left", "ctrl-right", "alt-left", "alt-right",
  "shift-left", "shift-right", "win-left", "win-right", "menu",
]);

type StyleMode = "capsule" | "particle" | "mirror";
const mode = ref<StyleMode>((localStorage.getItem("keypulse-keyshow-style") as StyleMode) || "capsule");
const showHint = ref(true);

// ---------- shared event sink ----------
type CapsuleSegment = { label: string; mod: boolean };
type Capsule = { id: number; kind: "key" | "mouse"; segments: CapsuleSegment[]; count: number; born: number };
const capsules = ref<Capsule[]>([]);
let capsuleSeq = 0;

// mirror keyboard state: keyId -> pressed-at timestamp; a lost keyup fades out
// after MIRROR_LIT_TTL so the board can never stay stuck lit.
const litKeys = ref<Record<string, number>>({});
const MIRROR_LIT_TTL = 4000;
const recentChips = ref<{ id: number; label: string; kind: string }[]>([]);
let chipSeq = 0;

// particle burst queue
type Burst = { id: number; label: string; heat: number };
const bursts = ref<Burst[]>([]);
let burstSeq = 0;
const recentHeat = new Map<string, number[]>();

// capsule combo pending modifiers
const pendingMods: CapsuleSegment[] = [];
let modCommitTimer: ReturnType<typeof setTimeout> | undefined;
let hideTimer: ReturnType<typeof setTimeout> | undefined;

function isModKey(keyId: string) {
  return MOD_KEYS.has(keyId);
}

function commitPendingMods() {
  if (modCommitTimer) clearTimeout(modCommitTimer);
  modCommitTimer = undefined;
  if (pendingMods.length) {
    pushCapsule(pendingMods.splice(0), 1);
  }
}

function pushCapsule(segments: CapsuleSegment[], count: number) {
  const cap: Capsule = { id: ++capsuleSeq, kind: "key", segments, count, born: Date.now() };
  capsules.value = [...capsules.value, cap].slice(-8);
  refreshHideTimer();
}

function onCapsuleDown(event: KeyShowEvent) {
  if (event.action !== "down") return;
  const now = Date.now();
  if (event.kind === "mouse") {
    pushCapsule([{ label: `🖱 ${event.label}`, mod: false }], 1);
    return;
  }
  if (isModKey(event.keyId)) {
    if (!pendingMods.some((mod) => mod.label === event.label)) {
      pendingMods.push({ label: event.label, mod: true });
      if (modCommitTimer) clearTimeout(modCommitTimer);
      // Modifier held alone becomes visible shortly; a normal key pressed
      // within this window merges into one combo capsule instead.
      modCommitTimer = setTimeout(commitPendingMods, 320);
    }
    return;
  }
  if (pendingMods.length) {
    if (modCommitTimer) clearTimeout(modCommitTimer);
    modCommitTimer = undefined;
    pushCapsule([...pendingMods.splice(0), { label: event.label, mod: false }], 1);
    return;
  }
  const last = capsules.value[capsules.value.length - 1];
  if (last && last.kind === "key" && last.segments.length === 1 && !last.segments[0].mod
    && last.segments[0].label === event.label && now - last.born < 900) {
    last.count += 1;
    last.born = now;
    capsules.value = [...capsules.value];
    refreshHideTimer();
    return;
  }
  pushCapsule([{ label: event.label, mod: false }], 1);
}

function onCapsuleUp(event: KeyShowEvent) {
  if (event.kind === "mouse") return;
  if (isModKey(event.keyId)) {
    const index = pendingMods.findIndex((mod) => mod.label === event.label);
    if (index >= 0) {
      pendingMods.splice(index, 1);
      // A modifier tapped alone (no key followed within the merge window)
      // becomes a normal capsule so single Ctrl/Shift presses are visible.
      pushCapsule([{ label: event.label, mod: false }], 1);
    }
    if (!pendingMods.length && modCommitTimer) {
      clearTimeout(modCommitTimer);
      modCommitTimer = undefined;
    }
  }
}

function refreshHideTimer() {
  if (hideTimer) clearTimeout(hideTimer);
  hideTimer = setTimeout(() => {
    if (capsules.value.length) capsules.value = [];
  }, 2600);
}

// ---------- mirror ----------
function onMirrorEvent(event: KeyShowEvent) {
  if (event.kind === "key") {
    if (event.action === "down") {
      litKeys.value = { ...litKeys.value, [event.keyId]: Date.now() };
      recentChips.value = [
        ...recentChips.value.slice(-11),
        { id: ++chipSeq, label: event.label, kind: event.kind },
      ];
    } else {
      litKeys.value = { ...litKeys.value, [event.keyId]: 0 };
    }
  } else if (event.action === "down") {
    recentChips.value = [
      ...recentChips.value.slice(-11),
      { id: ++chipSeq, label: `🖱 ${event.label}`, kind: event.kind },
    ];
  }
}

// ---------- particle ----------
function onParticleEvent(event: KeyShowEvent) {
  if (event.action !== "down") return;
  const now = Date.now();
  const times = (recentHeat.get(event.keyId) ?? []).filter((ts) => now - ts < 1200);
  times.push(now);
  recentHeat.set(event.keyId, times);
  const id = ++burstSeq;
  bursts.value = [...bursts.value.slice(-3), { id, label: event.label, heat: times.length }];
  setTimeout(() => {
    bursts.value = bursts.value.filter((burst) => burst.id !== id);
  }, 950);
}

function routeEvent(event: KeyShowEvent) {
  onParticleEvent(event);
  onCapsuleDown(event);
  onCapsuleUp(event);
  onMirrorEvent(event);
}

// ---------- mirror keyboard layout ----------
const mirrorRows: { label: string; keyId: string; width?: number }[][] = [
  ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"].map((l) => ({ label: l, keyId: l.toLowerCase() })),
  ["A", "S", "D", "F", "G", "H", "J", "K", "L"].map((l) => ({ label: l, keyId: l.toLowerCase() })),
  ["Z", "X", "C", "V", "B", "N", "M"].map((l) => ({ label: l, keyId: l.toLowerCase() })),
  [
    { label: "Ctrl", keyId: "ctrl-left" },
    { label: "Alt", keyId: "alt-left" },
    { label: "Space", keyId: "space", width: 5 },
    { label: "⌫", keyId: "backspace" },
    { label: "Enter", keyId: "enter" },
  ],
];

function isKeyLit(keyId: string) {
  const pressedAt = litKeys.value[keyId];
  return !!pressedAt && Date.now() - pressedAt < MIRROR_LIT_TTL;
}

function expireStaleLitKeys() {
  const now = Date.now();
  const stale = Object.entries(litKeys.value).filter(([, ts]) => !!ts && now - ts >= MIRROR_LIT_TTL);
  if (stale.length) {
    const next = { ...litKeys.value };
    for (const [keyId] of stale) next[keyId] = 0;
    litKeys.value = next;
  }
}

// ---------- lifecycle ----------
let stopListener: UnlistenFn | undefined;
let stopStorage: (() => void) | undefined;

function syncTheme() {
  const saved = localStorage.getItem("keypulse-theme");
  if (saved) document.documentElement.dataset.theme = saved;
}

function showFirstHint() {
  showHint.value = true;
  setTimeout(() => { showHint.value = false; }, 4000);
}

onMounted(async () => {
  document.documentElement.classList.add("keyshow-window");
  syncTheme();
  showFirstHint();
  stopListener = await listen<KeyShowEvent>("keyshow-event", (event) => {
    routeEvent(event.payload);
  });
  // Test hook for automated GUI acceptance (injects a synthetic key event).
  (window as unknown as Record<string, unknown>).__keyshowEvent = (payload: KeyShowEvent) => {
    routeEvent(payload);
  };
  stopStorage = () => {
    window.removeEventListener("storage", onStorage);
    if (pollTimer) clearInterval(pollTimer);
  };
  window.addEventListener("storage", onStorage);
  pollTimer = setInterval(pollSharedPrefs, 300);
});

let lastStyle = localStorage.getItem("keypulse-keyshow-style") || "capsule";
let lastTheme = localStorage.getItem("keypulse-theme") || "neon";
let pollTimer: ReturnType<typeof setInterval> | undefined;

// Storage events are not reliably delivered between WebView2 windows, so also
// poll the shared localStorage values and apply changes when they drift.
function pollSharedPrefs() {
  expireStaleLitKeys();
  const style = localStorage.getItem("keypulse-keyshow-style") || "capsule";
  if (style !== lastStyle) {
    lastStyle = style;
    mode.value = style as StyleMode;
  }
  const theme = localStorage.getItem("keypulse-theme");
  if (theme && theme !== lastTheme) {
    lastTheme = theme;
    syncTheme();
  }
}

function onStorage(event: StorageEvent) {
  if (event.key === "keypulse-theme") {
    lastTheme = event.newValue || lastTheme;
    syncTheme();
  }
  if (event.key === "keypulse-keyshow-style") {
    lastStyle = event.newValue || lastStyle;
    mode.value = lastStyle as StyleMode;
  }
}

onUnmounted(() => {
  stopListener?.();
  stopStorage?.();
  document.documentElement.classList.remove("keyshow-window");
  if (hideTimer) clearTimeout(hideTimer);
  if (modCommitTimer) clearTimeout(modCommitTimer);
});
</script>

<template>
  <div class="keyshow-root" :data-caps="capsules.length" :data-bursts="bursts.length" :data-mode="mode">
    <p v-if="showHint" class="keyshow-hint">按键可视化已开启 — 按下的键会出现在这里 · 可在主界面切换风格</p>

    <!-- 节奏胶囊流 -->
    <div v-if="mode === 'capsule'" class="capsule-stage" aria-hidden="true">
      <TransitionGroup name="cap">
        <div v-for="cap in capsules" :key="cap.id" class="cap-row">
          <template v-for="(segment, index) in cap.segments" :key="index">
            <span v-if="segment.mod" class="cap mod" :class="{ glow: cap.count > 1 }">{{ segment.label }}</span>
            <span v-else-if="cap.kind === 'mouse'" class="cap mouse">{{ segment.label }}</span>
            <span v-else class="cap key">{{ segment.label }}</span>
          </template>
          <span v-if="cap.count > 1" class="cap count">×{{ cap.count }}</span>
        </div>
      </TransitionGroup>
    </div>

    <!-- 能量粒子轨迹 -->
    <div v-if="mode === 'particle'" class="particle-stage" aria-hidden="true">
      <div v-for="(burst, bIndex) in bursts" :key="burst.id" class="burst" :data-heat="burst.heat" :style="{ '--burst-index': bIndex }">
        <span class="burst-label">{{ burst.label }}</span>
        <i v-for="n in 7" :key="n" class="spark" :style="{ '--i': n }"></i>
      </div>
    </div>

    <!-- 迷你键盘镜像 -->
    <div v-if="mode === 'mirror'" class="mirror-stage" aria-hidden="true">
      <div class="mirror-board">
        <div v-for="(row, rowIndex) in mirrorRows" :key="rowIndex" class="mirror-row">
          <div v-for="key in row" :key="key.keyId" class="mirror-key" :class="{ lit: isKeyLit(key.keyId), wide: key.width }">{{ key.label }}</div>
        </div>
      </div>
      <div class="mirror-chips">
        <span v-for="chip in recentChips" :key="chip.id" class="mirror-chip">{{ chip.label }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.keyshow-root { position: fixed; inset: 0; display: flex; align-items: end; justify-content: center; overflow: hidden; pointer-events: none; user-select: none; }
.keyshow-hint { position: absolute; top: 6px; left: 50%; transform: translateX(-50%); padding: 6px 14px; border: 1px solid rgba(148,163,184,.2); border-radius: 999px; color: rgba(148,163,184,.9); background: rgba(4,9,24,.55); font-size: 11px; white-space: nowrap; animation: hint-in .3s ease; }
@keyframes hint-in { from { opacity: 0; transform: translateX(-50%) translateY(6px); } }

/* ---------- capsule stream ---------- */
.capsule-stage { display: flex; gap: 10px; align-items: center; justify-content: center; padding-bottom: 14px; }
.cap-row { display: flex; gap: 5px; align-items: center; }
.cap { display: inline-grid; place-items: center; min-width: 34px; height: 34px; padding: 0 10px; border-radius: 9px; font-weight: 800; font-size: 16px; letter-spacing: .02em; background: rgba(15, 23, 42, .62); color: #f8fafc; box-shadow: 0 6px 18px rgba(0,0,0,.35), inset 0 0 0 1px rgba(148,163,184,.22); backdrop-filter: blur(2px); }
.cap.key { color: #fff; box-shadow: 0 6px 20px rgba(0,0,0,.4), inset 0 0 0 1px rgba(var(--cyan-rgb),.55); text-shadow: 0 0 14px rgba(var(--cyan-rgb),.8); }
.cap.mod { background: rgba(var(--pink-rgb),.24); box-shadow: 0 6px 20px rgba(var(--pink-rgb),.28), inset 0 0 0 1px rgba(var(--pink-rgb),.7); color: #fff; }
.cap.mod.glow { animation: mod-pulse .7s ease infinite alternate; }
.cap.mouse { background: rgba(var(--violet-rgb),.22); box-shadow: 0 6px 20px rgba(var(--violet-rgb),.25), inset 0 0 0 1px rgba(var(--violet-rgb),.65); color: #fff; }
.cap.count { min-width: auto; height: auto; padding: 3px 7px; border-radius: 7px; background: rgba(var(--amber-rgb),.25); box-shadow: inset 0 0 0 1px rgba(var(--amber-rgb),.6); color: #fff; font-size: 12px; }
@keyframes mod-pulse { from { transform: scale(1); } to { transform: scale(1.07); } }
.cap-enter-active { animation: cap-in .18s cubic-bezier(.2, 1.6, .4, 1); }
.cap-enter-from { opacity: 0; transform: translateY(16px) scale(.6); }
.cap-leave-active { animation: cap-out .22s ease forwards; }
.cap-leave-to { opacity: 0; transform: translateY(-8px) scale(.7); }
@keyframes cap-in { from { opacity: 0; transform: translateY(16px) scale(.6); } }
@keyframes cap-out { to { opacity: 0; transform: translateY(-8px) scale(.7); } }
.cap-row-leave-active { transition: none; }

/* ---------- particle trail ---------- */
.particle-stage { position: relative; width: 100%; height: 100%; }
.burst { position: absolute; left: 50%; bottom: 46px; display: flex; align-items: center; justify-content: center; animation: burst-rise .95s ease-out forwards; }
.burst-label { font-size: 34px; font-weight: 900; color: var(--text-main); text-shadow: 0 0 22px rgba(var(--cyan-rgb),.95); animation: label-flicker .9s ease-out; }
.burst.heat-2 .burst-label { color: #ffe9a8; text-shadow: 0 0 26px rgba(var(--amber-rgb),1); }
.burst.heat-3 .burst-label { color: #ffd0dd; text-shadow: 0 0 30px rgba(var(--pink-rgb),1); }
.burst.heat-4 .burst-label { color: #fff; text-shadow: 0 0 34px rgba(var(--pink-rgb),1), 0 0 14px #fff; }
.spark { position: absolute; left: 50%; top: 50%; width: 5px; height: 5px; border-radius: 50%; background: var(--acc-cyan); box-shadow: 0 0 8px var(--acc-cyan); animation: spark-fly .9s ease-out forwards; }
.burst.heat-2 .spark { background: var(--acc-amber); box-shadow: 0 0 10px var(--acc-amber); }
.burst.heat-3 .spark, .burst.heat-4 .spark { background: var(--acc-pink); box-shadow: 0 0 12px var(--acc-pink); }
.spark:nth-child(2) { --i: 1; } .spark:nth-child(3) { --i: 2; } .spark:nth-child(4) { --i: 3; }
.spark:nth-child(5) { --i: 4; } .spark:nth-child(6) { --i: 5; } .spark:nth-child(7) { --i: 6; }
@keyframes burst-rise { 0% { transform: translate(-50%, 0) scale(.6); opacity: 0; } 14% { opacity: 1; transform: translate(-50%, -12px) scale(1); } 100% { transform: translate(-50%, -118px) scale(.86); opacity: 0; } }
@keyframes label-flicker { 0% { opacity: 0; } 12% { opacity: 1; } 70% { opacity: 1; } 100% { opacity: 0; } }
@keyframes spark-fly { 0% { transform: translate(-50%, -50%) translate(0, 0) scale(1); opacity: 1; } 100% { transform: translate(-50%, -50%) translate(calc((var(--i) - 3) * 26px), -140px) scale(0); opacity: 0; } }

/* ---------- mirror keyboard ---------- */
.mirror-stage { display: flex; flex-direction: column; align-items: center; gap: 8px; padding-bottom: 10px; }
.mirror-board { display: flex; flex-direction: column; gap: 5px; padding: 9px 10px; border-radius: 12px; background: rgba(4, 9, 24, .5); box-shadow: 0 10px 26px rgba(0,0,0,.3), inset 0 0 0 1px rgba(148,163,184,.14); }
.mirror-row { display: flex; gap: 5px; justify-content: center; }
.mirror-key { display: grid; place-items: center; width: 38px; height: 30px; border-radius: 6px; color: rgba(226, 232, 240, .45); background: rgba(30, 41, 59, .55); font-size: 11px; font-weight: 700; transition: all .12s ease; box-shadow: inset 0 0 0 1px rgba(148,163,184,.1); }
.mirror-key.wide { width: 150px; }
.mirror-key.lit { color: #fff; background: linear-gradient(180deg, rgba(var(--cyan-rgb),.9), rgba(var(--violet-rgb),.75)); box-shadow: 0 0 16px rgba(var(--cyan-rgb),.9), inset 0 0 0 1px rgba(255,255,255,.35); transform: translateY(-1px); }
.mirror-chips { display: flex; gap: 4px; max-width: 90%; overflow: hidden; }
.mirror-chip { padding: 2px 7px; border-radius: 5px; color: #dbe4f3; background: rgba(15, 23, 42, .66); font-size: 10px; font-weight: 700; white-space: nowrap; animation: chip-in .16s ease; }
@keyframes chip-in { from { opacity: 0; transform: translateX(8px); } }
</style>
