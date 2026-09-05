<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { WebviewWindow } from "@tauri-apps/api/webviewWindow";
import KeyshowStage from "./KeyshowStage.vue";
import MiniStat from "./MiniStat.vue";
import { configureSound, loadCustomSound, playKeySound, playMetronomeTick, type SoundVoice } from "./sound";
import DailyCard from "./DailyCard.vue";
import PkDuel from "./PkDuel.vue";
import CloudAccount from "./CloudAccount.vue";

// ============================================================
// KeyPulse main dashboard window.
//
// Script sections (keep functions small & single-purpose):
//   1. window detection & types         4. keyshow/mini overlay state
//   2. date-range state + helpers       5. sound / achievements / count-up
//   3. keyboard template + metrics      6. footprint card
//   4. live dashboard listeners         7. PK (see PkDuel.vue component)
//   5. theme system (CSS variables)     8. settings modal state
// Template sections mirror the settings modal groups; heavy UI
// lives in components: KeyshowStage / MiniStat / DailyCard / PkDuel.
// ============================================================


let isKeyshowWindow = false;
let isMiniWindow = false;
try {
  const label = getCurrentWindow().label;
  isKeyshowWindow = label === "keys-overlay";
  isMiniWindow = label === "keys-mini";
} catch {
  // Plain-browser preview (`npm run dev`) has no Tauri window.
}

type KeyItem = { id: string; label: string; count: number; width?: number; muted?: boolean; blank?: boolean };
type MouseStat = { label: string; value: number; color: string };
type DashboardData = {
  date: string;
  totalKeyPresses: number;
  totalMouseActions: number;
  keys: Array<{ keyId: string; label: string; count: number }>;
  mouse: Array<{ actionId: string; label: string; count: number }>;
  activity: Array<{ hour: number; count: number }>;
};

const ranges = ["今天", "本周", "本月"];
const rangeKeys: Record<string, string> = { 今天: "today", 本周: "week", 本月: "month" };
const activeRange = ref("今天");
const showDatePicker = ref(false);
const customRangeError = ref("");

function formatDateInput(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function dateWithOffset(days: number) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return formatDateInput(date);
}

const maxSelectableDate = formatDateInput(new Date());
const customStart = ref(dateWithOffset(-6));
const customEnd = ref(maxSelectableDate);
const draftStart = ref(customStart.value);
const draftEnd = ref(customEnd.value);
const activeRangeLabel = computed(() => activeRange.value === "自定义" ? `${customStart.value} → ${customEnd.value}` : activeRange.value);
const rangeHeading = computed(() => activeRange.value === "自定义" ? "选定范围" : activeRange.value);
const recording = ref(true);
const inputAvailable = ref(false);
const showPrivacyPanel = ref(false);
const privacyDialog = ref<HTMLElement | null>(null);
watch(showPrivacyPanel, async (visible) => {
  if (visible) {
    await nextTick();
    privacyDialog.value?.focus();
  }
});

type ThemeOption = { id: string; name: string; dots: string[] };
const themeOptions: ThemeOption[] = [
  { id: "neon", name: "霓虹之夜", dots: ["#ff5c7a", "#34d9ff", "#a78bfa"] },
  { id: "ocean", name: "深海回声", dots: ["#2dd4bf", "#38bdf8", "#818cf8"] },
  { id: "sunset", name: "落日熔金", dots: ["#fb923c", "#f472b6", "#fbbf24"] },
  { id: "aurora", name: "极光森林", dots: ["#34d399", "#22d3ee", "#a3e635"] },
  { id: "graphite", name: "苹果石墨", dots: ["#0a84ff", "#ff375f", "#30d158"] },
  { id: "starlight", name: "星光浅色", dots: ["#007aff", "#ff9f0a", "#34c759"] },
  { id: "neon-drive", name: "霓虹夜驰", dots: ["#ff2fd4", "#05f4ff", "#7b2cff"] },
  { id: "miami", name: "迈阿密海岸", dots: ["#ff5e9f", "#3ae7ff", "#09fbd3"] },
  { id: "sunset-horizon", name: "落日地平线", dots: ["#ff006e", "#9d4edd", "#ffd670"] },
  { id: "laser-horizon", name: "镭射地平线", dots: ["#ff3f8e", "#ff8a3d", "#7b2cff"] },
  { id: "cyber-alley", name: "赛博雨巷", dots: ["#fe53bb", "#08f7fe", "#f5d300"] },
  { id: "volt", name: "荧光青柠", dots: ["#ccff00", "#00ff9d", "#00e5ff"] },
  { id: "latte", name: "拿铁暖白", dots: ["#b98a5e", "#7f97a5", "#a590a8"] },
  { id: "sage", name: "鼠尾草绿", dots: ["#7ba889", "#7ea3b0", "#c7a25f"] },
  { id: "matcha", name: "抹茶和纸", dots: ["#8a9a5b", "#7e9a8b", "#d0a259"] },
  { id: "dusk", name: "暮云蓝", dots: ["#8fa8c9", "#7fb2c4", "#a191c4"] },
  { id: "cocoa", name: "可可陶土", dots: ["#c98d6d", "#a89a86", "#d9b37a"] },
  { id: "mist-blue", name: "雾蓝清晨", dots: ["#6d9bc3", "#6fa3b8", "#c2a878"] },
  { id: "indigo-night", name: "靛夜静谧", dots: ["#7d9ecb", "#79a8c0", "#9a94c9"] },
];
const themeId = ref<string>(localStorage.getItem("keypulse-theme") || "neon");
const showThemePicker = ref(false);
let heatStops: string[] = [];

function refreshHeatHues() {
  const css = getComputedStyle(document.documentElement);
  heatStops = [1, 2, 3, 4, 5].map((index) => css.getPropertyValue(`--heat-${index}`).trim()).filter(Boolean);
  if (heatStops.length < 2) heatStops = ["#276eaa", "#34d9ff", "#2de2a6", "#ffd166", "#ff5c7a"];
}

function heatStopRgb(hex: string) {
  const value = parseInt(hex.slice(1), 16);
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

function applyTheme(id: string) {
  themeId.value = id;
  document.documentElement.dataset.theme = id;
  localStorage.setItem("keypulse-theme", id);
  refreshHeatHues();
  showThemePicker.value = false;
}

const keyshowEnabled = ref(false);
const showSettingsPanel = ref(false);
const keyshowOpacity = ref<number>(Number(localStorage.getItem("keypulse-keyshow-opacity")) || 1);
const keyshowDrag = ref(localStorage.getItem("keypulse-keyshow-drag") === "1");
const miniEnabled = ref(false);
let stopMiniListener: UnlistenFn | undefined;

async function refreshMiniState() {
  try {
    const mini = await WebviewWindow.getByLabel("keys-mini");
    miniEnabled.value = mini ? await mini.isVisible() : false;
  } catch {
    // Older runtime without the mini window.
  }
}

async function toggleMini() {
  try {
    miniEnabled.value = await invoke<boolean>("toggle_mini");
  } catch (error) {
    console.info("Could not toggle mini stats window.", error);
  }
}

// ---------- keyshow / mini overlay state ----------
// (toggle, layout prefs, drag mode, opacity; synced to the overlay windows
// through localStorage polling + Rust commands; see KeyshowStage.vue)

// ---------- fun: sound, achievements, count-up ----------
const SOUND_IDS: SoundVoice[] = ["off", "click", "typewriter", "bubble", "blub", "bell", "mahjong", "arcade", "laser"];
const savedVoice = localStorage.getItem("keypulse-sound") as SoundVoice | null;
const soundVoice = ref<SoundVoice>(savedVoice && SOUND_IDS.includes(savedVoice) ? savedVoice : "off");
const soundVolume = ref(Number(localStorage.getItem("keypulse-sound-volume")) || 60);
const achievementsOn = ref(localStorage.getItem("keypulse-achievements") !== "0");
const toastMsg = ref("");
const footprintAuto = ref(localStorage.getItem("keypulse-footprint-auto") !== "0");
const showFootprintCard = ref(false);
const showPkDuel = ref(false);
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

function promptRename(profile: PlayerProfile) {
  const next = window.prompt("给档案一个新名字", profile.name);
  if (next && next.trim()) renameProfile(profile.id, next.trim());
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
}
const footprintSnapshot = ref<DashboardData | null>(null);

function toggleFootprintAuto(on: boolean) {
  footprintAuto.value = on;
  localStorage.setItem("keypulse-footprint-auto", on ? "1" : "0");
}

async function openFootprintCard() {
  try {
    footprintSnapshot.value = await fetchActiveDashboard();
    showFootprintCard.value = true;
  } catch (error) {
    console.info("Could not build footprint card.", error);
  }
}

function markFootprintSeen() {
  showFootprintCard.value = false;
  localStorage.setItem("keypulse-footprint-seen", new Date().toISOString().slice(0, 10));
}

function autoShowFootprintIfNew() {
  if (!footprintAuto.value || demoMode.value) return;
  const today = new Date().toISOString().slice(0, 10);
  const seen = localStorage.getItem("keypulse-footprint-seen") || "";
  if (seen === today) return;
  if (liveDashboard.value && liveDashboard.value.totalKeyPresses > 0) {
    openFootprintCard();
  }
}
let toastTimer: ReturnType<typeof setTimeout> | undefined;

function showToast(message: string) {
  toastMsg.value = message;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toastMsg.value = ""; }, 4200);
}

function setSoundVoice(id: SoundVoice) {
  soundVoice.value = id;
  localStorage.setItem("keypulse-sound", id);
  configureSound(id, soundVolume.value / 100);
  if (id !== "off") playKeySound(true);
}

function setSoundVolume(percent: number) {
  const v = Math.min(Math.max(percent, 0), 100);
  soundVolume.value = v;
  localStorage.setItem("keypulse-sound-volume", String(v));
  configureSound(soundVoice.value, v / 100);
}

function toggleAchievements(on: boolean) {
  achievementsOn.value = on;
  localStorage.setItem("keypulse-achievements", on ? "1" : "0");
}

// ---------- custom key sound ----------
const customSounds = ref<string[]>([]);
const customSoundName = ref("");
const customSoundDir = ref("");

async function refreshCustomSounds() {
  try {
    customSoundDir.value = await invoke<string>("custom_sounds_dir");
    customSounds.value = await invoke<string[]>("list_custom_sounds");
  } catch {
    // older runtime
  }
}

async function applyCustomSound(fileName: string) {
  if (!fileName) return;
  try {
    const dataUrl = await invoke<string>("read_custom_sound_base64", { fileName });
    const loaded = await loadCustomSound(dataUrl);
    if (loaded) {
      setSoundVoice("custom");
      customSoundName.value = fileName;
      localStorage.setItem("keypulse-sound", "custom");
      localStorage.setItem("keypulse-custom-sound", fileName);
      playKeySound(true);
    } else {
      console.info("Could not decode audio file.");
    }
  } catch (error) {
    console.info(String(error));
  }
}

// ---------- metronome rhythm trainer ----------
const metronomeOn = ref(localStorage.getItem("keypulse-metronome") === "1");
const bpm = ref(Number(localStorage.getItem("keypulse-bpm")) || 90);
const beatCount = ref(0);
let metronomeTimer: ReturnType<typeof setInterval> | undefined;

function stopMetronome() {
  if (metronomeTimer) clearInterval(metronomeTimer);
  metronomeTimer = undefined;
  metronomeOn.value = false;
  localStorage.setItem("keypulse-metronome", "0");
}

function startMetronome() {
  metronomeOn.value = true;
  localStorage.setItem("keypulse-metronome", "1");
  if (metronomeTimer) clearInterval(metronomeTimer);
  beatCount.value = 0;
  const intervalMs = Math.max(200, Math.round(60000 / bpm.value));
  const tick = () => {
    beatCount.value += 1;
    playMetronomeTick(beatCount.value % 4 === 1);
  };
  tick();
  metronomeTimer = setInterval(tick, intervalMs);
}

function changeBpm(next: number) {
  bpm.value = Math.min(Math.max(next, 40), 220);
  localStorage.setItem("keypulse-bpm", String(bpm.value));
  if (metronomeOn.value) startMetronome();
}

function toggleMetronome(on: boolean) {
  if (on) startMetronome();
  else stopMetronome();
}

const KEY_MILESTONES: Array<[number, string]> = [
  [50000, "五万键 · 键盘马拉松选手！🏅"],
  [10000, "一万键 · 今日打字如飞 ✨"],
  [5000, "五千键 · 手感火热 🔥"],
  [1000, "一千键 · 今日开始发力 💪"],
];

function checkAchievements(total: number) {
  if (!achievementsOn.value) return;
  const today = new Date().toISOString().slice(0, 10);
  let done: string[] = [];
  try { done = JSON.parse(localStorage.getItem("keypulse-achievements-done") || "[]"); } catch { done = []; }
  for (const [threshold, message] of KEY_MILESTONES) {
    const key = `${today}:${threshold}`;
    if (total >= threshold && !done.includes(key)) {
      done.push(key);
      showToast(message);
    }
  }
  if (done.length) localStorage.setItem("keypulse-achievements-done", JSON.stringify(done.slice(-40)));
}

const shownKeys = ref(0);
const shownMouse = ref(0);
// One interval per headline number: sharing a single timer let the second
// card's tween cancel the first one's (total key count stayed at 0 forever).
const keysTimer: { id?: ReturnType<typeof setInterval> } = {};
const mouseTimer: { id?: ReturnType<typeof setInterval> } = {};
function tweenTo(
  target: number,
  setter: (v: number) => void,
  current: () => number,
  holder: { id?: ReturnType<typeof setInterval> },
) {
  if (holder.id) clearInterval(holder.id);
  const from = current();
  const diff = target - from;
  if (Math.abs(diff) < 2) { setter(target); return; }
  const started = Date.now();
  const duration = 360;
  holder.id = setInterval(() => {
    const progress = Math.min((Date.now() - started) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    setter(Math.round(from + diff * eased));
    if (progress >= 1 && holder.id) { clearInterval(holder.id); holder.id = undefined; }
  }, 24);
}
// ---------- cloud daily stats sync (leaderboard data) ----------
let cloudSyncTimer: ReturnType<typeof setInterval> | undefined;

async function cloudSyncToday() {
  const server = localStorage.getItem("kp-cloud-server");
  const token = localStorage.getItem("kp-cloud-token");
  if (!server || !token || demoMode.value) return;
  const today = new Date().toISOString().slice(0, 10);
  try {
    const dashboard = await fetchActiveDashboard();
    await fetch(server + "/api/stats", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        token,
        date: today,
        keys: dashboard.totalKeyPresses,
        mouse: dashboard.totalMouseActions,
      }),
    });
  } catch {
    // offline or server down; try again next tick
  }
}

let stopKeySoundListener: UnlistenFn | undefined;
async function wireSoundFx() {
  configureSound(soundVoice.value, soundVolume.value / 100);
  try {
    stopKeySoundListener = await listen<{ kind: string; label: string; keyId: string; action: string }>("keyshow-event", (event) => {
      const payload = event.payload;
      if (payload.kind !== "key" || payload.action !== "down") return;
      const heavy = /^(space|enter|backspace|tab)$/.test(payload.keyId);
      playKeySound(heavy);
    });
  } catch {
    // plain browser preview has no runtime events
  }
}

const dataLocation = ref("appdata");
const autostartOn = ref(false);
const startBehavior = ref("normal");
const closeBehavior = ref("tray");

async function refreshBehavior() {
  try {
    autostartOn.value = await invoke<boolean>("get_autostart");
    const [start, close] = await invoke<[string, string]>("get_app_behavior");
    startBehavior.value = start;
    closeBehavior.value = close;
  } catch {
    // older runtime
  }
}

async function toggleAutostart(on: boolean) {
  autostartOn.value = on;
  try {
    await invoke("set_autostart", { enabled: on });
  } catch (error) {
    autostartOn.value = !on;
    console.info("Could not change autostart.", error);
  }
}

async function changeBehavior(kind: "start" | "close", value: string) {
  if (kind === "start") startBehavior.value = value;
  else closeBehavior.value = value;
  try {
    await invoke("set_app_behavior", { start: startBehavior.value, close: closeBehavior.value });
  } catch (error) {
    console.info("Could not change behavior.", error);
  }
}
const dataPath = ref("");
const dataNotice = ref("");

