<script setup lang="ts">
/**
 * KeyshowStage — the transparent always-on-top overlay shown at the bottom of
 * the screen. Renders accepted physical key/mouse presses in one of three
 * switchable styles: capsule stream, particle trail, or a mini keyboard mirror.
 * Style and theme are shared with the main window through localStorage.
 */
import { onMounted, onUnmounted, ref } from "vue";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";

type KeyShowEvent = { kind: "key" | "mouse"; label: string; keyId: string; action: "down" | "up" };

const MOD_KEYS = new Set([
  "ctrl-left", "ctrl-right", "alt-left", "alt-right",
  "shift-left", "shift-right", "win-left", "win-right", "menu",
]);

type StyleMode = "capsule" | "particle" | "mirror" | "ring" | "firework" | "spring";
const mode = ref<StyleMode>((localStorage.getItem("keypulse-keyshow-style") as StyleMode) || "capsule");
const showHint = ref(true);
// The window is resized by the host (small/medium/large); content scales to match
// the medium baseline of 1080x190 so visuals stay crisp at every size.
const contentScale = ref(1);
const KEYSHOW_BASE_WIDTH = 1080;
// Drag-to-place mode: a grab handle appears at the top; dragging moves the
// overlay freely, locking (drag mode off) restores click-through.
const dragMode = ref(false);
const dragging = ref(false);
let dragOffsetX = 0;
let dragOffsetY = 0;
let dragRaf = 0;

function dragStart(event: PointerEvent) {
  if (!dragMode.value) return;
  dragging.value = true;
  dragOffsetX = event.screenX - window.screenX;
  dragOffsetY = event.screenY - window.screenY;
  (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
}

function dragMove(event: PointerEvent) {
  if (!dragging.value) return;
  if (dragRaf) cancelAnimationFrame(dragRaf);
  dragRaf = requestAnimationFrame(() => {
    const dpr = window.devicePixelRatio || 1;
    const x = Math.round((event.screenX - dragOffsetX) * dpr);
    const y = Math.round((event.screenY - dragOffsetY) * dpr);
    invoke("set_keyshow_custom_position", { x, y }).catch(() => undefined);
  });
}

function dragEnd() {
  dragging.value = false;
  localStorage.setItem("keypulse-keyshow-pos", "custom");
  localStorage.setItem("keypulse-keyshow-custom-x", String(window.screenX));
  localStorage.setItem("keypulse-keyshow-custom-y", String(window.screenY));
}

function applyContentScale() {
  const scale = window.innerWidth / KEYSHOW_BASE_WIDTH;
  contentScale.value = Math.min(Math.max(scale, 0.6), 1.8);
}

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

// extra effects: expanding rings, firework pops, springy key bounce
type Ring = { id: number; label: string };
const rings = ref<Ring[]>([]);
let ringSeq = 0;
type Spark = { angle: number; distance: number };
type Pop = { id: number; label: string; parts: Spark[] };
const pops = ref<Pop[]>([]);
let popSeq = 0;
const springs = ref<Ring[]>([]);
let springSeq = 0;

function dropAfter(millis: number, fn: () => void) {
  setTimeout(fn, millis);
}

function onRingEvent(event: KeyShowEvent) {
  if (event.action !== "down") return;
  const id = ++ringSeq;
  rings.value = [...rings.value.slice(-2), { id, label: event.label }];
  dropAfter(950, () => { rings.value = rings.value.filter((r) => r.id !== id); });
}

function onPopEvent(event: KeyShowEvent) {
  if (event.action !== "down") return;
  const id = ++popSeq;
  const parts: Spark[] = Array.from({ length: 12 }, (_, i) => ({
    angle: (i / 12) * Math.PI * 2 + Math.random() * 0.6,
    distance: 70 + Math.random() * 55,
  }));
  pops.value = [...pops.value.slice(-2), { id, label: event.label, parts }];
  dropAfter(850, () => { pops.value = pops.value.filter((pop) => pop.id !== id); });
}

function onSpringEvent(event: KeyShowEvent) {
  if (event.action !== "down") return;
  const id = ++springSeq;
  springs.value = [...springs.value.slice(-2), { id, label: event.label }];
  dropAfter(750, () => { springs.value = springs.value.filter((s) => s.id !== id); });
}

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

const MAX_CAPSULE_ROWS = 8;

function pushCapsule(segments: CapsuleSegment[], count: number) {
  // A combo with many modifiers folds to "Ctrl + Shift + … + key" so the row
  // never outgrows the overlay.
  let folded = segments;
  if (segments.length > 4) {
    folded = [...segments.slice(0, 2), { label: "…", mod: true }, segments[segments.length - 1]];
  }
  const cap: Capsule = { id: ++capsuleSeq, kind: "key", segments: folded, count, born: Date.now() };
  capsules.value = [...capsules.value, cap].slice(-MAX_CAPSULE_ROWS);
  refreshHideTimer();
  trimOverflowingCapsules();
}

function trimOverflowingCapsules() {
  requestAnimationFrame(() => {
    const stage = document.querySelector<HTMLElement>(".capsule-stage");
    if (!stage || capsules.value.length < 2) return;
    let guard = 0;
    while (stage.scrollWidth > stage.clientWidth + 2 && capsules.value.length > 1 && guard < MAX_CAPSULE_ROWS) {
      capsules.value = capsules.value.slice(1);
      guard += 1;
    }
  });
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
    trimOverflowingCapsules();
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
  onRingEvent(event);
  onPopEvent(event);
  onSpringEvent(event);
}

// ---------- mirror keyboard layout: full 104 keys (ANSI) ----------
type MirrorKey = { label: string; keyId: string; w?: number; fn?: boolean };
const K = (label: string, keyId: string, w?: number, fn?: boolean): MirrorKey => ({ label, keyId, w, fn });
const mirrorMain: MirrorKey[][] = [
  // row 0: escape + function keys
  [K("Esc", "escape"), ...Array.from({ length: 12 }, (_, i) => K(`F${i + 1}`, `f${i + 1}`, 1, true))],
  // row 1: backquote + digits + minus/equal/backspace
  [K("`", "backquote"), ...Array.from({ length: 10 }, (_, i) => K(String(i), String(i))),
    K("-", "minus"), K("=", "equal"), K("⌫", "backspace", 2)],
  // row 2: tab + QWERTYUIOP[]\
  [K("Tab", "tab", 1.5), ..."QWERTYUIOP".split("").map((l) => K(l, l.toLowerCase())),
    K("[", "bracket-left"), K("]", "bracket-right"), K("\\", "backslash", 1.5)].flat(),
  // row 3: caps + ASDFGHJKL;' + enter
  [K("Caps", "caps-lock", 1.8), "ASDFGHJKL".split("").map((l) => K(l, l.toLowerCase())),
    K(";", "semicolon"), K("'", "quote"), K("Enter", "enter", 2.2)].flat(),
  // row 4: shift + ZXCVBNM,./ + shift
  [K("Shift", "shift-left", 2.3), "ZXCVBNM".split("").map((l) => K(l, l.toLowerCase())),
    K(",", "comma"), K(".", "period"), K("/", "slash"), K("Shift", "shift-right", 2.8)].flat(),
  // row 5: ctrl win alt space alt menu ctrl
  [K("Ctrl", "ctrl-left", 1.5), K("Win", "win-left"), K("Alt", "alt-left", 1.3),
    K("Space", "space", 6.5), K("Alt", "alt-right", 1.3), K("Fn", "fn", 1.1, true),
    K("≣", "menu"), K("Ctrl", "ctrl-right", 1.5)],
];
// Right side of the standard 104 layout as coordinate grids over 6 rows that
// mirror the main rows: edit keys on rows 2-3 with the direction pad directly
// beneath them (rows 4-5), numeric keypad on rows 2-6 with true spans.
type MirrorCell = { id: string; label: string; row: number; col: number; rowspan?: number; colspan?: number };
const mirrorLeftKeys: MirrorCell[] = [
  { id: "print-screen", label: "PrtSc", row: 1, col: 1 },
  { id: "insert", label: "Ins", row: 2, col: 1 },
  { id: "scroll-lock", label: "ScrLk", row: 1, col: 2 },
  { id: "home", label: "Home", row: 2, col: 2 },
  { id: "pause", label: "Pause", row: 1, col: 3 },
  { id: "page-up", label: "PgUp", row: 2, col: 3 },
  { id: "delete", label: "Del", row: 3, col: 1 },
  { id: "end", label: "End", row: 3, col: 2 },
  { id: "page-down", label: "PgDn", row: 3, col: 3 },
  { id: "arrow-up", label: "↑", row: 5, col: 2, rowspan: 2 },
  { id: "arrow-left", label: "←", row: 6, col: 1 },
  { id: "arrow-down", label: "↓", row: 6, col: 2 },
  { id: "arrow-right", label: "→", row: 6, col: 3 },
];
const mirrorNumKeys: MirrorCell[] = [
  { id: "num-lock", label: "Num", row: 2, col: 1 },
  { id: "numpad-divide", label: "/", row: 2, col: 2 },
  { id: "numpad-multiply", label: "*", row: 2, col: 3 },
  { id: "numpad-subtract", label: "-", row: 2, col: 4 },
  { id: "numpad-7", label: "7", row: 3, col: 1 },
  { id: "numpad-8", label: "8", row: 3, col: 2 },
  { id: "numpad-9", label: "9", row: 3, col: 3 },
  { id: "numpad-add", label: "+", row: 3, col: 4, rowspan: 2 },
  { id: "numpad-4", label: "4", row: 4, col: 1 },
  { id: "numpad-5", label: "5", row: 4, col: 2 },
  { id: "numpad-6", label: "6", row: 4, col: 3 },
  { id: "numpad-1", label: "1", row: 5, col: 1 },
  { id: "numpad-2", label: "2", row: 5, col: 2 },
  { id: "numpad-3", label: "3", row: 5, col: 3 },
  { id: "numpad-enter", label: "↵", row: 5, col: 4, rowspan: 2 },
  { id: "numpad-0", label: "0", row: 6, col: 1, colspan: 2 },
  { id: "numpad-decimal", label: ".", row: 6, col: 3 },
];
function sideArea(spec: MirrorCell) {
  return spec.row + " / " + spec.col + " / span " + (spec.rowspan || 1) + " / span " + (spec.colspan || 1);
}
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
let stopListenerDrag: UnlistenFn | undefined;
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
  stopListenerDrag = await listen<boolean>("keyshow-dragmode", (event) => {
    dragMode.value = event.payload;
    if (!event.payload) dragging.value = false;
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
  window.addEventListener("resize", applyContentScale);
  applyContentScale();
  pollTimer = setInterval(pollSharedPrefs, 300);
});

let lastStyle = localStorage.getItem("keypulse-keyshow-style") || "capsule";
let lastTheme = localStorage.getItem("keypulse-theme") || "neon";
let pollTimer: ReturnType<typeof setInterval> | undefined;

// Storage events are not reliably delivered between WebView2 windows, so also
// poll the shared localStorage values and apply changes when they drift.
function pollSharedPrefs() {
  expireStaleLitKeys();
  applyContentScale();
  const drag = localStorage.getItem("keypulse-keyshow-drag") === "1";
  if (drag !== dragMode.value) {
    dragMode.value = drag;
    if (!drag) dragging.value = false;
  }
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
  stopListenerDrag?.();
  stopStorage?.();
  window.removeEventListener("resize", applyContentScale);
  document.documentElement.classList.remove("keyshow-window");
  if (hideTimer) clearTimeout(hideTimer);
  if (modCommitTimer) clearTimeout(modCommitTimer);
});
</script>