async function refreshDataInfo() {
  try {
    const info = await invoke<string>("get_data_location");
    const [kind, path] = info.split("|");
    dataLocation.value = kind;
    dataPath.value = path;
  } catch {
    // Older runtime.
  }
}

async function migrateData(kind: string) {
  dataLocation.value = kind;
  try {
    dataNotice.value = await invoke<string>("set_data_location", { kind });
  } catch (error) {
    dataNotice.value = String(error);
  }
}
const keyshowStyle = ref<string>(localStorage.getItem("keypulse-keyshow-style") || "capsule");
const keyshowOptions = [
  { id: "capsule", name: "节奏胶囊流", icon: "⬚", desc: "组合合并 · 连打 ×N" },
  { id: "particle", name: "能量粒子", icon: "✦", desc: "上飘拖尾 · 越按越亮" },
  { id: "ring", name: "波纹扩散", icon: "◎", desc: "同心圆涟漪 + 键名" },
  { id: "firework", name: "烟花爆裂", icon: "✺", desc: "彩色火花四溅" },
  { id: "spring", name: "弹性蹦跳", icon: "⬢", desc: "键块落地回弹" },
  { id: "mirror", name: "迷你键盘", icon: "⌨", desc: "实时点亮 + 记录条" },
];
let stopKeyshowChangedListener: UnlistenFn | undefined;

async function refreshKeyshowState() {
  try {
    const overlay = await WebviewWindow.getByLabel("keys-overlay");
    keyshowEnabled.value = overlay ? await overlay.isVisible() : false;
  } catch {
    // Older runtime without the overlay window, or browser preview.
  }
}

async function toggleKeyshow() {
  try {
    keyshowEnabled.value = await invoke<boolean>("toggle_keyshow");
  } catch (error) {
    console.info("Could not toggle keyshow overlay.", error);
  }
}

function openSettings() {
  keyshowPosition.value = localStorage.getItem("keypulse-keyshow-pos") || "bottom-center";
  keyshowSize.value = localStorage.getItem("keypulse-keyshow-size") || "medium";
  keyshowStyle.value = localStorage.getItem("keypulse-keyshow-style") || "capsule";
  keyshowOpacity.value = Number(localStorage.getItem("keypulse-keyshow-opacity")) || 1;
  keyshowDrag.value = localStorage.getItem("keypulse-keyshow-drag") === "1";
  refreshDataInfo();
  refreshBehavior();
  refreshProfiles();
  refreshCustomSounds();
  showSettingsPanel.value = true;
}

async function changeKeyshowOpacity(percent: number) {
  const value = Math.min(Math.max(percent / 100, 0.15), 1);
  keyshowOpacity.value = value;
  localStorage.setItem("keypulse-keyshow-opacity", String(value));
  try {
    await invoke("set_keyshow_opacity", { opacity: value });
  } catch (error) {
    console.info("Could not change keyshow opacity.", error);
  }
}

async function toggleKeyshowDrag(enabled: boolean) {
  keyshowDrag.value = enabled;
  localStorage.setItem("keypulse-keyshow-drag", enabled ? "1" : "0");
  try {
    await invoke("set_keyshow_drag_mode", { enabled });
    // Locking keeps the current placement; preset buttons restore alignment.
    if (!enabled && keyshowPosition.value !== "custom") {
      await invoke("set_keyshow_position", { position: keyshowPosition.value });
    }
  } catch (error) {
    console.info("Could not change keyshow drag mode.", error);
  }
}

function pickKeyshowStyle(id: string) {
  keyshowStyle.value = id;
  localStorage.setItem("keypulse-keyshow-style", id);
}

const keyshowPosition = ref<string>(localStorage.getItem("keypulse-keyshow-pos") || "bottom-center");
const keyshowSize = ref<string>(localStorage.getItem("keypulse-keyshow-size") || "medium");
const keyshowPositions = [
  { id: "top-left", name: "左上", dot: { left: "22%", top: "22%" } },
  { id: "top-center", name: "顶部中央", dot: { left: "50%", top: "22%" } },
  { id: "top-right", name: "右上", dot: { left: "78%", top: "22%" } },
  { id: "bottom-left", name: "左下", dot: { left: "22%", top: "78%" } },
  { id: "bottom-center", name: "底部中央", dot: { left: "50%", top: "78%" } },
  { id: "bottom-right", name: "右下", dot: { left: "78%", top: "78%" } },
];
const keyshowSizeOptions = [
  { id: "small", name: "小" },
  { id: "medium", name: "中" },
  { id: "large", name: "大" },
];

async function changeKeyshowPosition(id: string) {
  keyshowPosition.value = id;
  localStorage.setItem("keypulse-keyshow-pos", id);
  try {
    await invoke("set_keyshow_position", { position: id });
  } catch (error) {
    console.info("Could not move keyshow overlay.", error);
  }
}

async function changeKeyshowSize(id: string) {
  keyshowSize.value = id;
  localStorage.setItem("keypulse-keyshow-size", id);
  try {
    await invoke("set_keyshow_size", { size: id });
  } catch (error) {
    console.info("Could not resize keyshow overlay.", error);
  }
}

function closePopoversOnOutsideClick(event: MouseEvent) {
  const target = event.target as HTMLElement;
  if (showThemePicker.value && !target.closest(".theme-control")) showThemePicker.value = false;
  if (showDatePicker.value && !target.closest(".range-control")) showDatePicker.value = false;
  if (showSettingsPanel.value && !target.closest(".settings-control") && !target.closest(".settings-button")) showSettingsPanel.value = false;
}
const liveDashboard = ref<DashboardData | null>(null);
const demoMode = ref(true);
let stopStatsListener: UnlistenFn | undefined;
let stopRecordingListener: UnlistenFn | undefined;

const keyboardRows: KeyItem[][] = [
  [
    ["Esc", 122], ["", 0, 0.55, "gap"], ["F1", 84], ["F2", 96], ["F3", 44], ["F4", 58], ["", 0, 0.45, "gap"],
    ["F5", 278], ["F6", 65], ["F7", 72], ["F8", 51], ["", 0, 0.45, "gap"],
    ["F9", 40], ["F10", 32], ["F11", 29], ["F12", 20],
  ].map(([label, count, width, kind]) => ({
    id: kind === "gap" ? `gap-${count}-${width}` : String(label),
    label: String(label),
    count: Number(count),
    width: width ? Number(width) : undefined,
    muted: kind === "gap",
    blank: kind === "gap",
  })),
  [
    ["~", 58], ["1", 486], ["2", 348], ["3", 198], ["4", 176], ["5", 262], ["6", 213], ["7", 219], ["8", 320], ["9", 298], ["0", 443], ["-", 92], ["=", 67], ["⌫", 427, 2],
  ].map(([label, count, width]) => ({ id: String(label), label: String(label), count: Number(count), width: Number(width) || undefined })),
  [
    ["Tab", 352, 1.5], ["Q", 564], ["W", 1110], ["E", 2350], ["R", 1568], ["T", 1326], ["Y", 622], ["U", 784], ["I", 1890], ["O", 1736], ["P", 1058], ["[", 120], ["]", 148], ["\\", 82, 1.5],
  ].map(([label, count, width]) => ({ id: String(label), label: String(label), count: Number(count), width: Number(width) || undefined })),
  [
    ["Caps", 164, 1.75], ["A", 1480], ["S", 1228], ["D", 962], ["F", 744], ["G", 502], ["H", 558], ["J", 94], ["K", 274], ["L", 988], [";", 201], ["'", 138], ["Enter", 692, 2.25],
  ].map(([label, count, width]) => ({ id: String(label), label: String(label), count: Number(count), width: Number(width) || undefined })),
  [
    ["Shift", 602, 2.25], ["Z", 230], ["X", 298], ["C", 680], ["V", 514], ["B", 388], ["N", 702], ["M", 1134], [",", 372], [".", 440], ["/", 182], ["Shift", 360, 2.75],
  ].map(([label, count, width], index) => ({ id: `${label}-${index}`, label: String(label), count: Number(count), width: Number(width) || undefined })),
  [
    ["Ctrl", 812, 1.5], ["Alt", 234, 1.5], ["Space", 8420, 6.5], ["Alt", 144, 1.5], ["Win", 96], ["Menu", 18], ["Ctrl", 314, 1.5],
  ].map(([label, count, width], index) => ({ id: `${label}-${index}`, label: String(label), count: Number(count), width: Number(width) || undefined, muted: label === "Fn" || label === "Menu" })),
];