<template>
  <div class="keyshow-root" :data-caps="capsules.length" :data-bursts="bursts.length" :data-mode="mode" :data-scale="contentScale" :data-drag="dragMode">
    <div v-if="dragMode" class="ks-drag-handle" :class="{ active: dragging }" title="拖动到想要的位置，完成后在设置里锁定"
      @pointerdown="dragStart" @pointermove="dragMove" @pointerup="dragEnd" @pointercancel="dragEnd">⠿ 拖动到喜欢的位置 — 松手即停</div>
    <p v-if="showHint" class="keyshow-hint">按键可视化已开启 — 按下的键会出现在这里 · 可在主界面切换风格</p>
    <div class="keyshow-content" :style="{ transform: `scale(${contentScale})` }">

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

    <!-- 波纹扩散 -->
    <div v-if="mode === 'ring'" class="fx-stage" aria-hidden="true">
      <div v-for="ring in rings" :key="ring.id" class="fx-ring"><span>{{ ring.label }}</span></div>
    </div>

    <!-- 烟花爆裂 -->
    <div v-if="mode === 'firework'" class="fx-stage" aria-hidden="true">
      <div v-for="pop in pops" :key="pop.id" class="fx-pop">
        <span class="fx-pop-label">{{ pop.label }}</span>
        <i v-for="(part, index) in pop.parts" :key="index" class="fx-spark" :style="{ '--a': part.angle + 'rad', '--d': part.distance + 'px', '--c': index % 3 }"></i>
      </div>
    </div>

    <!-- 弹性蹦跳 -->
    <div v-if="mode === 'spring'" class="fx-stage" aria-hidden="true">
      <div v-for="spring in springs" :key="spring.id" class="fx-spring"><span>{{ spring.label }}</span></div>
    </div>

    <!-- 迷你键盘镜像（104 全键位） -->
    <div v-if="mode === 'mirror'" class="mirror-stage" aria-hidden="true">
      <div class="mirror-board">
        <div class="mirror-main">
          <div v-for="(row, rowIndex) in mirrorMain" :key="rowIndex" class="mirror-row">
            <div v-for="key in row" :key="key.keyId" class="mirror-key" :class="{ lit: isKeyLit(key.keyId), wide: key.w, fn: key.fn }">{{ key.label }}</div>
          </div>
        </div>
        <div class="mirror-side">
          <div class="mirror-right-block">
            <div v-for="key in mirrorLeftKeys" :key="key.id" class="mirror-key side" :class="{ lit: isKeyLit(key.id) }" :style="{ gridArea: sideArea(key) }">{{ key.label }}</div>
          </div>
          <div class="mirror-right-block num">
            <div v-for="key in mirrorNumKeys" :key="key.id" class="mirror-key side" :class="{ lit: isKeyLit(key.id) }" :style="{ gridArea: sideArea(key) }">{{ key.label }}</div>
          </div>
        </div>
      <div class="mirror-chips">
        <span v-for="chip in recentChips" :key="chip.id" class="mirror-chip">{{ chip.label }}</span>
      </div>
    </div>
    </div>
  </div>
  </div>
</template>

<style scoped>
.keyshow-root { position: fixed; inset: 0; display: flex; align-items: end; justify-content: center; overflow: hidden; pointer-events: none; user-select: none; }
.keyshow-content { flex: 0 0 auto; width: 1080px; height: 190px; display: flex; flex-direction: column; align-items: center; justify-content: end; transform-origin: center bottom; }
.keyshow-hint { position: absolute; top: 6px; left: 50%; transform: translateX(-50%); padding: 6px 14px; border: 1px solid rgba(148,163,184,.2); border-radius: 999px; color: rgba(148,163,184,.9); background: rgba(4,9,24,.55); font-size: 11px; white-space: nowrap; animation: hint-in .3s ease; }
@keyframes hint-in { from { opacity: 0; transform: translateX(-50%) translateY(6px); } }
.ks-drag-handle { position: absolute; z-index: 5; top: 6px; left: 50%; transform: translateX(-50%); padding: 7px 18px; pointer-events: auto; border: 1px solid rgba(var(--cyan-rgb), .5); border-radius: 999px; color: #eaf6ff; background: rgba(var(--pop-rgb), .92); box-shadow: 0 8px 22px rgba(0,0,0,.35); font-size: 12px; font-weight: 700; cursor: grab; user-select: none; white-space: nowrap; letter-spacing: .02em; }
.ks-drag-handle:hover { border-color: rgba(var(--cyan-rgb), .9); box-shadow: 0 8px 26px rgba(var(--cyan-rgb), .3); }
.ks-drag-handle.active { cursor: grabbing; transform: translateX(-50%) scale(1.03); }

/* ---------- capsule stream ---------- */
.capsule-stage { display: flex; gap: 10px; align-items: center; justify-content: center; padding-bottom: 14px; height: 90px; max-width: 100%; overflow: hidden; }
.cap-row { max-width: 100%; }
.cap { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.particle-stage { position: relative; width: 1080px; height: 150px; }
.mirror-stage { display: flex; flex-direction: column; align-items: center; gap: 8px; padding-bottom: 10px; }
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
.burst { position: absolute; left: 50%; bottom: 30px; display: flex; align-items: center; justify-content: center; animation: burst-rise .95s ease-out forwards; }
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

/* ---------- extra effects ---------- */
.fx-stage { position: relative; width: 1080px; height: 150px; }
.fx-ring { position: absolute; left: 50%; bottom: 40px; width: 90px; height: 90px; margin-left: -45px; animation: ring-out .95s ease-out forwards; }
.fx-ring span { position: absolute; inset: 0; display: grid; place-items: center; color: #fff; font-weight: 900; font-size: 20px; text-shadow: 0 0 18px rgba(var(--cyan-rgb), 1); }
.fx-ring::before, .fx-ring::after { content: ""; position: absolute; inset: 0; border-radius: 50%; border: 2px solid rgba(var(--cyan-rgb), .8); animation: ring-wave .95s ease-out forwards; }
.fx-ring::after { animation-delay: .18s; }
@keyframes ring-wave { 0% { transform: scale(.25); opacity: 1; } 100% { transform: scale(2.4); opacity: 0; } }
@keyframes ring-out { 0% { transform: scale(.6); opacity: 0; } 18% { opacity: 1; transform: scale(1); } 100% { transform: scale(1.25); opacity: 0; } }
.fx-pop { position: absolute; left: 50%; bottom: 36px; animation: pop-rise .8s ease-out forwards; }
.fx-pop-label { display: block; margin-bottom: 4px; text-align: center; color: var(--text-main); font-weight: 900; font-size: 22px; text-shadow: 0 0 16px rgba(var(--amber-rgb), .9); }
.fx-spark { position: absolute; left: 50%; top: 14px; width: 6px; height: 6px; border-radius: 50%; background: var(--acc-pink); box-shadow: 0 0 8px var(--acc-pink); transform: translate(-50%, -50%) rotate(var(--a)) translateX(var(--d)) scale(1); animation: spark-fade .8s ease-out forwards; }
.fx-spark:nth-child(3n) { background: var(--acc-amber); box-shadow: 0 0 8px var(--acc-amber); }
.fx-spark:nth-child(3n+1) { background: var(--acc-cyan); box-shadow: 0 0 8px var(--acc-cyan); }
@keyframes spark-fade { 0% { opacity: 1; } 100% { opacity: 0; transform: translate(-50%, -50%) rotate(var(--a)) translateX(calc(var(--d) * 1.5)) scale(.2); } }
@keyframes pop-rise { 0% { transform: translate(-50%, 10px) scale(.5); opacity: 0; } 20% { opacity: 1; transform: translate(-50%, -10px) scale(1.05); } 100% { transform: translate(-50%, -46px) scale(.94); opacity: 0; } }
.fx-spring { position: absolute; left: 50%; bottom: 34px; display: grid; place-items: center; min-width: 64px; height: 44px; padding: 0 12px; border-radius: 12px; color: #fff; font-weight: 900; font-size: 20px; background: linear-gradient(160deg, rgba(var(--violet-rgb), .85), rgba(var(--cyan-rgb), .75)); box-shadow: 0 8px 24px rgba(var(--cyan-rgb), .35); animation: spring-bounce .75s cubic-bezier(.2, 1.6, .4, 1) forwards; }
@keyframes spring-bounce { 0% { transform: translate(-50%, 0) scaleY(.6); opacity: 0; } 16% { opacity: 1; transform: translate(-50%, -78px) scaleY(1.05); } 34% { transform: translate(-50%, 0) scaleY(.94); } 52% { transform: translate(-50%, -40px) scaleY(1); } 70% { transform: translate(-50%, 0) scaleY(.97); } 100% { transform: translate(-50%, -8px) scaleY(.9); opacity: 0; } }

/* ---------- mirror keyboard ---------- */
.mirror-board { display: flex; gap: 7px; padding: 8px 9px; border-radius: 12px; background: rgba(4, 9, 24, .5); box-shadow: 0 10px 26px rgba(0,0,0,.3), inset 0 0 0 1px rgba(148,163,184,.14); }
.mirror-main { display: flex; flex-direction: column; gap: 4px; }
.mirror-row { display: flex; gap: 3px; justify-content: center; }
.mirror-key { display: grid; place-items: center; width: 25px; height: 19px; border-radius: 4px; color: rgba(226, 232, 240, .5); background: rgba(30, 41, 59, .6); font-size: 7.5px; font-weight: 700; box-shadow: inset 0 0 0 1px rgba(148,163,184,.1); transition: color .08s ease, background .1s ease, box-shadow .1s ease, transform .07s ease; }
.mirror-key.wide { flex: 1 1 auto; }
.mirror-key.fn { font-size: 6.5px; }
.mirror-right-block .mirror-key { width: auto; height: auto; }
.mirror-key.lit { color: #fff; background: linear-gradient(180deg, rgba(var(--cyan-rgb), .95), rgba(var(--violet-rgb), .8)); box-shadow: 0 0 16px rgba(var(--cyan-rgb), .95), inset 0 0 0 1px rgba(255, 255, 255, .4); animation: mirror-press .16s ease-out; }
@keyframes mirror-press {
  0% { transform: translateY(1.5px) scale(.92); filter: brightness(1.9); }
  45% { transform: translateY(0) scale(1.07); filter: brightness(1.4); }
  100% { transform: translateY(0) scale(1); filter: brightness(1); }
}
.mirror-side { display: flex; gap: 6px; align-items: start; border-left: 1px solid rgba(148,163,184,.14); padding-left: 6px; }
.mirror-right-block { display: grid; grid-template-rows: repeat(6, 19px); grid-template-columns: repeat(3, 24px); gap: 4px; }
.mirror-right-block.num { grid-template-columns: repeat(4, 25px); }
.mirror-chips { display: flex; gap: 4px; max-width: 90%; overflow: hidden; }
.mirror-chip { padding: 2px 7px; border-radius: 5px; color: #dbe4f3; background: rgba(15, 23, 42, .66); font-size: 10px; font-weight: 700; white-space: nowrap; animation: chip-in .16s ease; }
@keyframes chip-in { from { opacity: 0; transform: translateX(8px); } }
</style>