// Right side of the real 104 layout as coordinate grids over 6 rows that
// mirror the main keyboard rows: edit keys on rows 2-3 with the direction pad
// right beneath them (rows 4-5, under the PrtSc column), and the numeric
// keypad on rows 2-6 with true key spans (+/Enter double-height, 0 wide).
type SideKeySpec = { id: string; label: string; row: number; col: number; rowspan?: number; colspan?: number };
const leftSideKeys: SideKeySpec[] = [
  { id: "print-screen", label: "PrtSc", row: 1, col: 1 },
  { id: "scroll-lock", label: "ScrLk", row: 1, col: 2 },
  { id: "pause", label: "Pause", row: 1, col: 3 },
  { id: "insert", label: "Ins", row: 2, col: 1 },
  { id: "home", label: "Home", row: 2, col: 2 },
  { id: "page-up", label: "PgUp", row: 2, col: 3 },
  { id: "delete", label: "Del", row: 3, col: 1 },
  { id: "end", label: "End", row: 3, col: 2 },
  { id: "page-down", label: "PgDn", row: 3, col: 3 },
  { id: "arrow-up", label: "↑", row: 5, col: 2, rowspan: 2 },
  { id: "arrow-left", label: "←", row: 6, col: 1 },
  { id: "arrow-down", label: "↓", row: 6, col: 2 },
  { id: "arrow-right", label: "→", row: 6, col: 3 },
];
const numSideKeys: SideKeySpec[] = [
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
function sideArea(spec: SideKeySpec) {
  return spec.row + " / " + spec.col + " / span " + (spec.rowspan || 1) + " / span " + (spec.colspan || 1);
}

const sideKeyColumnCounts: Record<string, number> = {
  "print-screen": 12, "scroll-lock": 4, insert: 20, home: 34, "page-up": 26, delete: 96, end: 41, "page-down": 33,
  "arrow-up": 62, "arrow-left": 88, "arrow-down": 120, "arrow-right": 97,
  "num-lock": 8, "numpad-divide": 5, "numpad-multiply": 6, "numpad-subtract": 14,
  "numpad-7": 42, "numpad-8": 38, "numpad-9": 45, "numpad-add": 18,
  "numpad-4": 31, "numpad-5": 33, "numpad-6": 29,
  "numpad-1": 26, "numpad-2": 28, "numpad-3": 24, "numpad-enter": 22,
  "numpad-0": 44, "numpad-decimal": 16,
};

const demoMouseStats: MouseStat[] = [
  { label: "左键", value: 4832, color: "var(--acc-pink)" },
  { label: "右键", value: 812, color: "var(--acc-violet)" },
  { label: "滚轮", value: 1204, color: "var(--acc-cyan)" },
  { label: "侧键", value: 208, color: "var(--acc-green)" },
];
const demoHourlyActivity = [32, 48, 26, 18, 12, 22, 45, 72, 88, 64, 76, 94, 82, 68, 74, 91, 100, 86, 60, 44, 36, 30, 22, 16];

function backendKeyId(key: KeyItem) {
  const aliases: Record<string, string> = {
    Esc: "escape", "⌫": "backspace", Tab: "tab", Enter: "enter", Space: "space",
    "~": "backquote", "-": "minus", "=": "equal", "[": "bracket-left", "]": "bracket-right",
    "\\": "backslash", ";": "semicolon", "'": "quote", ",": "comma", ".": "period", "/": "slash",
  };
  if (key.id === "Shift-0") return "shift-left";
  if (key.id === "Shift-11") return "shift-right";
  if (key.id === "Ctrl-0") return "ctrl-left";
  if (key.id === "Ctrl-6") return "ctrl-right";
  if (key.id === "Alt-1") return "alt-left";
  if (key.id === "Alt-3") return "alt-right";
  // Duplicated keys in the bottom two rows use a "label-index" id such as "Z-1" or "Space-2";
  // strip the index suffix so the label maps to the backend key id.
  const label = key.id.includes("-") ? key.id.slice(0, key.id.lastIndexOf("-")) : key.id;
  if (label.startsWith("F")) return label.toLowerCase();
  return aliases[label] ?? label.toLowerCase();
}

function keyCount(key: KeyItem) {
  const liveKey = liveDashboard.value?.keys.find((item) => item.keyId === key.id || item.keyId === backendKeyId(key));
  return liveKey?.count ?? (demoMode.value ? key.count : 0);
}

function sideKeyCount(key: { id: string; count?: number }) {
  if (demoMode.value) return key.count ?? sideKeyColumnCounts[key.id] ?? 0;
  const liveKey = liveDashboard.value?.keys.find((item) => item.keyId === key.id);
  return liveKey?.count ?? 0;
}

const allKeys = computed(() => keyboardRows.flat().map((key) => ({ ...key, count: keyCount(key) })));
const totalKeyPresses = computed(() => demoMode.value ? allKeys.value.reduce((sum, key) => sum + key.count, 0) : liveDashboard.value?.totalKeyPresses ?? 0);
const mouseStats = computed<MouseStat[]>(() => {
  if (demoMode.value || !liveDashboard.value) return demoMouseStats;
  const countFor = (ids: string[]) => liveDashboard.value?.mouse.filter((item) => ids.includes(item.actionId)).reduce((sum, item) => sum + item.count, 0) ?? 0;
  return [
    { label: "左键", value: countFor(["left-click"]), color: "var(--acc-pink)" },
    { label: "右键", value: countFor(["right-click"]), color: "var(--acc-violet)" },
    { label: "滚轮", value: countFor(["wheel-up", "wheel-down", "wheel-left", "wheel-right"]), color: "var(--acc-cyan)" },
    { label: "侧键", value: countFor(["x-button-1", "x-button-2"]), color: "var(--acc-green)" },
  ];
});
const totalMouseActions = computed(() =>
  demoMode.value || !liveDashboard.value
    ? mouseStats.value.reduce((sum, item) => sum + item.value, 0)
    : liveDashboard.value.totalMouseActions,
);
const topKeys = computed(() => [...allKeys.value].sort((a, b) => b.count - a.count).slice(0, 4));
const champion = computed(() => topKeys.value.find((key) => key.count > 0) ?? null);
watch(totalKeyPresses, (value) => {
  tweenTo(value, (n) => { shownKeys.value = n; }, () => shownKeys.value, keysTimer);
  checkAchievements(value);
});
watch(totalMouseActions, (value) => {
  tweenTo(value, (n) => { shownMouse.value = n; }, () => shownMouse.value, mouseTimer);
});
const maxKeyCount = computed(() => Math.max(1, ...allKeys.value.map((key) => key.count)));
const hourlyActivity = computed(() => {
  const source = demoMode.value || !liveDashboard.value ? demoHourlyActivity : liveDashboard.value.activity.map((item) => item.count);
  const max = Math.max(1, ...source);
  return source.map((value) => Math.round((value / max) * 100));
});
const activeHours = computed(() => demoMode.value || !liveDashboard.value ? 9 : liveDashboard.value.activity.filter((item) => item.count > 0).length);
const peakHour = computed(() => hourlyActivity.value.indexOf(Math.max(...hourlyActivity.value)));

function formatNumber(value: number) { return value.toLocaleString("zh-CN"); }
/** Map a key count to a color interpolated across the active theme's heat stops. */
function heatColor(count: number) {
  const ratio = Math.min(count / maxKeyCount.value, 1);
  if (heatStops.length < 2) return "rgb(52 217 255)";
  const position = ratio * (heatStops.length - 1);
  const index = Math.min(Math.floor(position), heatStops.length - 2);
  const step = position - index;
  const from = heatStopRgb(heatStops[index]);
  const to = heatStopRgb(heatStops[index + 1]);
  const channel = (offset: number) => Math.round(from[offset] + (to[offset] - from[offset]) * step);
  return `rgb(${channel(0)} ${channel(1)} ${channel(2)})`;
}
function heatLevel(count: number) {
  const ratio = count / maxKeyCount.value;
  return ratio > 0.65 ? "hot" : ratio > 0.28 ? "warm" : "cool";
}

async function fetchActiveDashboard() {
  if (activeRange.value === "自定义") {
    return invoke<DashboardData>("get_dashboard_custom", { start: customStart.value, end: customEnd.value });
  }
  return invoke<DashboardData>("get_dashboard", { range: rangeKeys[activeRange.value] });
}

/** Connect to the Tauri backend once: fetch today's dashboard, recording and
 * input-listener state, then subscribe to live events. Falls back to demo data
 * when running in a plain browser. */
async function connectToRuntime() {
  try {
    const [snapshot, currentRecording, currentInputAvailable] = await Promise.all([
      fetchActiveDashboard(),
      invoke<boolean>("get_recording"),
      invoke<boolean>("get_input_status"),
    ]);
    liveDashboard.value = snapshot;
    demoMode.value = false;
    recording.value = currentRecording;
    inputAvailable.value = currentInputAvailable;
    stopStatsListener = await listen<DashboardData>("stats-updated", (event) => {
      if (activeRange.value === "今天") liveDashboard.value = event.payload;
    });
    stopRecordingListener = await listen<boolean>("recording-changed", (event) => {
      recording.value = event.payload;
    });
  } catch (error) {
    // `npm run dev` runs outside Tauri, so keeping the preview data is intentional.
    console.info("KeyPulse runtime is not connected; showing preview data.", error);
  }
}

async function changeRange(range: string) {
  activeRange.value = range;
  customRangeError.value = "";
  showDatePicker.value = false;
  if (!demoMode.value) {
    try {
      liveDashboard.value = await fetchActiveDashboard();
    } catch (error) {
      console.info("Could not load dashboard range.", error);
    }
  }
}

function toggleDatePicker() {
  if (!showDatePicker.value) {
    draftStart.value = customStart.value;
    draftEnd.value = customEnd.value;
    customRangeError.value = "";
  }
  showDatePicker.value = !showDatePicker.value;
}

/** Apply the edited custom date range after validating order; refreshes data. */
async function applyCustomRange() {
  customRangeError.value = "";
  if (!draftStart.value || !draftEnd.value) {
    customRangeError.value = "请选择开始日期和结束日期";
    return;
  }
  if (draftStart.value > draftEnd.value) {
    customRangeError.value = "开始日期不能晚于结束日期";
    return;
  }

  customStart.value = draftStart.value;
  customEnd.value = draftEnd.value;
  activeRange.value = "自定义";
  showDatePicker.value = false;
  if (!demoMode.value) {
    try {
      liveDashboard.value = await fetchActiveDashboard();
    } catch (error) {
      customRangeError.value = "日期范围加载失败，请稍后重试";
      console.info("Could not load custom dashboard range.", error);
    }
  }
}

async function toggleRecording() {
  const nextValue = !recording.value;
  try {
    await invoke("set_recording", { enabled: nextValue });
  } catch {
    // The browser-only preview still lets the control be explored.
  }
  recording.value = nextValue;
}

/** Wipe all aggregates after a confirm dialog, then refresh the view. */
async function clearStats() {
  if (demoMode.value || !window.confirm("确定清空本地统计数据吗？此操作不可撤销。")) return;
  try {
    await invoke("clear_stats");
    liveDashboard.value = await fetchActiveDashboard();
  } catch (error) {
    console.info("Could not clear dashboard data.", error);
  }
}

onMounted(async () => {
  applyTheme(themeId.value);
  if (isMiniWindow) return; // MiniStat owns its lifecycle
  if (!isKeyshowWindow) {
    connectToRuntime();
    wireSoundFx();
    cloudSyncToday();
    cloudSyncTimer = setInterval(cloudSyncToday, 30_000);
    const storedCustom = localStorage.getItem("keypulse-custom-sound");
    if (soundVoice.value === "custom" && storedCustom) {
      invoke<string>("read_custom_sound_base64", { fileName: storedCustom })
        .then((dataUrl) => loadCustomSound(dataUrl))
        .catch(() => undefined);
    }
    setTimeout(autoShowFootprintIfNew, 2600);
    refreshKeyshowState();
    refreshMiniState();
    try {
      if (keyshowPosition.value === "custom") {
        const cx = Number(localStorage.getItem("keypulse-keyshow-custom-x")) || 0;
        const cy = Number(localStorage.getItem("keypulse-keyshow-custom-y")) || 0;
        const dpr = window.devicePixelRatio || 1;
        await invoke("set_keyshow_custom_position", { x: Math.round(cx * dpr), y: Math.round(cy * dpr) });
      } else {
        await invoke("set_keyshow_position", { position: keyshowPosition.value });
      }
      await invoke("set_keyshow_size", { size: keyshowSize.value });
      await invoke("set_keyshow_opacity", { opacity: keyshowOpacity.value });
      await invoke("set_keyshow_drag_mode", { enabled: keyshowDrag.value });
    } catch {
      // Older runtime without layout commands.
    }
    try {
      stopKeyshowChangedListener = await listen<boolean>("keyshow-changed", (event) => {
        keyshowEnabled.value = event.payload;
      });
      stopMiniListener = await listen<boolean>("mini-changed", (event) => {
        miniEnabled.value = event.payload;
      });
    } catch {
      // Browser preview has no runtime events.
    }
  }
  document.addEventListener("click", closePopoversOnOutsideClick);
});
onUnmounted(() => {
  stopStatsListener?.();
  stopRecordingListener?.();
  stopKeyshowChangedListener?.();
  stopMiniListener?.();
  stopKeySoundListener?.();
  stopMetronome();
  if (cloudSyncTimer) clearInterval(cloudSyncTimer);
  document.removeEventListener("click", closePopoversOnOutsideClick);
});
</script>

<template>
  <KeyshowStage v-if="isKeyshowWindow" />
  <main v-else-if="isMiniWindow" class="mini-host"><MiniStat /></main>
  <main v-else class="app-shell">
    <div class="ambient ambient-one"></div><div class="ambient ambient-two"></div>
    <header class="topbar">
      <div class="brand-lockup">
        <div class="brand-mark"><span></span><span></span><span></span></div>
        <div><p class="eyebrow">PERSONAL INPUT LAB</p><h1>Key<span>Pulse</span></h1></div>
      </div>
      <div class="topbar-actions">
        <div class="demo-chip" :class="{ warning: !demoMode && !inputAvailable }"><i></i> {{ demoMode ? "演示数据" : inputAvailable ? "本地实时数据" : "监听不可用" }}</div>
        <div class="keyshow-control">
          <button class="keyshow-button" :class="{ on: keyshowEnabled }" aria-label="按键可视化开/关" :title="keyshowEnabled ? '按键可视化：开（点击关闭）' : '按键可视化：关（点击开启）'" @click="toggleKeyshow"><i>⌨</i><span class="keyshow-led"></span></button>
        </div>
        <button class="settings-button" aria-label="打开设置" @click="openSettings"><i>⚙</i></button>
        <div class="settings-control">
          <div v-if="showSettingsPanel" class="ks-modal-backdrop" @click.self="showSettingsPanel = false">
            <section class="ks-modal" role="dialog" aria-modal="true" aria-label="设置" tabindex="-1" @keydown.esc="showSettingsPanel = false">
              <div class="ks-modal-head"><div><p class="eyebrow accent">SETTINGS</p><h3>设置</h3></div><button class="ks-modal-close" aria-label="关闭设置" @click="showSettingsPanel = false">×</button></div>
              <div class="ks-section-title">我的档案</div>
              <div v-if="activeProfile" class="profile-current">
                <i class="profile-avatar" :style="{ background: activeProfile.color }"></i>
                <span class="profile-meta"><b>{{ activeProfile.name }}</b><small>最佳 {{ activeProfile.best }} 键 · 胜 {{ activeProfile.wins }} 负 {{ activeProfile.losses }} · {{ activeProfile.games }} 局</small></span>
                <button class="ks-radio small" @click="promptRename(activeProfile)">改名</button>
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
              <CloudAccount />
              <div class="ks-section-title">主题配色</div>
              <div class="settings-themes" role="radiogroup" aria-label="主题配色">
                <button v-for="option in themeOptions" :key="option.id" role="radio" :aria-checked="themeId === option.id" :class="{ active: themeId === option.id }" class="setting-theme" @click="applyTheme(option.id)"><span class="theme-dots"><i v-for="(dot, dotIndex) in option.dots" :key="dotIndex" :style="{ background: dot }"></i></span>{{ option.name }}</button>
              </div>
              <div class="ks-section-title">按键可视化</div>
              <button class="keyshow-master" :class="{ on: keyshowEnabled }" @click="toggleKeyshow"><span class="ks-master-text"><b>{{ keyshowEnabled ? "正在显示按键" : "已关闭" }}</b><small>{{ keyshowEnabled ? "按下的键实时显示在屏幕" : "开启后按键会实时显示在屏幕" }}</small></span><span class="ks-switch"><i></i></span></button>
              <div class="ks-layout-title">显示风格</div>
              <div class="ks-styles" role="radiogroup" aria-label="按键显示风格">
                <button v-for="option in keyshowOptions" :key="option.id" role="radio" :aria-checked="keyshowStyle === option.id" class="ks-style" :class="{ active: keyshowStyle === option.id }" @click="pickKeyshowStyle(option.id)"><span class="ks-style-icon">{{ option.icon }}</span><span class="ks-style-text"><b>{{ option.name }}</b><small>{{ option.desc }}</small></span></button>
              </div>
              <div class="ks-layout-row">
                <div class="ks-layout-col"><div class="ks-layout-title">显示位置</div>
                  <div class="ks-positions" role="radiogroup" aria-label="按键浮层显示位置">
                    <button v-for="pos in keyshowPositions" :key="pos.id" class="ks-pos" :class="{ active: keyshowPosition === pos.id }" role="radio" :aria-checked="keyshowPosition === pos.id" :title="pos.name" @click="changeKeyshowPosition(pos.id)"><i :style="{ left: pos.dot.left, top: pos.dot.top }"></i></button>
                  </div>
                </div>
                <div class="ks-layout-col"><div class="ks-layout-title">浮层大小</div>
                  <div class="ks-sizes" role="radiogroup" aria-label="按键浮层大小">
                    <button v-for="option in keyshowSizeOptions" :key="option.id" class="ks-size" :class="{ active: keyshowSize === option.id }" role="radio" :aria-checked="keyshowSize === option.id" @click="changeKeyshowSize(option.id)">{{ option.name }}</button>
                  </div>
                </div>
              </div>
              <div class="ks-layout-row">
                <div class="ks-layout-col">
                  <div class="ks-layout-title">透明度</div>
                  <label class="ks-range"><input type="range" min="20" max="100" step="5" :value="Math.round(keyshowOpacity * 100)" @input="changeKeyshowOpacity(Number(($event.target as HTMLInputElement).value))" /><span>{{ Math.round(keyshowOpacity * 100) }}%</span></label>
                </div>
                <div class="ks-layout-col">
                  <div class="ks-layout-title">拖动位置</div>
                  <button class="ks-drag-toggle" :class="{ on: keyshowDrag }" @click="toggleKeyshowDrag(!keyshowDrag)"><span class="ks-master-text"><b>{{ keyshowDrag ? "拖动中 · 手柄已出现" : "已锁定" }}</b><small>{{ keyshowDrag ? "拖到想要的位置后回来点一下锁定" : "开启后浮层出现手柄，可拖到任意位置" }}</small></span><span class="ks-switch"><i></i></span></button>
                </div>
              </div>
              <div class="ks-section-title">迷你统计窗</div>
              <button class="keyshow-master" :class="{ on: miniEnabled }" @click="toggleMini"><span class="ks-master-text"><b>{{ miniEnabled ? "迷你窗已显示" : "迷你窗已隐藏" }}</b><small>{{ miniEnabled ? "右上角小卡片实时显示今日总量与冠军键" : "开启后在桌面右上角显示实时统计小卡片" }}</small></span><span class="ks-switch"><i></i></span></button>
              <div class="ks-section-title">启动与关闭</div>
              <div class="ks-behavior-row">
                <button class="ks-drag-toggle" :class="{ on: autostartOn }" @click="toggleAutostart(!autostartOn)"><span class="ks-master-text"><b>{{ autostartOn ? "开机自启动已开" : "开机自启动已关" }}</b><small>{{ autostartOn ? "登录 Windows 后自动在后台运行" : "开机时不会自动启动" }}</small></span><span class="ks-switch"><i></i></span></button>
              </div>
              <div class="ks-radio-row">
                <span class="ks-radio-label">启动时</span>
                <div class="ks-radios" role="radiogroup" aria-label="启动方式">
                  <button v-for="opt in [{ id: 'normal', name: '显示窗口' }, { id: 'minimized', name: '最小化' }, { id: 'tray', name: '后台托盘' }]" :key="opt.id" class="ks-radio" :class="{ active: startBehavior === opt.id }" role="radio" :aria-checked="startBehavior === opt.id" @click="changeBehavior('start', opt.id)">{{ opt.name }}</button>
                </div>
              </div>
              <div class="ks-radio-row">
                <span class="ks-radio-label">关闭时</span>
                <div class="ks-radios" role="radiogroup" aria-label="关闭按钮行为">
                  <button v-for="opt in [{ id: 'tray', name: '隐藏到托盘' }, { id: 'minimize', name: '最小化' }, { id: 'quit', name: '退出' }]" :key="opt.id" class="ks-radio" :class="{ active: closeBehavior === opt.id }" role="radio" :aria-checked="closeBehavior === opt.id" @click="changeBehavior('close', opt.id)">{{ opt.name }}</button>
                </div>
              </div>
              <div class="ks-section-title">数据存储</div>
              <div class="ks-data">
                <button class="ks-data-opt" :class="{ active: dataLocation === 'appdata' }" @click="migrateData('appdata')"><b>系统数据目录</b><small>默认位置，任何安装方式都可用</small></button>
                <button class="ks-data-opt" :class="{ active: dataLocation === 'appdir' }" @click="migrateData('appdir')"><b>程序所在目录</b><small>便携式，不占系统盘（安装版可能因权限不可写）</small></button>
              </div>
              <p class="ks-data-path">当前数据库：<code>{{ dataPath || "加载中…" }}</code></p>
              <p v-if="dataNotice" class="ks-data-notice">{{ dataNotice }}</p>
                            <div class="ks-section-title">趣味功能</div>
              <div class="ks-layout-row">
                <div class="ks-layout-col"><div class="ks-layout-title">打字音效</div>
                  <div class="ks-sound-row">
                    <select class="ks-select" :value="soundVoice" @change="setSoundVoice(($event.target as HTMLSelectElement).value as SoundVoice)">
                      <option value="off">关闭</option><option value="click">机械青轴</option><option value="typewriter">打字机</option><option value="bubble">泡泡</option><option value="blub">咕噜气泡</option><option value="bell">风铃</option><option value="mahjong">麻将</option><option value="arcade">8bit 游戏机</option><option value="laser">激光枪</option>
                    </select>
                    <label class="ks-range compact"><input type="range" min="0" max="100" step="5" :value="soundVolume" :disabled="soundVoice === 'off'" @input="setSoundVolume(Number(($event.target as HTMLInputElement).value))" /><span>{{ soundVolume }}</span></label>
                  </div>
                </div>
                <div class="ks-layout-col"><div class="ks-layout-title">成就提示</div>
                  <button class="ks-drag-toggle" :class="{ on: achievementsOn }" @click="toggleAchievements(!achievementsOn)"><span class="ks-master-text"><b>{{ achievementsOn ? "已开启" : "已关闭" }}</b><small>当日 1k / 5k / 1w / 5w 键里程碑弹提示</small></span><span class="ks-switch"><i></i></span></button>
                </div>
              </div>
              <div class="ks-layout-row">
                <div class="ks-layout-col"><div class="ks-layout-title">每日足迹卡</div>
                  <button class="ks-drag-toggle" :class="{ on: footprintAuto }" @click="toggleFootprintAuto(!footprintAuto)"><span class="ks-master-text"><b>{{ footprintAuto ? "自动提醒已开" : "自动提醒已关" }}</b><small>每天首次打开时弹出当天的足迹卡</small></span><span class="ks-switch"><i></i></span></button>
                </div>
                <div class="ks-layout-col"><div class="ks-layout-title"> </div>
                  <button class="ks-size" style="width:100%; padding:11px 0;" @click="openFootprintCard">✦ 立即查看今日足迹</button>
                </div>
              </div>
              <div class="ks-layout-row">
                <div class="ks-layout-col"><div class="ks-layout-title">自定义音效</div>
                  <div class="ks-sound-row">
                    <select class="ks-select" :value="customSoundName" @change="applyCustomSound(($event.target as HTMLSelectElement).value)">
                      <option value="">选择音频文件…</option>
                      <option v-for="file in customSounds" :key="file" :value="file">{{ file }}</option>
                    </select>
                    <button class="ks-size" style="width:100%; padding:6px 0;" @click="refreshCustomSounds">↻ 刷新文件列表</button>
                    <small class="ks-custom-hint">把 .mp3/.wav 放进：{{ customSoundDir || "加载中…" }}</small>
                  </div>
                </div>
                <div class="ks-layout-col"><div class="ks-layout-title">节奏节拍器</div>
                  <button class="ks-drag-toggle" :class="{ on: metronomeOn }" @click="toggleMetronome(!metronomeOn)"><span class="ks-master-text"><b>{{ metronomeOn ? "节拍器运行中 · 第 " + beatCount + " 拍" : "节拍器已停" }}</b><small>{{ metronomeOn ? "按 BPM 打点，重拍提示" : "开启后每拍滴答提示节奏" }}</small></span><span class="ks-switch"><i></i></span></button>
                  <label class="ks-range compact"><input type="range" min="40" max="220" step="2" :value="bpm" @input="changeBpm(Number(($event.target as HTMLInputElement).value))" /><span>{{ bpm }} BPM</span></label>
                </div>
              </div>
<p class="ks-note">⌨ 显示的是按下动作，不记录文本 · 托盘菜单或顶栏 ⌨ 按钮可随时开/关 · 拖动后选择任意预设位置可恢复对齐</p>
            </section>
          </div>
        </div>
        <div class="theme-control">
          <button class="theme-button" aria-label="切换主题配色" :aria-expanded="showThemePicker" @click="showThemePicker = !showThemePicker"><i class="theme-dot" :style="{ background: 'var(--acc-pink)' }"></i><i class="theme-dot" :style="{ background: 'var(--acc-cyan)' }"></i><i class="theme-dot" :style="{ background: 'var(--acc-violet)' }"></i></button>
          <div v-if="showThemePicker" class="theme-popover" role="listbox" aria-label="主题配色">
            <p class="theme-popover-title">主题配色</p>
            <button v-for="option in themeOptions" :key="option.id" role="option" :aria-selected="themeId === option.id" :class="{ active: themeId === option.id }" class="theme-option" @click="applyTheme(option.id)"><span class="theme-dots"><i v-for="(dot, dotIndex) in option.dots" :key="dotIndex" :style="{ background: dot }"></i></span>{{ option.name }}</button>
          </div>
        </div>
        <button class="record-button" :class="{ paused: !recording }" :disabled="!demoMode && !inputAvailable" :title="!demoMode && !inputAvailable ? '全局输入监听不可用' : ''" @click="toggleRecording"><span class="record-dot"></span>{{ recording ? "正在记录" : "已暂停" }}</button>
        <button class="avatar-button" aria-label="打开隐私与权限说明" :aria-expanded="showPrivacyPanel" @click="showPrivacyPanel = true">KP</button>
      </div>
    </header>

    <div v-if="!demoMode && !inputAvailable" class="runtime-warning" role="status"><span>!</span><div><b>全局输入监听未连接</b><small>本地统计仍可查看；请检查系统权限后重启 KeyPulse。</small></div></div>

    <div v-if="showPrivacyPanel" class="privacy-backdrop" role="presentation" @click.self="showPrivacyPanel = false">
      <section class="privacy-dialog" role="dialog" aria-modal="true" aria-labelledby="privacy-title" tabindex="-1" ref="privacyDialog" @keydown.esc="showPrivacyPanel = false">
        <div class="privacy-dialog-heading"><div><p class="eyebrow accent">PRIVACY FIRST</p><h3 id="privacy-title">隐私与权限说明</h3></div><button class="privacy-close" aria-label="关闭隐私说明" @click="showPrivacyPanel = false">×</button></div>
        <p class="privacy-intro">KeyPulse 只回答“哪些输入更常用”，不会保存“你输入了什么”。</p>
        <div class="privacy-points">
          <article><span>01</span><div><b>只存聚合统计</b><small>数据库按日期、小时和键位/鼠标动作保存次数，不保存原始输入序列。</small></div></article>
          <article><span>02</span><div><b>全程本机处理</b><small>统计和 SQLite 数据留在本机，不上传服务器，也不保存鼠标坐标。</small></div></article>
          <article><span>03</span><div><b>随时可控</b><small>顶部或托盘可以暂停/继续，底部“清空本地数据”可以删除现有聚合统计。</small></div></article>
        </div>
        <div class="privacy-notice"><b>权限提示</b><span>普通权限通常可以统计常规桌面输入；管理员窗口、UAC 安全桌面和部分受保护程序可能无法被低级 Hook 观测。</span></div>
        <div class="privacy-storage"><span>本地数据库</span><code>默认 %APPDATA%\com.keyboardmouse.heatmap\keypulse.sqlite · 可在“设置 → 数据存储”中更改位置</code></div>
      </section>
    </div>

    <section class="hero-row">
      <div><p class="eyebrow accent">YOUR RHYTHM, VISUALIZED</p><h2>{{ rangeHeading }}的输入节奏<br /><em>每一次动作都算数。</em></h2><p class="hero-copy">看见每一次敲击、点击和滚动，找到属于你的数字节奏。</p></div>
      <div class="range-control">
        <div class="range-switch" role="tablist" aria-label="时间范围">
          <button v-for="range in ranges" :key="range" :class="{ active: activeRange === range }" @click="changeRange(range)">{{ range }}</button><button class="calendar-button" :class="{ active: activeRange === '自定义' }" aria-label="选择日期" :aria-expanded="showDatePicker" @click="toggleDatePicker">▣</button>
        </div>
        <div v-if="showDatePicker" class="date-popover">
          <p class="date-popover-title">自定义时间范围</p>
          <label>开始日期<input v-model="draftStart" type="date" :max="maxSelectableDate" /></label>
          <label>结束日期<input v-model="draftEnd" type="date" :max="maxSelectableDate" /></label>
          <p v-if="customRangeError" class="date-error">{{ customRangeError }}</p>
          <div class="date-popover-actions"><button class="date-cancel" @click="showDatePicker = false">取消</button><button class="date-apply" @click="applyCustomRange">应用范围</button></div>
        </div>
      </div>
    </section>

    <section class="stat-grid">
      <article class="stat-card stat-card-primary"><div class="card-icon icon-spark">✦</div><p>总按键数</p><strong>{{ formatNumber(shownKeys) }}</strong><span class="trend" :class="demoMode ? 'up' : 'neutral'">{{ demoMode ? "↗ 12.8%" : "⌁ 已保存聚合" }} <small>{{ demoMode ? "对比昨日" : activeRangeLabel }}</small></span></article>
      <article class="stat-card"><div class="card-icon icon-mouse">●</div><p>鼠标操作</p><strong>{{ formatNumber(shownMouse) }}</strong><span class="trend" :class="demoMode ? 'up' : 'neutral'">{{ demoMode ? "↗ 8.4%" : "⌁ 已保存聚合" }} <small>{{ demoMode ? "对比昨日" : activeRangeLabel }}</small></span></article>
      <article class="stat-card"><div class="card-icon icon-time">◷</div><p>活跃时段</p><strong>{{ activeHours }}<span class="unit">h</span></strong><span class="trend neutral">⌁ 按小时聚合统计</span></article>
      <article class="stat-card highlight-card"><div class="card-icon icon-top">♛</div><p>{{ activeRange === "今天" ? "今日冠军" : "范围冠军" }}</p><strong>{{ champion?.label ?? "暂无" }}</strong><span class="trend accent-text">{{ formatNumber(champion?.count ?? 0) }} 次按下</span></article>
    </section>

    <section class="content-grid">
      <article class="panel keyboard-panel">
        <div class="panel-heading"><div><p class="eyebrow">KEYBOARD MAP</p><h3>键盘热力图</h3></div><div class="legend"><span class="legend-gradient"></span><small>低</small><small>高</small></div></div>
        <div class="keyboard-wrap">
          <div class="kb-main">
            <div v-for="(row, rowIndex) in keyboardRows" :key="rowIndex" class="keyboard-row">
              <div v-for="key in row" :key="key.id" class="keycap" :class="[heatLevel(keyCount(key)), { muted: key.muted, blank: key.blank }]" :style="{ flex: `${key.width ?? 1} 1 0`, '--key-color': heatColor(keyCount(key)) }" :title="`${key.label}：${formatNumber(keyCount(key))} 次`"><span>{{ key.label }}</span><b>{{ formatNumber(keyCount(key)) }}</b></div>
            </div>
          </div>
          <div class="kb-side">
            <div class="kb-right-block">
              <div v-for="key in leftSideKeys" :key="key.id" class="keycap side" :style="{ gridArea: sideArea(key), '--key-color': heatColor(sideKeyCount(key)) }" :title="`${key.label}：${formatNumber(sideKeyCount(key))} 次`"><span>{{ key.label }}</span><b>{{ formatNumber(sideKeyCount(key)) }}</b></div>
            </div>
            <div class="kb-right-block num">
              <div v-for="key in numSideKeys" :key="key.id" class="keycap side" :style="{ gridArea: sideArea(key), '--key-color': heatColor(sideKeyCount(key)) }" :title="`${key.label}：${formatNumber(sideKeyCount(key))} 次`"><span>{{ key.label }}</span><b>{{ formatNumber(sideKeyCount(key)) }}</b></div>
            </div>
          </div>
        </div>
        <div class="keyboard-footer"><span><i class="live-indicator"></i>{{ demoMode ? "界面预览数据" : "数据实时更新中" }}</span><span>按键总量 · {{ formatNumber(totalKeyPresses) }}</span></div>
      </article>

      <div class="side-column">
        <article class="panel mouse-panel">
          <div class="panel-heading compact"><div><p class="eyebrow">MOUSE MAP</p><h3>鼠标热力图</h3></div><span class="panel-kicker">{{ formatNumber(totalMouseActions) }} actions</span></div>
          <div class="mouse-content"><div class="mouse-shape" aria-label="鼠标模板"><div class="mouse-top"><div class="mouse-button mouse-left"><span>{{ formatNumber(mouseStats[0].value) }}</span></div><div class="mouse-button mouse-right"><span>{{ formatNumber(mouseStats[1].value) }}</span></div><div class="mouse-wheel"><i></i></div></div><div class="mouse-side-buttons"><i></i><i></i></div></div><div class="mouse-stats"><div v-for="item in mouseStats" :key="item.label" class="mouse-stat"><i :style="{ background: item.color }"></i><span>{{ item.label }}</span><b>{{ formatNumber(item.value) }}</b></div></div></div>
        </article>
        <article class="panel top-keys-panel">
          <div class="panel-heading compact"><div><p class="eyebrow">TOP KEYS</p><h3>高频按键</h3></div><span class="sparkline">╱╲╱╲╱╱╲</span></div>
          <div class="top-key-list"><div v-for="(key, index) in topKeys" :key="key.id" class="top-key-row"><span class="rank">0{{ index + 1 }}</span><span class="top-key-label">{{ key.label }}</span><div class="mini-bar"><i :style="{ width: `${(key.count / maxKeyCount) * 100}%`, background: heatColor(key.count) }"></i></div><b>{{ formatNumber(key.count) }}</b></div></div>
        </article>
      </div>
    </section>

    <section class="panel timeline-panel"><div class="panel-heading compact"><div><p class="eyebrow">ACTIVITY PULSE · {{ activeRangeLabel }}</p><h3>一天中的活跃节奏</h3></div><span class="timeline-note">峰值时段 <b>{{ String(peakHour).padStart(2, "0") }}:00</b></span></div><div class="timeline-chart"><div class="chart-grid-lines"><i></i><i></i><i></i><i></i></div><div v-for="(value, hour) in hourlyActivity" :key="hour" class="chart-column"><div class="chart-bar" :style="{ height: `${value * 0.84}%` }"><span>{{ value }}</span></div><small v-if="hour % 3 === 0">{{ String(hour).padStart(2, "0") }}:00</small></div></div></section>
    <PkDuel v-if="showPkDuel" @close="showPkDuel = false" />
    <DailyCard v-if="showFootprintCard && footprintSnapshot" :snapshot="footprintSnapshot" @close="markFootprintSeen" />
    <Transition name="beat-pop"><i v-if="metronomeOn" :key="beatCount" class="beat-dot"></i></Transition>
    <Transition name="toast-pop"><div v-if="toastMsg" class="achievement-toast" role="status"><span>🏆</span><div><b>成就达成</b><small>{{ toastMsg }}</small></div></div></Transition>
    <footer class="footer-note"><span>KeyPulse · offline by design</span><span>隐私优先 · 只保存聚合统计，不保存输入文本</span><button class="clear-button" :disabled="demoMode" @click="clearStats">清空本地数据</button><button class="footprint-button" @click="openFootprintCard">✦ 足迹卡</button><button class="footprint-button pk-launch" @click="showPkDuel = true">⚔ PK 对战</button></footer>
  </main>
</template>

<style>
:root {
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color-scheme: dark;
  /* neon 霓虹之夜 (default) */
  --page-bg: #0f172a; --page-glow: rgba(120, 87, 255, .17);
  --acc-pink: #ff5c7a; --acc-pink-bright: #ff718b; --acc-pink-soft: #ff8098;
  --acc-cyan: #34d9ff; --acc-cyan-bright: #72e5ff;
  --acc-violet: #a78bfa; --acc-green: #2de2a6; --acc-amber: #ffd166;
  --panel-rgb: 23, 37, 84; --hero-rgb: 49, 56, 112; --ink-rgb: 8, 16, 35; --pop-rgb: 19, 31, 70;
  --pink-rgb: 255, 92, 122; --cyan-rgb: 52, 217, 255; --violet-rgb: 167, 139, 250;
  --green-rgb: 45, 226, 166; --amber-rgb: 255, 209, 102;
  --text-main: #f8fafc; --surface-active: #2f3c65;
  --tx-strong: #e2e8f0; --tx-soft: #a9b6cc; --tx-dim: #8d9ab3; --tx-faint: #71819d;
  --tx-mute: #53627c; --amber-mute: #c1a968;
  --line-rgb: 148, 163, 184; --veil-rgb: 4, 9, 24;
  --bar-track: #263452; --bar-tip: #455184; --apply-ink: #091329;
  --heat-1: #276eaa; --heat-2: #34d9ff; --heat-3: #2de2a6; --heat-4: #ffd166; --heat-5: #ff5c7a;
  transition: background .3s ease, color .3s ease;
}
html[data-theme="ocean"] {
  --page-bg: #071422; --page-glow: rgba(56, 189, 248, .18);
  --acc-pink: #2dd4bf; --acc-pink-bright: #5eead4; --acc-pink-soft: #99f6e4;
  --acc-cyan: #38bdf8; --acc-cyan-bright: #7dd3fc;
  --acc-violet: #818cf8; --acc-green: #4ade80; --acc-amber: #fbbf24;
  --panel-rgb: 15, 38, 74; --hero-rgb: 20, 52, 96; --ink-rgb: 4, 14, 28; --pop-rgb: 12, 32, 62;
  --pink-rgb: 45, 212, 191; --cyan-rgb: 56, 189, 248; --violet-rgb: 129, 140, 248;
  --green-rgb: 74, 222, 128; --amber-rgb: 251, 191, 36;
  --surface-active: #1e4a78; --bar-track: #14283f; --bar-tip: #2c4a6e; --apply-ink: #03121f;
  --heat-1: #1e6091; --heat-2: #38bdf8; --heat-3: #4ade80; --heat-4: #fbbf24; --heat-5: #fb7185;
}
html[data-theme="sunset"] {
  --page-bg: #1d0f1e; --page-glow: rgba(251, 146, 60, .2);
  --acc-pink: #fb923c; --acc-pink-bright: #fdba74; --acc-pink-soft: #ffb4a2;
  --acc-cyan: #f472b6; --acc-cyan-bright: #f9a8d4;
  --acc-violet: #c084fc; --acc-green: #fbbf24; --acc-amber: #fde047;
  --panel-rgb: 58, 22, 52; --hero-rgb: 92, 30, 66; --ink-rgb: 24, 7, 22; --pop-rgb: 48, 17, 44;
  --pink-rgb: 251, 146, 60; --cyan-rgb: 244, 114, 182; --violet-rgb: 192, 132, 252;
  --green-rgb: 251, 191, 36; --amber-rgb: 253, 224, 71;
  --surface-active: #6d2a52; --bar-track: #3c1c35; --bar-tip: #7c3a5e; --apply-ink: #2a0c21;
  --heat-1: #9d4edd; --heat-2: #f472b6; --heat-3: #fdba74; --heat-4: #fde047; --heat-5: #fb923c;
}
html[data-theme="aurora"] {
  --page-bg: #081410; --page-glow: rgba(52, 211, 153, .18);
  --acc-pink: #34d399; --acc-pink-bright: #6ee7b7; --acc-pink-soft: #a7f3d0;
  --acc-cyan: #22d3ee; --acc-cyan-bright: #67e8f9;
  --acc-violet: #a3e635; --acc-green: #4ade80; --acc-amber: #facc15;
  --panel-rgb: 12, 42, 33; --hero-rgb: 17, 62, 47; --ink-rgb: 4, 18, 13; --pop-rgb: 10, 34, 27;
  --pink-rgb: 52, 211, 153; --cyan-rgb: 34, 211, 238; --violet-rgb: 163, 230, 53;
  --green-rgb: 74, 222, 128; --amber-rgb: 250, 204, 21;
  --surface-active: #155e47; --bar-track: #0f2e22; --bar-tip: #1f4a38; --apply-ink: #03120c;
  --heat-1: #0f766e; --heat-2: #22d3ee; --heat-3: #a3e635; --heat-4: #facc15; --heat-5: #fb923c;
}

/* neon-drive 霓虹夜驰 — classic synthwave (designer palette: #FF2FD4 #05F4FF #0B032D) */
html[data-theme="neon-drive"] {
  --page-bg: #0b032d; --page-glow: rgba(5, 244, 255, .2);
  --acc-pink: #ff2fd4; --acc-pink-bright: #ff6fe0; --acc-pink-soft: #ffa4ec;
  --acc-cyan: #05f4ff; --acc-cyan-bright: #55faff;
  --acc-violet: #7b2cff; --acc-green: #f9f871; --acc-amber: #ffb86b;
  --panel-rgb: 18, 5, 52; --hero-rgb: 28, 8, 78; --ink-rgb: 5, 1, 20; --pop-rgb: 22, 6, 60;
  --pink-rgb: 255, 47, 212; --cyan-rgb: 5, 244, 255; --violet-rgb: 123, 44, 255;
  --green-rgb: 249, 248, 113; --amber-rgb: 255, 184, 107;
  --surface-active: #40138f; --bar-track: #1d0a44; --bar-tip: #4b1ea0; --apply-ink: #0b032d;
  --heat-1: #2b2dff; --heat-2: #05f4ff; --heat-3: #ff2fd4; --heat-4: #ffb86b; --heat-5: #f9f871;
}
/* miami 迈阿密海岸 — Miami Vice coastal neon (designer palette: #FF5E9F #3AE7FF #0B1021) */
html[data-theme="miami"] {
  --page-bg: #0b1021; --page-glow: rgba(58, 231, 255, .18);
  --acc-pink: #ff5e9f; --acc-pink-bright: #ff82b9; --acc-pink-soft: #ffa8d0;
  --acc-cyan: #3ae7ff; --acc-cyan-bright: #7cf1ff;
  --acc-violet: #1f2cff; --acc-green: #09fbd3; --acc-amber: #ffb86b;
  --panel-rgb: 16, 22, 48; --hero-rgb: 24, 34, 72; --ink-rgb: 4, 6, 16; --pop-rgb: 20, 26, 58;
  --pink-rgb: 255, 94, 159; --cyan-rgb: 58, 231, 255; --violet-rgb: 31, 44, 255;
  --green-rgb: 9, 251, 211; --amber-rgb: 255, 184, 107;
  --surface-active: #2739a8; --bar-track: #182648; --bar-tip: #3a52c8; --apply-ink: #0b1021;
  --heat-1: #2b3a8f; --heat-2: #3ae7ff; --heat-3: #09fbd3; --heat-4: #ffb86b; --heat-5: #ff5e9f;
}
/* sunset-horizon 落日地平线 — synthwave sun gradient (designer: #FF006E #7B2CFF #240046) */
html[data-theme="sunset-horizon"] {
  --page-bg: #240046; --page-glow: rgba(255, 0, 110, .26);
  --acc-pink: #ff006e; --acc-pink-bright: #ff4d94; --acc-pink-soft: #ff85b8;
  --acc-cyan: #9d4edd; --acc-cyan-bright: #bf77ea;
  --acc-violet: #7b2cff; --acc-green: #ffd670; --acc-amber: #ffbf69;
  --panel-rgb: 40, 0, 70; --hero-rgb: 58, 4, 100; --ink-rgb: 12, 0, 24; --pop-rgb: 34, 2, 60;
  --pink-rgb: 255, 0, 110; --cyan-rgb: 157, 78, 221; --violet-rgb: 123, 44, 255;
  --green-rgb: 255, 214, 112; --amber-rgb: 255, 191, 105;
  --surface-active: #6a1fb0; --bar-track: #33064f; --bar-tip: #6b239e; --apply-ink: #240046;
  --heat-1: #4a0e8f; --heat-2: #7b2cff; --heat-3: #ff006e; --heat-4: #ff5c39; --heat-5: #ffd670;
}
/* laser-horizon 镭射地平线 — laser streaks over violet night (designer: #FF3F8E #FF8A3D #1A0B2E) */
html[data-theme="laser-horizon"] {
  --page-bg: #1a0b2e; --page-glow: rgba(255, 63, 142, .24);
  --acc-pink: #ff3f8e; --acc-pink-bright: #ff6fac; --acc-pink-soft: #ff9fcb;
  --acc-cyan: #ff8a3d; --acc-cyan-bright: #ffab6f;
  --acc-violet: #7b2cff; --acc-green: #4dffc3; --acc-amber: #ffd447;
  --panel-rgb: 32, 14, 60; --hero-rgb: 46, 20, 88; --ink-rgb: 10, 3, 20; --pop-rgb: 30, 12, 56;
  --pink-rgb: 255, 63, 142; --cyan-rgb: 255, 138, 61; --violet-rgb: 123, 44, 255;
  --green-rgb: 77, 255, 195; --amber-rgb: 255, 212, 71;
  --surface-active: #6420b8; --bar-track: #2c1454; --bar-tip: #5a2aa0; --apply-ink: #1a0b2e;
  --heat-1: #3d1680; --heat-2: #7b2cff; --heat-3: #ff3f8e; --heat-4: #ff8a3d; --heat-5: #ffd447;
}
/* cyber-alley 赛博雨巷 — rainy neon city (designer: #08F7FE #FE53BB #050816) */
html[data-theme="cyber-alley"] {
  --page-bg: #050816; --page-glow: rgba(8, 247, 254, .2);
  --acc-pink: #fe53bb; --acc-pink-bright: #ff7fd0; --acc-pink-soft: #ffa9e0;
  --acc-cyan: #08f7fe; --acc-cyan-bright: #70fbff;
  --acc-violet: #7c83ff; --acc-green: #09fbd3; --acc-amber: #f5d300;
  --panel-rgb: 10, 14, 40; --hero-rgb: 16, 22, 60; --ink-rgb: 2, 4, 12; --pop-rgb: 12, 16, 46;
  --pink-rgb: 254, 83, 187; --cyan-rgb: 8, 247, 254; --violet-rgb: 124, 131, 255;
  --green-rgb: 9, 251, 211; --amber-rgb: 245, 211, 0;
  --surface-active: #1f3f9e; --bar-track: #131a44; --bar-tip: #2f48a8; --apply-ink: #050816;
  --heat-1: #121c66; --heat-2: #08f7fe; --heat-3: #fe53bb; --heat-4: #f5d300; --heat-5: #09fbd3;
}
/* volt 荧光青柠 — acid lime on deep green-black */
html[data-theme="volt"] {
  --page-bg: #0c1400; --page-glow: rgba(204, 255, 0, .2);
  --acc-pink: #ccff00; --acc-pink-bright: #dbff57; --acc-pink-soft: #eaff9e;
  --acc-cyan: #00ff9d; --acc-cyan-bright: #52ffbb;
  --acc-violet: #00e5ff; --acc-green: #a8ff3e; --acc-amber: #ffee32;
  --panel-rgb: 18, 32, 6; --hero-rgb: 28, 48, 10; --ink-rgb: 4, 10, 2; --pop-rgb: 16, 28, 6;
  --pink-rgb: 204, 255, 0; --cyan-rgb: 0, 255, 157; --violet-rgb: 0, 229, 255;
  --green-rgb: 168, 255, 62; --amber-rgb: 255, 238, 50;
  --surface-active: #2f5c1a; --bar-track: #12260c; --bar-tip: #2b4f1a; --apply-ink: #0c1400;
  --heat-1: #005c2e; --heat-2: #00ff9d; --heat-3: #ccff00; --heat-4: #ffee32; --heat-5: #ff9e00;
}


/* mist-blue 雾蓝 — light paper blue, calm as a hazy morning sky */
html[data-theme="mist-blue"] {
  color-scheme: light;
  --page-bg: #eef3f7; --page-glow: rgba(96, 145, 185, .13);
  --acc-pink: #6d9bc3; --acc-pink-bright: #5586b0; --acc-pink-soft: #8bb3d1;
  --acc-cyan: #6fa3b8; --acc-cyan-bright: #5b93aa;
  --acc-violet: #94a3c7; --acc-green: #7aa892; --acc-amber: #c2a878;
  --panel-rgb: 252, 254, 255; --hero-rgb: 240, 246, 251; --ink-rgb: 229, 237, 243; --pop-rgb: 248, 251, 253;
  --pink-rgb: 109, 155, 195; --cyan-rgb: 111, 163, 184; --violet-rgb: 148, 163, 199;
  --green-rgb: 122, 168, 146; --amber-rgb: 194, 168, 120;
  --text-main: #2b3a47; --surface-active: #ccdbe6;
  --tx-strong: #46586a; --tx-soft: #6d8093; --tx-dim: #8698a9; --tx-faint: #a3b3c2;
  --tx-mute: #bcc9d4; --amber-mute: #93805c;
  --line-rgb: 205, 218, 228; --veil-rgb: 238, 243, 247;
  --bar-track: #dfe8ef; --bar-tip: #c2d2de; --apply-ink: #ffffff;
  --heat-1: #c9dcea; --heat-2: #9cc3dc; --heat-3: #6d9bc3; --heat-4: #4f7ea8; --heat-5: #33587a;
}
/* indigo-night 靛夜 — soft low-saturation indigo dark, gentle on the eyes */
html[data-theme="indigo-night"] {
  --page-bg: #1b2233; --page-glow: rgba(122, 150, 199, .15);
  --acc-pink: #7d9ecb; --acc-pink-bright: #93b1d8; --acc-pink-soft: #a9c4e3;
  --acc-cyan: #79a8c0; --acc-cyan-bright: #8fbacd;
  --acc-violet: #9a94c9; --acc-green: #83ad9b; --acc-amber: #c9b489;
  --panel-rgb: 30, 38, 57; --hero-rgb: 41, 52, 77; --ink-rgb: 14, 18, 28; --pop-rgb: 27, 34, 52;
  --pink-rgb: 125, 158, 203; --cyan-rgb: 121, 168, 192; --violet-rgb: 154, 148, 201;
  --green-rgb: 131, 173, 155; --amber-rgb: 201, 180, 137;
  --text-main: #e8edf5; --surface-active: #45557a;
  --tx-strong: #d5dde9; --tx-soft: #a6b2c5; --tx-dim: #8996ab; --tx-faint: #6c7889;
  --tx-mute: #525c6e; --amber-mute: #a08c69;
  --line-rgb: 84, 96, 118; --veil-rgb: 8, 11, 17;
  --bar-track: #2b3550; --bar-tip: #48587e; --apply-ink: #ffffff;
  --heat-1: #33405c; --heat-2: #5f7ba6; --heat-3: #7d9ecb; --heat-4: #a8b9d8; --heat-5: #cfdcec;
}
/* latte 拿铁暖白 — warm paper-light, caramel & cream (calm, low glare) */
html[data-theme="latte"] {
  color-scheme: light;
  --page-bg: #f6f0e4; --page-glow: rgba(192, 148, 110, .14);
  --acc-pink: #b98a5e; --acc-pink-bright: #a5713f; --acc-pink-soft: #caa377;
  --acc-cyan: #7f97a5; --acc-cyan-bright: #6c8b9c;
  --acc-violet: #a590a8; --acc-green: #7ba080; --acc-amber: #c9a05f;
  --panel-rgb: 255, 252, 246; --hero-rgb: 248, 242, 232; --ink-rgb: 240, 233, 221; --pop-rgb: 252, 248, 240;
  --pink-rgb: 185, 138, 94; --cyan-rgb: 127, 151, 165; --violet-rgb: 165, 144, 168;
  --green-rgb: 123, 160, 128; --amber-rgb: 201, 160, 95;
  --text-main: #37322a; --surface-active: #d9cdb6;
  --tx-strong: #54493c; --tx-soft: #7d7162; --tx-dim: #94897a; --tx-faint: #b0a695;
  --tx-mute: #c6bca9; --amber-mute: #9c7f52;
  --line-rgb: 214, 204, 188; --veil-rgb: 245, 240, 230;
  --bar-track: #e4dccb; --bar-tip: #cbbfa6; --apply-ink: #ffffff;
  --heat-1: #d9c8a8; --heat-2: #c9a882; --heat-3: #b98a5e; --heat-4: #a5713f; --heat-5: #7a4f2c;
}
/* sage 鼠尾草绿 — soft sage on cool paper */
html[data-theme="sage"] {
  color-scheme: light;
  --page-bg: #eef2ea; --page-glow: rgba(123, 168, 137, .16);
  --acc-pink: #7ba889; --acc-pink-bright: #5f8f6e; --acc-pink-soft: #93bda0;
  --acc-cyan: #7ea3b0; --acc-cyan-bright: #6b92a1;
  --acc-violet: #9b92b5; --acc-green: #6f9a74; --acc-amber: #c7a25f;
  --panel-rgb: 252, 255, 250; --hero-rgb: 244, 248, 240; --ink-rgb: 234, 240, 230; --pop-rgb: 248, 251, 246;
  --pink-rgb: 123, 168, 137; --cyan-rgb: 126, 163, 176; --violet-rgb: 155, 146, 181;
  --green-rgb: 111, 154, 116; --amber-rgb: 199, 162, 95;
  --text-main: #2f352e; --surface-active: #d4dfd0;
  --tx-strong: #4b5647; --tx-soft: #6f7d6d; --tx-dim: #88968a; --tx-faint: #a3b0a5;
  --tx-mute: #b9c3b8; --amber-mute: #8f7647;
  --line-rgb: 210, 218, 206; --veil-rgb: 240, 245, 238;
  --bar-track: #dfe6db; --bar-tip: #c2cfc0; --apply-ink: #ffffff;
  --heat-1: #d5e3d4; --heat-2: #a9c4ae; --heat-3: #7ba889; --heat-4: #5f8f6e; --heat-5: #3f6049;
}
/* matcha 抹茶和纸 — washi paper with matcha green */
html[data-theme="matcha"] {
  color-scheme: light;
  --page-bg: #f4f0e2; --page-glow: rgba(138, 154, 91, .15);
  --acc-pink: #8a9a5b; --acc-pink-bright: #71824a; --acc-pink-soft: #a3b177;
  --acc-cyan: #7e9a8b; --acc-cyan-bright: #6b8978;
  --acc-violet: #a6969f; --acc-green: #95a567; --acc-amber: #d0a259;
  --panel-rgb: 253, 250, 242; --hero-rgb: 245, 241, 230; --ink-rgb: 236, 231, 218; --pop-rgb: 249, 245, 236;
  --pink-rgb: 138, 154, 91; --cyan-rgb: 126, 154, 139; --violet-rgb: 166, 150, 159;
  --green-rgb: 149, 165, 103; --amber-rgb: 208, 162, 89;
  --text-main: #36362c; --surface-active: #dcd5bc;
  --tx-strong: #4d4d3e; --tx-soft: #74745f; --tx-dim: #8d8c76; --tx-faint: #a8a692;
  --tx-mute: #bfbda9; --amber-mute: #93713a;
  --line-rgb: 214, 210, 190; --veil-rgb: 244, 240, 228;
  --bar-track: #e3ddc9; --bar-tip: #c9c1a4; --apply-ink: #ffffff;
  --heat-1: #dcd8b6; --heat-2: #b9bd7f; --heat-3: #8a9a5b; --heat-4: #71824a; --heat-5: #4d5c31;
}
/* dusk 暮云蓝 — calm misty blue-grey (dark, low glare) */
html[data-theme="dusk"] {
  --page-bg: #222936; --page-glow: rgba(140, 168, 201, .14);
  --acc-pink: #8fa8c9; --acc-pink-bright: #7697bd; --acc-pink-soft: #aec2db;
  --acc-cyan: #7fb2c4; --acc-cyan-bright: #6fa3b6;
  --acc-violet: #a191c4; --acc-green: #86b39a; --acc-amber: #c9b283;
  --panel-rgb: 34, 42, 58; --hero-rgb: 46, 56, 76; --ink-rgb: 16, 21, 30; --pop-rgb: 30, 38, 54;
  --pink-rgb: 143, 168, 201; --cyan-rgb: 127, 178, 196; --violet-rgb: 161, 145, 196;
  --green-rgb: 134, 179, 154; --amber-rgb: 201, 178, 131;
  --text-main: #eceff4; --surface-active: #4a5a7a;
  --tx-strong: #d8dee8; --tx-soft: #a9b2c2; --tx-dim: #8c96a8; --tx-faint: #6e7889;
  --tx-mute: #545d6d; --amber-mute: #a6906a;
  --line-rgb: 86, 96, 116; --veil-rgb: 10, 13, 18;
  --bar-track: #303c54; --bar-tip: #4d5d7e; --apply-ink: #ffffff;
  --heat-1: #33405c; --heat-2: #6d8cad; --heat-3: #a3bad6; --heat-4: #d4c59e; --heat-5: #b58a6e;
}
/* cocoa 可可陶土 — dark cocoa with terracotta & sand */
html[data-theme="cocoa"] {
  --page-bg: #282019; --page-glow: rgba(201, 141, 109, .15);
  --acc-pink: #c98d6d; --acc-pink-bright: #b37758; --acc-pink-soft: #d8a587;
  --acc-cyan: #a89a86; --acc-cyan-bright: #968a76;
  --acc-violet: #ad90a0; --acc-green: #a3a06c; --acc-amber: #d9b37a;
  --panel-rgb: 46, 36, 28; --hero-rgb: 60, 48, 38; --ink-rgb: 20, 15, 11; --pop-rgb: 42, 32, 25;
  --pink-rgb: 201, 141, 109; --cyan-rgb: 168, 154, 134; --violet-rgb: 173, 144, 160;
  --green-rgb: 163, 160, 108; --amber-rgb: 217, 179, 122;
  --text-main: #f1eae2; --surface-active: #6e5540;
  --tx-strong: #ddd1c4; --tx-soft: #ab9d8d; --tx-dim: #8e8070; --tx-faint: #6f6355;
  --tx-mute: #564c40; --amber-mute: #a3875c;
  --line-rgb: 96, 84, 72; --veil-rgb: 12, 9, 7;
  --bar-track: #443629; --bar-tip: #6d5843; --apply-ink: #ffffff;
  --heat-1: #5c4230; --heat-2: #8a5f43; --heat-3: #c98d6d; --heat-4: #d9b37a; --heat-5: #ecd9b2;
}
/* graphite 石墨 — clean dark, Apple-like neutral surfaces with vivid accents */
html[data-theme="graphite"] {
  --page-bg: #17171a; --page-glow: rgba(10, 132, 255, .16);
  --acc-pink: #ff375f; --acc-pink-bright: #ff6482; --acc-pink-soft: #ff9aa8;
  --acc-cyan: #0a84ff; --acc-cyan-bright: #409cff;
  --acc-violet: #bf5af2; --acc-green: #30d158; --acc-amber: #ffd60a;
  --panel-rgb: 32, 32, 36; --hero-rgb: 44, 44, 50; --ink-rgb: 12, 12, 14; --pop-rgb: 28, 28, 32;
  --pink-rgb: 255, 55, 95; --cyan-rgb: 10, 132, 255; --violet-rgb: 191, 90, 242;
  --green-rgb: 48, 209, 88; --amber-rgb: 255, 214, 10;
  --text-main: #f5f5f7; --surface-active: #3a3a3c;
  --tx-strong: #e8e8ed; --tx-soft: #aeaeb2; --tx-dim: #98989d; --tx-faint: #7c7c80;
  --tx-mute: #55555a; --amber-mute: #d0a53e;
  --line-rgb: 120, 120, 128; --veil-rgb: 0, 0, 0;
  --bar-track: #2c2c2e; --bar-tip: #48484e; --apply-ink: #ffffff; --heat-cold: #0a84ff;
  --heat-1: #284f8f; --heat-2: #0a84ff; --heat-3: #30d158; --heat-4: #ffd60a; --heat-5: #ff375f;
}
/* starlight 星光 — a light Apple-like theme */
html[data-theme="starlight"] {
  --page-bg: #f5f5f7; --page-glow: rgba(10, 132, 255, .10);
  color-scheme: light;
  --acc-pink: #ff375f; --acc-pink-bright: #e8304f; --acc-pink-soft: #fa5a77;
  --acc-cyan: #007aff; --acc-cyan-bright: #0a84ff;
  --acc-violet: #af52de; --acc-green: #34c759; --acc-amber: #ff9f0a;
  --panel-rgb: 255, 255, 255; --hero-rgb: 244, 245, 248; --ink-rgb: 233, 234, 238;
  --pop-rgb: 250, 250, 252; --pink-rgb: 255, 55, 95; --cyan-rgb: 0, 122, 255;
  --violet-rgb: 175, 82, 222; --green-rgb: 52, 199, 89; --amber-rgb: 255, 159, 10;
  --text-main: #1d1d1f; --surface-active: #e5e5ea;
  --tx-strong: #3a3a3c; --tx-soft: #6e6e73; --tx-dim: #86868b; --tx-faint: #a1a1a6;
  --tx-mute: #b8b8bd; --amber-mute: #9a6a1f;
  --line-rgb: 209, 209, 214; --veil-rgb: 235, 235, 240;
  --bar-track: #e2e2e6; --bar-tip: #c7c7cc; --apply-ink: #ffffff; --heat-cold: #007aff;
  --heat-1: #64b5f6; --heat-2: #42a5f5; --heat-3: #66bb6a; --heat-4: #ffca28; --heat-5: #ff5252;
}
/* Apple-ish UI details: system font stack, quiet scrollbars, focus rings */
html { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI Variable", "Segoe UI", Inter, ui-sans-serif, system-ui, sans-serif; }
html[data-theme="starlight"] ::-webkit-scrollbar { width: 10px; }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { border: 3px solid transparent; border-radius: 99px; background: rgba(var(--line-rgb), .55); background-clip: content-box; }
::-webkit-scrollbar-thumb:hover { background: rgba(var(--line-rgb), .8); background-clip: content-box; }
::-webkit-scrollbar-track { background: transparent; }
button:focus-visible, input:focus-visible, [tabindex]:focus-visible { outline: 2px solid rgba(var(--cyan-rgb), .6); outline-offset: 2px; }
html[data-theme="starlight"] input[type="date"] { color-scheme: light; }
/* light theme fixes for text that was tuned for dark surfaces */
html[data-theme="starlight"] .theme-option:hover, html[data-theme="starlight"] .ks-style:hover, html[data-theme="starlight"] .record-button { color: #1d1d1f; }
html[data-theme="starlight"] .theme-option.active, html[data-theme="starlight"] .ks-style.active { color: #1d1d1f; }
html[data-theme="starlight"] .keycap span, html[data-theme="starlight"] .keycap b { color: rgba(255,255,255,.92); }
html[data-theme="starlight"] .date-popover-title, html[data-theme="starlight"] .keyshow-popover-title, html[data-theme="starlight"] .theme-popover-title { color: #1d1d1f; }
html[data-theme="starlight"] .mouse-shape { background: linear-gradient(160deg, rgba(var(--cyan-rgb), .12), rgba(var(--violet-rgb), .10)); }
html[data-theme="starlight"] .cap { background: rgba(255,255,255,.85); color: #1d1d1f; }
html[data-theme="starlight"] .keyshow-hint { color: #48484a; background: rgba(255,255,255,.8); }
* { box-sizing: border-box; } body { margin: 0; min-width: 320px; min-height: 100vh; background: var(--page-bg); } button { font: inherit; }
html.keyshow-window, html.keyshow-window body { background: transparent !important; }
</style>

<style scoped>
.mini-host { margin: 0; min-height: 100vh; background: transparent; }
.app-shell { position: relative; min-height: 100vh; overflow: hidden; padding: 34px clamp(22px, 5vw, 76px) 28px; background: radial-gradient(circle at 86% 6%, var(--page-glow), transparent 29%), var(--page-bg); }
.ambient { position: absolute; pointer-events: none; border-radius: 50%; filter: blur(8px); }.ambient-one { width: 320px; height: 320px; right: -130px; top: 260px; background: var(--acc-pink); opacity: .08; }.ambient-two { width: 240px; height: 240px; left: -120px; bottom: 160px; background: var(--acc-cyan); opacity: .08; }
.topbar, .hero-row, .stat-grid, .content-grid, .timeline-panel, .footer-note { position: relative; z-index: 1; max-width: 1480px; margin-inline: auto; }.topbar, .hero-row { display: flex; align-items: center; justify-content: space-between; gap: 24px; }.topbar { margin-bottom: 82px; }.brand-lockup, .topbar-actions, .range-switch, .legend, .keyboard-footer, .mouse-content, .timeline-note { display: flex; align-items: center; }.brand-lockup { gap: 13px; }.brand-mark { width: 34px; height: 34px; display: flex; align-items: end; justify-content: center; gap: 3px; padding: 6px; border-radius: 11px; transform: rotate(-8deg); background: linear-gradient(135deg, var(--acc-pink), var(--acc-violet)); box-shadow: 0 8px 24px rgba(var(--pink-rgb),.23); }.brand-mark span { display: block; width: 5px; border-radius: 5px; background: #fff; }.brand-mark span:nth-child(1) { height: 11px; opacity: .75; }.brand-mark span:nth-child(2) { height: 18px; }.brand-mark span:nth-child(3) { height: 14px; opacity: .85; }
.eyebrow { margin: 0; color: var(--tx-faint); font-size: 10px; font-weight: 800; letter-spacing: .18em; line-height: 1.3; }.eyebrow.accent { color: var(--acc-pink-soft); } h1, h2, h3, p { margin-top: 0; } h1 { margin-bottom: 0; font-size: 19px; line-height: 1; letter-spacing: -.04em; } h1 span { color: var(--acc-pink-bright); }.topbar-actions { gap: 12px; }
.demo-chip, .record-button, .avatar-button, .range-switch, .panel-kicker { border: 1px solid rgba(var(--line-rgb),.15); background: rgba(var(--panel-rgb),.55); }.demo-chip { display: flex; align-items: center; gap: 8px; padding: 9px 13px; border-radius: 999px; color: var(--tx-soft); font-size: 11px; }.demo-chip i, .live-indicator { width: 7px; height: 7px; border-radius: 50%; background: var(--acc-green); box-shadow: 0 0 0 4px rgba(var(--green-rgb),.11), 0 0 14px var(--acc-green); }.demo-chip.warning { color: var(--acc-amber); border-color: rgba(var(--amber-rgb),.3); }.demo-chip.warning i { background: var(--acc-amber); box-shadow: 0 0 0 4px rgba(var(--amber-rgb),.12), 0 0 14px var(--acc-amber); }.record-button { display: flex; align-items: center; gap: 8px; padding: 9px 13px; border-radius: 999px; color: var(--tx-strong); cursor: pointer; font-size: 11px; transition: .2s ease; }.record-button:hover:not(:disabled) { border-color: rgba(var(--cyan-rgb),.7); transform: translateY(-1px); }.record-button.paused { color: var(--tx-soft); }.record-button:disabled { cursor: not-allowed; opacity: .55; }.record-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--acc-pink); box-shadow: 0 0 12px var(--acc-pink); }.paused .record-dot { background: #64748b; box-shadow: none; }.avatar-button { width: 34px; height: 34px; border-radius: 50%; color: #fff; font-size: 10px; font-weight: 800; cursor: pointer; background: linear-gradient(135deg, var(--acc-cyan), var(--acc-violet)); } .theme-control { position: relative; }.theme-button { display: flex; align-items: center; gap: 4px; height: 34px; padding: 0 11px; border: 1px solid rgba(var(--line-rgb),.15); border-radius: 999px; background: rgba(var(--panel-rgb),.55); cursor: pointer; }.theme-button .theme-dot { display: block; width: 7px; height: 7px; border-radius: 50%; }.theme-button:hover { border-color: rgba(var(--cyan-rgb),.7); transform: translateY(-1px); }.theme-popover { position: absolute; z-index: 8; top: calc(100% + 10px); right: 0; width: 190px; padding: 15px; border: 1px solid rgba(var(--cyan-rgb),.22); border-radius: 14px; background: rgba(var(--pop-rgb),.98); box-shadow: 0 18px 42px rgba(0,0,0,.35); }.theme-popover-title { margin: 0 0 11px; color: var(--text-main); font-size: 12px; font-weight: 800; }.theme-option { display: flex; align-items: center; gap: 10px; width: 100%; margin-top: 4px; padding: 8px 9px; border: 1px solid transparent; border-radius: 9px; color: var(--tx-soft); background: transparent; cursor: pointer; font-size: 11px; text-align: left; transition: .15s ease; }.theme-option:hover { color: #fff; background: rgba(var(--line-rgb),.08); }.theme-option.active { color: #fff; border-color: rgba(var(--cyan-rgb),.45); background: rgba(var(--cyan-rgb),.1); }.theme-dots { display: flex; align-items: center; gap: 3px; }.theme-dots i { width: 8px; height: 8px; border-radius: 50%; display: block; } .keyshow-control { position: relative; }.keyshow-button { display: flex; align-items: center; gap: 6px; height: 34px; padding: 0 10px; border: 1px solid rgba(var(--line-rgb),.15); border-radius: 999px; background: rgba(var(--panel-rgb),.55); cursor: pointer; color: var(--tx-faint); transition: border-color .2s ease, color .2s ease; }.keyshow-button i { font-style: normal; font-size: 14px; }.keyshow-button:hover { border-color: rgba(var(--cyan-rgb),.7); color: #fff; }.keyshow-button.on { border-color: rgba(var(--green-rgb),.65); color: var(--text-main); box-shadow: 0 0 14px rgba(var(--green-rgb),.25); }.keyshow-led { width: 6px; height: 6px; border-radius: 50%; background: #64748b; }.keyshow-button.on .keyshow-led { background: var(--acc-green); box-shadow: 0 0 8px var(--acc-green); }.keyshow-popover { position: absolute; z-index: 8; top: calc(100% + 10px); right: 0; width: 236px; padding: 15px; border: 1px solid rgba(var(--cyan-rgb),.22); border-radius: 14px; background: rgba(var(--pop-rgb),.98); box-shadow: 0 18px 42px rgba(0,0,0,.35); }.keyshow-popover-title { margin: 0 0 11px; color: var(--text-main); font-size: 12px; font-weight: 800; }.keyshow-master { display: flex; align-items: center; justify-content: space-between; gap: 10px; width: 100%; padding: 10px 11px; border: 1px solid rgba(var(--line-rgb),.16); border-radius: 11px; color: var(--tx-soft); background: rgba(var(--ink-rgb),.4); cursor: pointer; text-align: left; }.keyshow-master.on { border-color: rgba(var(--green-rgb),.55); background: rgba(var(--green-rgb),.08); }.ks-master-text b, .ks-master-text small { display: block; }.ks-master-text b { color: var(--tx-strong); font-size: 12px; }.keyshow-master.on .ks-master-text b { color: var(--acc-green); }.ks-master-text small { margin-top: 3px; color: var(--tx-faint); font-size: 9px; }.ks-switch { position: relative; flex: 0 0 34px; height: 18px; border-radius: 99px; background: #263452; transition: background .2s ease; }.ks-switch i { position: absolute; top: 3px; left: 3px; width: 12px; height: 12px; border-radius: 50%; background: #94a3b8; transition: all .2s ease; }.keyshow-master.on .ks-switch { background: rgba(var(--green-rgb),.5); }.keyshow-master.on .ks-switch i { left: 19px; background: var(--acc-green); box-shadow: 0 0 8px var(--acc-green); }.ks-styles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-top: 4px; }.ks-style { display: flex; flex-direction: column; align-items: center; gap: 5px; width: 100%; padding: 9px 6px; border: 1px solid rgba(var(--line-rgb),.14); border-radius: 11px; color: var(--tx-soft); background: rgba(var(--ink-rgb),.28); cursor: pointer; text-align: center; transition: all .15s ease; }.ks-style:active { transform: scale(.96); }.ks-style:hover { border-color: rgba(var(--cyan-rgb),.5); background: rgba(var(--ink-rgb),.45); }.ks-style.active { border-color: rgba(var(--cyan-rgb),.6); background: rgba(var(--cyan-rgb),.12); box-shadow: 0 0 12px rgba(var(--cyan-rgb),.12); }.ks-style-icon { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 9px; color: var(--text-main); background: linear-gradient(135deg, rgba(var(--cyan-rgb),.4), rgba(var(--violet-rgb),.4)); font-style: normal; font-size: 15px; }.ks-style-text b, .ks-style-text small { display: block; }.ks-style-text b { color: var(--tx-strong); font-size: 10px; }.ks-style-text small { margin-top: 2px; color: var(--tx-faint); font-size: 8px; line-height: 1.4; }.ks-style.active .ks-style-text b { color: var(--text-main); }.ks-note { margin: 11px 0 0; padding-top: 10px; border-top: 1px dashed rgba(var(--line-rgb),.16); color: var(--tx-faint); font-size: 9px; line-height: 1.55; }
.ks-modal-backdrop { position: fixed; z-index: 30; inset: 0; display: grid; place-items: start center; padding: max(24px, 8vh) 22px 22px; background: rgba(var(--veil-rgb),.55); backdrop-filter: blur(6px); }
.ks-modal { width: min(100%, 460px); max-height: calc(100vh - max(28px, 8vh) - 46px); overflow: auto; padding: 24px; border: 1px solid rgba(var(--cyan-rgb), .22); border-radius: 20px; background: linear-gradient(145deg, rgba(var(--panel-rgb), .98), rgba(var(--pop-rgb), .98)); box-shadow: 0 24px 70px rgba(0, 0, 0, .4); }
.ks-modal-head { display: flex; align-items: start; justify-content: space-between; gap: 14px; margin-bottom: 16px; }
.ks-modal h3 { margin: 4px 0 0; font-size: 20px; letter-spacing: -.04em; }
.ks-modal-close { width: 30px; height: 30px; border: 1px solid rgba(var(--line-rgb),.2); border-radius: 50%; color: var(--tx-soft); background: rgba(var(--line-rgb),.1); cursor: pointer; font-size: 19px; line-height: 1; }
.ks-modal-close:hover { color: #fff; border-color: rgba(var(--cyan-rgb), .6); }
.ks-layout-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 4px; }
.settings-button { display: grid; place-items: center; flex: 0 0 auto; width: 36px; height: 36px; border: 1px solid rgba(var(--line-rgb), .2); border-radius: 999px; background: rgba(var(--panel-rgb), .6); color: var(--tx-faint); cursor: pointer; font-size: 16px; transition: all .25s ease; }
.settings-button:hover { border-color: rgba(var(--cyan-rgb), .8); color: var(--text-main); transform: rotate(90deg) scale(1.05); box-shadow: 0 0 16px rgba(var(--cyan-rgb), .25); }
.ks-section-title { display: flex; align-items: center; gap: 7px; margin: 16px 0 9px; padding-top: 10px; border-top: 1px dashed rgba(var(--line-rgb), .18); color: var(--tx-faint); font-size: 9px; font-weight: 800; letter-spacing: .12em; }.ks-section-title::before { content: ""; flex: 0 0 auto; width: 4px; height: 10px; border-radius: 2px; background: linear-gradient(180deg, var(--acc-cyan), var(--acc-violet)); }
.settings-themes { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; }
.setting-theme { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border: 1px solid rgba(var(--line-rgb),.15); border-radius: 10px; color: var(--tx-soft); background: rgba(var(--ink-rgb),.35); cursor: pointer; font-size: 11px; text-align: left; transition: all .15s ease; }
.setting-theme:hover { border-color: rgba(var(--cyan-rgb),.5); color: #fff; }
.setting-theme.active { border-color: rgba(var(--cyan-rgb),.65); color: #fff; background: rgba(var(--cyan-rgb),.1); }
.ks-range { display: flex; align-items: center; gap: 8px; width: 100%; padding: 9px 10px; border: 1px solid rgba(var(--line-rgb),.14); border-radius: 10px; background: rgba(var(--ink-rgb),.35); }
.ks-range input[type="range"] { flex: 1; accent-color: var(--acc-cyan); cursor: pointer; }
.ks-range span { color: var(--tx-soft); font-size: 10px; font-weight: 700; min-width: 30px; text-align: right; }
.ks-drag-toggle { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; padding: 8px 10px; border: 1px solid rgba(var(--line-rgb),.14); border-radius: 10px; color: var(--tx-soft); background: rgba(var(--ink-rgb),.35); cursor: pointer; text-align: left; }
.ks-drag-toggle:active { transform: scale(.98); }
.ks-drag-toggle.on { border-color: rgba(var(--amber-rgb),.45); background: rgba(var(--amber-rgb),.07); }
.ks-drag-toggle .ks-master-text b { font-size: 10px; }
.ks-drag-toggle.on .ks-master-text b { color: var(--acc-amber); }
.ks-drag-toggle .ks-master-text small { font-size: 8px; }
.ks-data { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.ks-behavior-row { margin-bottom: 8px; }
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

.ks-radio-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.ks-radio-label { flex: 0 0 52px; color: var(--tx-faint); font-size: 10px; font-weight: 700; }
.ks-radios { display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; flex: 1; }
.ks-radio { padding: 7px 0; border: 1px solid rgba(var(--line-rgb), .2); border-radius: 9px; color: var(--tx-soft); background: rgba(var(--ink-rgb), .3); cursor: pointer; font-size: 10px; }
.ks-radio:hover { border-color: rgba(var(--cyan-rgb), .55); color: var(--text-main); }
.ks-radio.active { border-color: rgba(var(--cyan-rgb), .7); color: #fff; background: rgba(var(--cyan-rgb), .16); }
html[data-theme="starlight"] .ks-radio.active, html[data-theme="latte"] .ks-radio.active, html[data-theme="sage"] .ks-radio.active, html[data-theme="matcha"] .ks-radio.active { color: #1d1d1f; }

.ks-data-opt { padding: 9px 10px; border: 1px solid rgba(var(--line-rgb), .28); border-radius: 10px; color: var(--tx-soft); background: rgba(var(--ink-rgb), .35); cursor: pointer; text-align: left; }
.ks-data-opt b, .ks-data-opt small { display: block; }
.ks-data-opt b { color: var(--tx-strong); font-size: 11px; }
.ks-data-opt small { margin-top: 3px; color: var(--tx-faint); font-size: 8px; line-height: 1.5; }
.ks-data-opt.active { border-color: rgba(var(--cyan-rgb), .6); background: rgba(var(--cyan-rgb), .1); }
.ks-data-opt.active b { color: var(--acc-cyan-bright); }
.ks-data-path { margin: 10px 0 0; color: var(--tx-faint); font-size: 9px; }
.ks-data-path code { display: inline-block; max-width: 100%; overflow-wrap: anywhere; color: var(--tx-soft); font-family: ui-monospace, Consolas, monospace; font-size: 9px; }
.ks-data-notice { margin: 8px 0 0; padding: 8px 10px; border-radius: 8px; color: var(--acc-amber); background: rgba(var(--amber-rgb), .08); font-size: 9px; line-height: 1.5; }
.ks-custom-hint { display: block; margin-top: 4px; color: var(--tx-faint); font-size: 8px; line-height: 1.5; overflow-wrap: anywhere; }
.beat-dot { position: fixed; z-index: 45; right: 18px; bottom: 16px; width: 10px; height: 10px; border-radius: 50%; background: var(--acc-pink); box-shadow: 0 0 12px var(--acc-pink); }
.beat-pop-enter-active { animation: beat-pulse .24s ease; }
.beat-pop-leave-active { display: none; }
@keyframes beat-pulse { 0% { transform: scale(.4); opacity: 1; } 100% { transform: scale(1.6); opacity: .2; } }

.ks-sound-row { display: flex; flex-direction: column; gap: 6px; }
.ks-select { width: 100%; padding: 7px 9px; border: 1px solid rgba(var(--line-rgb), .25); border-radius: 9px; color: var(--tx-strong); background: rgba(var(--ink-rgb), .35); font-size: 11px; cursor: pointer; }
.ks-range.compact { padding: 5px 8px; }
.achievement-toast { position: fixed; z-index: 40; right: 22px; bottom: 26px; display: flex; align-items: center; gap: 10px; max-width: 320px; padding: 12px 16px; border: 1px solid rgba(var(--amber-rgb), .4); border-radius: 14px; background: rgba(var(--pop-rgb), .92); backdrop-filter: blur(14px); box-shadow: 0 16px 44px rgba(0, 0, 0, .3); }
.achievement-toast > span { font-size: 20px; }
.achievement-toast b, .achievement-toast small { display: block; }
.achievement-toast b { color: var(--text-main); font-size: 12px; }
.achievement-toast small { margin-top: 3px; color: var(--tx-soft); font-size: 11px; line-height: 1.45; }
.toast-pop-enter-active { transition: all .35s cubic-bezier(.2, 1.4, .4, 1); }
.toast-pop-leave-active { transition: all .25s ease; }
.toast-pop-enter-from, .toast-pop-leave-to { opacity: 0; transform: translateY(16px) scale(.92); }
.footprint-button { border: 0; padding: 0 10px; color: var(--tx-faint); background: transparent; cursor: pointer; font-size: 10px; }
.footprint-button:hover { color: var(--acc-pink-soft); }
.pk-launch:hover { color: var(--acc-cyan-bright); }



.ks-layout-col .ks-layout-title { margin-top: 0; }
.keyshow-master { display: flex; align-items: center; justify-content: space-between; gap: 10px; width: 100%; padding: 11px 12px; border: 1px solid rgba(var(--line-rgb),.16); border-radius: 12px; color: var(--tx-soft); background: rgba(var(--ink-rgb),.4); cursor: pointer; text-align: left; }
.keyshow-master.on { border-color: rgba(var(--green-rgb),.55); background: rgba(var(--green-rgb),.08); }
.ks-master-text b, .ks-master-text small { display: block; }
.ks-master-text b { color: var(--tx-strong); font-size: 12px; }
.keyshow-master.on .ks-master-text b { color: var(--acc-green); }
.ks-master-text small { margin-top: 3px; color: var(--tx-faint); font-size: 9px; }
.ks-switch { position: relative; flex: 0 0 38px; height: 20px; border-radius: 99px; background: #263452; transition: background .2s ease; }
.ks-switch i { position: absolute; top: 3px; left: 3px; width: 14px; height: 14px; border-radius: 50%; background: #94a3b8; transition: all .2s ease; }
.keyshow-master.on .ks-switch { background: rgba(var(--green-rgb),.5); }
.keyshow-master.on .ks-switch i, .ks-drag-toggle.on .ks-switch i { left: 21px; background: var(--acc-green); box-shadow: 0 0 8px var(--acc-green); }
 .keyshow-popover { width: 272px; }.ks-layout-title { margin: 12px 0 6px; color: var(--tx-faint); font-size: 9px; font-weight: 800; letter-spacing: .08em; }.ks-positions { display: grid; grid-template-columns: repeat(6, 1fr); gap: 5px; }.ks-pos { position: relative; height: 30px; border: 1px solid rgba(var(--line-rgb),.15); border-radius: 7px; background: rgba(var(--ink-rgb),.4); cursor: pointer; }.ks-pos:hover { border-color: rgba(var(--cyan-rgb),.5); }.ks-pos.active { border-color: rgba(var(--cyan-rgb),.65); background: rgba(var(--cyan-rgb),.12); box-shadow: 0 0 10px rgba(var(--cyan-rgb),.18); }.ks-pos i { position: absolute; width: 5px; height: 5px; border-radius: 50%; background: var(--tx-faint); transform: translate(-50%, -50%); }.ks-pos.active i { background: var(--acc-cyan); box-shadow: 0 0 6px var(--acc-cyan); }.ks-sizes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; }.ks-size { padding: 6px 0; border: 1px solid rgba(var(--line-rgb),.15); border-radius: 7px; color: var(--tx-soft); background: rgba(var(--ink-rgb),.4); cursor: pointer; font-size: 10px; font-weight: 700; }.ks-size:hover { border-color: rgba(var(--cyan-rgb),.5); color: #fff; }.ks-size.active { border-color: rgba(var(--cyan-rgb),.65); color: #fff; background: rgba(var(--cyan-rgb),.14); }
.hero-row { align-items: end; margin-bottom: 35px; } h2 { margin-bottom: 13px; font-size: clamp(34px,4vw,58px); line-height: 1.05; letter-spacing: -.065em; } h2 em { color: var(--acc-pink-bright); font-style: normal; }.hero-copy { margin-bottom: 0; color: var(--tx-faint); font-size: 14px; }.range-control { position: relative; }.range-switch { gap: 3px; padding: 4px; border-radius: 13px; }.range-switch button { border: 0; padding: 9px 15px; border-radius: 9px; color: var(--tx-faint); background: transparent; cursor: pointer; font-size: 12px; }.range-switch button:hover { color: var(--text-main); }.range-switch button.active { color: #fff; background: var(--surface-active); box-shadow: 0 5px 13px rgba(0,0,0,.15); }.range-switch .calendar-button { padding-inline: 12px; color: var(--acc-cyan); }.date-popover { position: absolute; z-index: 5; top: calc(100% + 10px); right: 0; width: 252px; padding: 16px; border: 1px solid rgba(var(--cyan-rgb),.22); border-radius: 15px; background: rgba(var(--pop-rgb),.98); box-shadow: 0 18px 42px rgba(0,0,0,.35); }.date-popover-title { margin: 0 0 13px; color: var(--text-main); font-size: 12px; font-weight: 800; }.date-popover label { display: flex; flex-direction: column; gap: 6px; margin-top: 10px; color: var(--tx-dim); font-size: 10px; }.date-popover input { width: 100%; border: 1px solid rgba(var(--line-rgb),.2); border-radius: 8px; padding: 8px 9px; color: var(--text-main); background: rgba(var(--ink-rgb),.72); color-scheme: dark; font-size: 11px; }.date-popover input:focus { outline: 2px solid rgba(var(--cyan-rgb),.45); outline-offset: 1px; }.date-error { margin: 10px 0 0; color: var(--acc-pink-soft); font-size: 10px; }.date-popover-actions { display: flex; justify-content: end; gap: 8px; margin-top: 15px; }.date-popover-actions button { border: 0; border-radius: 8px; padding: 8px 10px; cursor: pointer; font-size: 10px; }.date-cancel { color: var(--tx-soft); background: rgba(var(--line-rgb),.12); }.date-apply { color: var(--apply-ink); background: var(--acc-cyan); font-weight: 800; }.date-apply:hover { background: var(--acc-cyan-bright); }
.runtime-warning { position: relative; z-index: 1; display: flex; align-items: center; gap: 10px; max-width: 1480px; margin: -54px auto 35px; padding: 11px 14px; border: 1px solid rgba(var(--amber-rgb),.28); border-radius: 12px; color: var(--acc-amber); background: rgba(84,64,31,.3); }.runtime-warning > span { display: grid; place-items: center; width: 18px; height: 18px; border-radius: 50%; color: #17120a; background: var(--acc-amber); font-size: 11px; font-weight: 900; }.runtime-warning b, .runtime-warning small { display: block; }.runtime-warning b { font-size: 11px; }.runtime-warning small { margin-top: 3px; color: var(--amber-mute); font-size: 10px; }
.privacy-backdrop { position: fixed; z-index: 20; inset: 0; display: grid; place-items: start center; padding: max(24px, 9vh) 22px 22px; background: rgba(var(--veil-rgb),.72); backdrop-filter: blur(8px); }.privacy-dialog { width: min(100%, 520px); max-height: calc(100vh - max(28px, 9vh) - 46px); overflow: auto; padding: 26px; border: 1px solid rgba(var(--cyan-rgb),.25); border-radius: 20px; background: linear-gradient(145deg, #192956, #101a39); box-shadow: 0 28px 80px rgba(0,0,0,.45); }.privacy-dialog-heading { display: flex; align-items: start; justify-content: space-between; gap: 18px; }.privacy-dialog h3 { margin: 5px 0 0; font-size: 22px; letter-spacing: -.05em; }.privacy-close { width: 30px; height: 30px; border: 1px solid rgba(var(--line-rgb),.2); border-radius: 50%; color: var(--tx-soft); background: rgba(var(--line-rgb),.1); cursor: pointer; font-size: 20px; line-height: 1; }.privacy-close:hover { color: #fff; border-color: rgba(var(--cyan-rgb),.65); }.privacy-intro { margin: 22px 0 18px; color: var(--tx-soft); font-size: 13px; line-height: 1.65; }.privacy-points { display: grid; gap: 10px; }.privacy-points article { display: grid; grid-template-columns: 29px 1fr; gap: 11px; padding: 13px; border: 1px solid rgba(var(--line-rgb),.13); border-radius: 12px; background: rgba(var(--ink-rgb),.28); }.privacy-points article > span { color: var(--acc-cyan); font-size: 10px; font-weight: 900; }.privacy-points b, .privacy-points small { display: block; }.privacy-points b { margin-bottom: 4px; color: var(--text-main); font-size: 11px; }.privacy-points small { color: var(--tx-faint); font-size: 10px; line-height: 1.55; }.privacy-notice { display: grid; gap: 5px; margin-top: 14px; padding: 13px; border-left: 3px solid var(--acc-amber); color: var(--amber-mute); background: rgba(var(--amber-rgb),.07); font-size: 10px; line-height: 1.55; }.privacy-notice b { color: var(--acc-amber); }.privacy-storage { display: grid; gap: 6px; margin-top: 17px; color: var(--tx-faint); font-size: 9px; }.privacy-storage code { overflow-wrap: anywhere; color: var(--tx-soft); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 9px; }
.stat-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 15px; }.stat-card, .panel { border: 1px solid rgba(var(--line-rgb),.13); background: linear-gradient(145deg,rgba(var(--panel-rgb),.86),rgba(var(--ink-rgb),.9)); box-shadow: 0 20px 50px rgba(0,0,0,.13); }.stat-card { position: relative; min-height: 168px; padding: 22px 23px; overflow: hidden; border-radius: 18px; }.stat-card::after { position: absolute; content: ""; right: -37px; bottom: -45px; width: 135px; height: 135px; border: 1px solid rgba(var(--cyan-rgb),.1); border-radius: 50%; }.stat-card-primary { background: linear-gradient(140deg,rgba(var(--hero-rgb),.97),rgba(var(--panel-rgb),.8)); }.highlight-card { background: linear-gradient(140deg,rgba(var(--pink-rgb),.55),rgba(var(--panel-rgb),.86)); }.card-icon { display: grid; place-items: center; width: 30px; height: 30px; margin-bottom: 19px; border-radius: 9px; font-size: 14px; }.icon-spark { color: var(--acc-amber); background: rgba(var(--amber-rgb),.14); }.icon-mouse { color: var(--acc-cyan); background: rgba(52,217,255,.13); }.icon-time { color: var(--acc-violet); background: rgba(var(--violet-rgb),.14); }.icon-top { color: var(--acc-pink-soft); background: rgba(var(--pink-rgb),.14); }.stat-card p { margin-bottom: 5px; color: var(--tx-dim); font-size: 11px; }.stat-card strong { display: block; margin-bottom: 11px; font-size: 28px; letter-spacing: -.05em; }.unit { margin-left: 2px; color: var(--tx-dim); font-size: 14px; font-weight: 500; letter-spacing: 0; }.trend { font-size: 11px; }.trend small { margin-left: 5px; color: var(--tx-faint); }.trend.up { color: var(--acc-green); }.trend.neutral { color: var(--tx-dim); }.accent-text { color: var(--acc-pink-soft); }
.content-grid { display: grid; grid-template-columns: minmax(0,1.8fr) minmax(300px,.85fr); gap: 15px; margin-bottom: 15px; }.panel { border-radius: 18px; }.keyboard-panel { container-type: inline-size; padding: 27px 28px 20px; overflow: hidden; }.panel-heading { display: flex; align-items: start; justify-content: space-between; gap: 18px; margin-bottom: 28px; }.panel-heading.compact { align-items: center; margin-bottom: 22px; }.panel h3 { margin: 5px 0 0; font-size: 19px; letter-spacing: -.04em; }.legend { gap: 9px; color: var(--tx-faint); font-size: 10px; }.legend-gradient { display: block; width: 75px; height: 6px; border-radius: 99px; background: linear-gradient(90deg,var(--heat-1),var(--heat-2),var(--heat-3),var(--heat-4),var(--heat-5)); }
.keyboard-wrap { display: flex; gap: 1.2cqw; padding: 1.6cqw 1.4cqw; border-radius: 1.4cqw; background: rgba(var(--ink-rgb),.42); }.kb-main { display: flex; flex-direction: column; gap: .9cqw; flex: 1 1 auto; min-width: 0; }.keyboard-row { display: flex; gap: .7cqw; min-height: 5.1cqw; }.keycap { display: flex; min-width: 0; flex-direction: column; justify-content: space-between; padding: .9cqw .8cqw .7cqw; border: 1px solid color-mix(in srgb,var(--key-color),white 18%); border-radius: .8cqw; color: #fff; background: linear-gradient(145deg,color-mix(in srgb,var(--key-color),white 9%),var(--key-color)); box-shadow: inset 0 1px rgba(255,255,255,.15),0 5px 10px rgba(0,0,0,.17); transition: transform .18s ease,filter .18s ease; }.keycap:hover { z-index: 2; filter: brightness(1.16); transform: translateY(-4px) scale(1.04); }.keycap span { overflow: hidden; white-space: nowrap; color: rgba(255,255,255,.78); font-size: clamp(5px,.92cqw,9.5px); font-weight: 700; text-overflow: clip; letter-spacing: -.01em; }.keycap b { overflow: hidden; white-space: nowrap; font-size: clamp(5px,.92cqw,9.5px); font-weight: 700; text-overflow: clip; font-variant-numeric: tabular-nums; }.keycap.muted { opacity: .7; }.keycap.blank { opacity: 0; border-color: transparent; box-shadow: none; }
/* function row keys carry 3-char labels (F10-F12): keep them fully readable */
.keyboard-row:first-child .keycap span { font-size: clamp(4.5px,.78cqw,8.5px); letter-spacing: -.03em; }.keycap.side { padding: .5cqw .4cqw; border-radius: .6cqw; min-width: 0; }.keycap.side span { font-size: clamp(5.5px,.95cqw,9px); }.keycap.side b { font-size: clamp(5px,.9cqw,8.5px); }.kb-side { display: flex; gap: 1cqw; flex: 0 0 auto; align-items: start; }
.kb-right-block { display: grid; grid-template-rows: repeat(6, 5.1cqw); grid-template-columns: repeat(3, minmax(3.2cqw, auto)); gap: .9cqw; }
.kb-right-block.num { grid-template-columns: repeat(4, minmax(3.4cqw, auto)); }
.keycap.warm { box-shadow: inset 0 1px rgba(255,255,255,.17),0 5px 14px color-mix(in srgb,var(--key-color),transparent 65%); }.keycap.hot { box-shadow: inset 0 1px rgba(255,255,255,.2),0 6px 18px color-mix(in srgb,var(--key-color),transparent 53%); }.keyboard-footer { justify-content: space-between; margin-top: 18px; color: var(--tx-faint); font-size: 10px; }.keyboard-footer span { display: flex; align-items: center; gap: 8px; }.live-indicator { width: 5px; height: 5px; }
.side-column { display: flex; flex-direction: column; gap: 15px; }.mouse-panel, .top-keys-panel { padding: 24px 25px; }.panel-kicker { padding: 5px 8px; border-radius: 6px; color: var(--tx-faint); font-size: 9px; }.mouse-content { gap: 20px; align-items: center; }.mouse-shape { position: relative; flex: 0 0 105px; height: 148px; border: 2px solid rgba(var(--violet-rgb),.58); border-radius: 52px 52px 43px 43px; background: linear-gradient(160deg,rgba(52,217,255,.2),rgba(var(--violet-rgb),.14)); transform: rotate(-3deg); }.mouse-top { position: relative; display: flex; height: 85px; overflow: hidden; border-bottom: 1px solid rgba(var(--violet-rgb),.25); border-radius: 50px 50px 0 0; }.mouse-button { position: relative; flex: 1; padding-top: 25px; color: #fff; text-align: center; font-size: 9px; }.mouse-left { border-right: 1px solid rgba(var(--violet-rgb),.25); background: linear-gradient(135deg,rgba(var(--pink-rgb),.82),rgba(var(--pink-rgb),.12)); }.mouse-right { background: linear-gradient(45deg,rgba(var(--violet-rgb),.1),rgba(var(--violet-rgb),.7)); }.mouse-wheel { position: absolute; top: 15px; left: 50%; width: 13px; height: 25px; border: 1px solid rgba(255,255,255,.55); border-radius: 8px; transform: translateX(-50%); }.mouse-wheel i { display: block; width: 3px; height: 8px; margin: 4px auto; border-radius: 3px; background: var(--acc-cyan); }.mouse-side-buttons { position: absolute; top: 65px; right: -8px; display: flex; flex-direction: column; gap: 5px; }.mouse-side-buttons i { width: 9px; height: 20px; border: 1px solid rgba(var(--green-rgb),.65); border-radius: 4px; background: rgba(var(--green-rgb),.35); }.mouse-stats { flex: 1; display: flex; flex-direction: column; gap: 12px; }.mouse-stat { display: grid; grid-template-columns: 7px 1fr auto; align-items: center; gap: 8px; color: var(--tx-dim); font-size: 10px; }.mouse-stat i { width: 6px; height: 6px; border-radius: 50%; }.mouse-stat b { color: var(--tx-strong); font-size: 11px; }.sparkline { color: var(--acc-pink-bright); font-size: 18px; letter-spacing: -5px; }.top-key-list { display: flex; flex-direction: column; gap: 13px; }.top-key-row { display: grid; grid-template-columns: 23px 48px 1fr 44px; align-items: center; gap: 9px; }.rank { color: var(--tx-mute); font-size: 9px; }.top-key-label { color: var(--tx-strong); font-size: 11px; font-weight: 700; }.mini-bar { height: 5px; overflow: hidden; border-radius: 99px; background: var(--bar-track); }.mini-bar i { display: block; height: 100%; border-radius: inherit; }.top-key-row b { color: var(--tx-soft); text-align: right; font-size: 10px; }
.timeline-panel { padding: 24px 28px 20px; }.timeline-note { gap: 5px; color: var(--tx-faint); font-size: 10px; }.timeline-note b { color: var(--acc-pink-soft); }.timeline-chart { position: relative; display: flex; align-items: end; gap: 7px; height: 120px; padding: 0 6px; }.chart-grid-lines { position: absolute; inset: 0 6px 20px; display: flex; flex-direction: column; justify-content: space-between; }.chart-grid-lines i { display: block; border-top: 1px dashed rgba(var(--line-rgb),.1); }.chart-column { position: relative; z-index: 1; display: flex; flex: 1; height: 100%; flex-direction: column; align-items: center; justify-content: flex-end; }.chart-bar { position: relative; width: min(100%,30px); min-height: 5px; margin-bottom: 15px; border-radius: 6px 6px 2px 2px; background: linear-gradient(180deg,var(--acc-pink-bright),var(--acc-violet) 75%,var(--bar-tip)); opacity: .85; transition: height .25s ease,opacity .2s ease; }.chart-bar:hover { opacity: 1; }.chart-bar span { position: absolute; top: -17px; left: 50%; display: none; color: var(--tx-soft); font-size: 8px; transform: translateX(-50%); white-space: nowrap; }.chart-bar:hover span { display: block; }.chart-column small { position: absolute; bottom: 0; left: 0; right: 0; height: 12px; color: var(--tx-mute); font-size: 8px; text-align: center; }.footer-note { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-top: 15px; color: var(--tx-mute); font-size: 10px; }.clear-button { border: 0; padding: 0; color: var(--tx-mute); background: transparent; cursor: pointer; font-size: 10px; }.clear-button:hover:not(:disabled) { color: var(--acc-pink-soft); }.clear-button:disabled { cursor: not-allowed; opacity: .35; }
/* Stacking fixes: freshly opened layers must paint above the stat cards.
   The hero row owns the date popover, the topbar owns the theme/keyshow popovers,
   so both need a higher z-index than the stat grid below them. */
.topbar { z-index: 5; }.hero-row { z-index: 2; }.runtime-warning { z-index: 4; }
.topbar { position: sticky; top: 10px; padding: 9px 16px; border: 1px solid rgba(var(--line-rgb), .14); border-radius: 18px; background: rgba(var(--pop-rgb), .8); backdrop-filter: blur(16px); box-shadow: 0 12px 32px rgba(0, 0, 0, .16); margin-bottom: 26px; }
html[data-theme="starlight"] .topbar { box-shadow: 0 12px 30px rgba(0, 0, 0, .08); }
@media (max-width: 1050px) { .content-grid { grid-template-columns: 1fr; }.side-column { display: grid; grid-template-columns: 1fr 1fr; } }
@media (max-width: 720px) { .app-shell { padding: 22px 15px; }.topbar { align-items: flex-start; margin-bottom: 58px; }.topbar-actions { gap: 7px; }.demo-chip { display: none; }.hero-row { align-items: flex-start; flex-direction: column; }.range-switch { align-self: stretch; justify-content: space-between; }.range-switch button { flex: 1; }.stat-grid { grid-template-columns: 1fr 1fr; }.stat-card { min-height: 145px; padding: 16px; }.stat-card strong { font-size: 22px; }.side-column { display: flex; }.mouse-content { justify-content: center; }.timeline-panel, .keyboard-panel, .mouse-panel, .top-keys-panel { padding-inline: 17px; }.footer-note { flex-direction: column; gap: 7px; } }
</style>
