<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { WebviewWindow } from "@tauri-apps/api/webviewWindow";
import KeyshowStage from "./KeyshowStage.vue";

let isKeyshowWindow = false;
try {
  isKeyshowWindow = getCurrentWindow().label === "keys-overlay";
} catch {
  // Plain-browser preview (`npm run dev`) has no Tauri window.
}

type KeyItem = { id: string; label: string; count: number; width?: number; muted?: boolean };
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
const showKeyshowPanel = ref(false);
const keyshowStyle = ref<string>(localStorage.getItem("keypulse-keyshow-style") || "capsule");
const keyshowOptions = [
  { id: "capsule", name: "节奏胶囊流", icon: "⬚", desc: "组合合并 · 连打 ×N" },
  { id: "particle", name: "能量粒子", icon: "✦", desc: "上飘拖尾 · 越按越亮" },
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
    showKeyshowPanel.value = false;
  } catch (error) {
    console.info("Could not toggle keyshow overlay.", error);
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
  if (showKeyshowPanel.value && !target.closest(".keyshow-control")) showKeyshowPanel.value = false;
}
const liveDashboard = ref<DashboardData | null>(null);
const demoMode = ref(true);
let stopStatsListener: UnlistenFn | undefined;
let stopRecordingListener: UnlistenFn | undefined;

const keyboardRows: KeyItem[][] = [
  ["Esc", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"].map((label, index) => ({ id: label, label, count: [122, 84, 96, 44, 58, 278, 65, 72, 51, 40, 32, 29, 20][index], muted: true })),
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
    ["Ctrl", 812, 1.5], ["Alt", 234, 1.5], ["Space", 8420, 6.5], ["Alt", 144, 1.5], ["Fn", 52], ["Menu", 18], ["Ctrl", 314, 1.5],
  ].map(([label, count, width], index) => ({ id: `${label}-${index}`, label: String(label), count: Number(count), width: Number(width) || undefined, muted: label === "Fn" || label === "Menu" })),
];

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
  const liveKey = liveDashboard.value?.keys.find((item) => item.keyId === backendKeyId(key));
  return liveKey?.count ?? (demoMode.value ? key.count : 0);
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
const maxKeyCount = computed(() => Math.max(1, ...allKeys.value.map((key) => key.count)));
const hourlyActivity = computed(() => {
  const source = demoMode.value || !liveDashboard.value ? demoHourlyActivity : liveDashboard.value.activity.map((item) => item.count);
  const max = Math.max(1, ...source);
  return source.map((value) => Math.round((value / max) * 100));
});
const activeHours = computed(() => demoMode.value || !liveDashboard.value ? 9 : liveDashboard.value.activity.filter((item) => item.count > 0).length);
const peakHour = computed(() => hourlyActivity.value.indexOf(Math.max(...hourlyActivity.value)));

function formatNumber(value: number) { return value.toLocaleString("zh-CN"); }
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
  if (!isKeyshowWindow) {
    connectToRuntime();
    refreshKeyshowState();
    try {
      await invoke("set_keyshow_position", { position: keyshowPosition.value });
      await invoke("set_keyshow_size", { size: keyshowSize.value });
    } catch {
      // Older runtime without layout commands.
    }
    try {
      stopKeyshowChangedListener = await listen<boolean>("keyshow-changed", (event) => {
        keyshowEnabled.value = event.payload;
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
  document.removeEventListener("click", closePopoversOnOutsideClick);
});
</script>

<template>
  <KeyshowStage v-if="isKeyshowWindow" />
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
          <button class="keyshow-button" :class="{ on: keyshowEnabled }" :aria-expanded="showKeyshowPanel" aria-label="按键可视化设置" @click="showKeyshowPanel = !showKeyshowPanel"><i>⌨</i><span class="keyshow-led"></span></button>
          <div v-if="showKeyshowPanel" class="keyshow-popover">
            <p class="keyshow-popover-title">按键可视化</p>
            <button class="keyshow-master" :class="{ on: keyshowEnabled }" @click="toggleKeyshow"><span class="ks-master-text"><b>{{ keyshowEnabled ? "正在显示按键" : "已关闭" }}</b><small>{{ keyshowEnabled ? "按下的键实时显示在屏幕底部" : "开启后按键会实时显示在屏幕底部" }}</small></span><span class="ks-switch"><i></i></span></button>
            <div class="ks-layout-title">显示位置</div>
            <div class="ks-positions" role="radiogroup" aria-label="按键浮层显示位置">
              <button v-for="pos in keyshowPositions" :key="pos.id" class="ks-pos" :class="{ active: keyshowPosition === pos.id }" role="radio" :aria-checked="keyshowPosition === pos.id" :title="pos.name" @click="changeKeyshowPosition(pos.id)"><i :style="{ left: pos.dot.left, top: pos.dot.top }"></i></button>
            </div>
            <div class="ks-layout-title">浮层大小</div>
            <div class="ks-sizes" role="radiogroup" aria-label="按键浮层大小">
              <button v-for="option in keyshowSizeOptions" :key="option.id" class="ks-size" :class="{ active: keyshowSize === option.id }" role="radio" :aria-checked="keyshowSize === option.id" @click="changeKeyshowSize(option.id)">{{ option.name }}</button>
            </div>
            <div class="ks-styles" role="radiogroup" aria-label="按键显示风格">
              <button v-for="option in keyshowOptions" :key="option.id" role="radio" :aria-checked="keyshowStyle === option.id" class="ks-style" :class="{ active: keyshowStyle === option.id }" @click="pickKeyshowStyle(option.id)"><span class="ks-style-icon">{{ option.icon }}</span><span class="ks-style-text"><b>{{ option.name }}</b><small>{{ option.desc }}</small></span></button>
            </div>
            <p class="ks-note">⌨ 显示的是按下动作，不记录文本；托盘菜单也可随时开/关。</p>
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
        <div class="privacy-storage"><span>本地数据库</span><code>%APPDATA%\com.keyboardmouse.heatmap\keypulse.sqlite</code></div>
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
      <article class="stat-card stat-card-primary"><div class="card-icon icon-spark">✦</div><p>总按键数</p><strong>{{ formatNumber(totalKeyPresses) }}</strong><span class="trend" :class="demoMode ? 'up' : 'neutral'">{{ demoMode ? "↗ 12.8%" : "⌁ 已保存聚合" }} <small>{{ demoMode ? "对比昨日" : activeRangeLabel }}</small></span></article>
      <article class="stat-card"><div class="card-icon icon-mouse">●</div><p>鼠标操作</p><strong>{{ formatNumber(totalMouseActions) }}</strong><span class="trend" :class="demoMode ? 'up' : 'neutral'">{{ demoMode ? "↗ 8.4%" : "⌁ 已保存聚合" }} <small>{{ demoMode ? "对比昨日" : activeRangeLabel }}</small></span></article>
      <article class="stat-card"><div class="card-icon icon-time">◷</div><p>活跃时段</p><strong>{{ activeHours }}<span class="unit">h</span></strong><span class="trend neutral">⌁ 按小时聚合统计</span></article>
      <article class="stat-card highlight-card"><div class="card-icon icon-top">♛</div><p>{{ activeRange === "今天" ? "今日冠军" : "范围冠军" }}</p><strong>{{ champion?.label ?? "暂无" }}</strong><span class="trend accent-text">{{ formatNumber(champion?.count ?? 0) }} 次按下</span></article>
    </section>

    <section class="content-grid">
      <article class="panel keyboard-panel">
        <div class="panel-heading"><div><p class="eyebrow">KEYBOARD MAP</p><h3>键盘热力图</h3></div><div class="legend"><span class="legend-gradient"></span><small>低</small><small>高</small></div></div>
        <div class="keyboard-wrap">
          <div v-for="(row, rowIndex) in keyboardRows" :key="rowIndex" class="keyboard-row">
            <div v-for="key in row" :key="key.id" class="keycap" :class="[heatLevel(keyCount(key)), { muted: key.muted }]" :style="{ flex: `${key.width ?? 1} 1 0`, '--key-color': heatColor(keyCount(key)) }" :title="`${key.label}：${formatNumber(keyCount(key))} 次`"><span>{{ key.label }}</span><b>{{ formatNumber(keyCount(key)) }}</b></div>
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

    <section class="panel timeline-panel"><div class="panel-heading compact"><div><p class="eyebrow">ACTIVITY PULSE · {{ activeRangeLabel }}</p><h3>一天中的活跃节奏</h3></div><span class="timeline-note">峰值时段 <b>{{ String(peakHour).padStart(2, "0") }}:00</b></span></div><div class="timeline-chart"><div class="chart-grid-lines"><i></i><i></i><i></i><i></i></div><div v-for="(value, hour) in hourlyActivity" :key="hour" class="chart-column"><div class="chart-bar" :style="{ height: `${value}%` }"><span>{{ value }}</span></div><small v-if="hour % 3 === 0">{{ String(hour).padStart(2, "0") }}:00</small></div></div></section>
    <footer class="footer-note"><span>KeyPulse · offline by design</span><span>隐私优先 · 只保存聚合统计，不保存输入文本</span><button class="clear-button" :disabled="demoMode" @click="clearStats">清空本地数据</button></footer>
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
* { box-sizing: border-box; } body { margin: 0; min-width: 320px; min-height: 100vh; background: var(--page-bg); } button { font: inherit; }
html.keyshow-window, html.keyshow-window body { background: transparent !important; }
</style>

<style scoped>
.app-shell { position: relative; min-height: 100vh; overflow: hidden; padding: 34px clamp(22px, 5vw, 76px) 28px; background: radial-gradient(circle at 86% 6%, var(--page-glow), transparent 29%), var(--page-bg); }
.ambient { position: absolute; pointer-events: none; border-radius: 50%; filter: blur(8px); }.ambient-one { width: 320px; height: 320px; right: -130px; top: 260px; background: var(--acc-pink); opacity: .08; }.ambient-two { width: 240px; height: 240px; left: -120px; bottom: 160px; background: var(--acc-cyan); opacity: .08; }
.topbar, .hero-row, .stat-grid, .content-grid, .timeline-panel, .footer-note { position: relative; z-index: 1; max-width: 1480px; margin-inline: auto; }.topbar, .hero-row { display: flex; align-items: center; justify-content: space-between; gap: 24px; }.topbar { margin-bottom: 82px; }.brand-lockup, .topbar-actions, .range-switch, .legend, .keyboard-footer, .mouse-content, .timeline-note { display: flex; align-items: center; }.brand-lockup { gap: 13px; }.brand-mark { width: 34px; height: 34px; display: flex; align-items: end; justify-content: center; gap: 3px; padding: 6px; border-radius: 11px; transform: rotate(-8deg); background: linear-gradient(135deg, var(--acc-pink), var(--acc-violet)); box-shadow: 0 8px 24px rgba(var(--pink-rgb),.23); }.brand-mark span { display: block; width: 5px; border-radius: 5px; background: #fff; }.brand-mark span:nth-child(1) { height: 11px; opacity: .75; }.brand-mark span:nth-child(2) { height: 18px; }.brand-mark span:nth-child(3) { height: 14px; opacity: .85; }
.eyebrow { margin: 0; color: #7e8eae; font-size: 10px; font-weight: 800; letter-spacing: .18em; line-height: 1.3; }.eyebrow.accent { color: var(--acc-pink-soft); } h1, h2, h3, p { margin-top: 0; } h1 { margin-bottom: 0; font-size: 19px; line-height: 1; letter-spacing: -.04em; } h1 span { color: var(--acc-pink-bright); }.topbar-actions { gap: 12px; }
.demo-chip, .record-button, .avatar-button, .range-switch, .panel-kicker { border: 1px solid rgba(148,163,184,.15); background: rgba(var(--panel-rgb),.55); }.demo-chip { display: flex; align-items: center; gap: 8px; padding: 9px 13px; border-radius: 999px; color: #a9b6cc; font-size: 11px; }.demo-chip i, .live-indicator { width: 7px; height: 7px; border-radius: 50%; background: var(--acc-green); box-shadow: 0 0 0 4px rgba(var(--green-rgb),.11), 0 0 14px var(--acc-green); }.demo-chip.warning { color: var(--acc-amber); border-color: rgba(var(--amber-rgb),.3); }.demo-chip.warning i { background: var(--acc-amber); box-shadow: 0 0 0 4px rgba(var(--amber-rgb),.12), 0 0 14px var(--acc-amber); }.record-button { display: flex; align-items: center; gap: 8px; padding: 9px 13px; border-radius: 999px; color: #e2e8f0; cursor: pointer; font-size: 11px; transition: .2s ease; }.record-button:hover:not(:disabled) { border-color: rgba(var(--cyan-rgb),.7); transform: translateY(-1px); }.record-button.paused { color: #a9b6cc; }.record-button:disabled { cursor: not-allowed; opacity: .55; }.record-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--acc-pink); box-shadow: 0 0 12px var(--acc-pink); }.paused .record-dot { background: #64748b; box-shadow: none; }.avatar-button { width: 34px; height: 34px; border-radius: 50%; color: #fff; font-size: 10px; font-weight: 800; cursor: pointer; background: linear-gradient(135deg, var(--acc-cyan), var(--acc-violet)); } .theme-control { position: relative; }.theme-button { display: flex; align-items: center; gap: 4px; height: 34px; padding: 0 11px; border: 1px solid rgba(148,163,184,.15); border-radius: 999px; background: rgba(var(--panel-rgb),.55); cursor: pointer; }.theme-button .theme-dot { display: block; width: 7px; height: 7px; border-radius: 50%; }.theme-button:hover { border-color: rgba(var(--cyan-rgb),.7); transform: translateY(-1px); }.theme-popover { position: absolute; z-index: 8; top: calc(100% + 10px); right: 0; width: 190px; padding: 15px; border: 1px solid rgba(var(--cyan-rgb),.22); border-radius: 14px; background: rgba(var(--pop-rgb),.98); box-shadow: 0 18px 42px rgba(0,0,0,.35); }.theme-popover-title { margin: 0 0 11px; color: var(--text-main); font-size: 12px; font-weight: 800; }.theme-option { display: flex; align-items: center; gap: 10px; width: 100%; margin-top: 4px; padding: 8px 9px; border: 1px solid transparent; border-radius: 9px; color: #a9b6cc; background: transparent; cursor: pointer; font-size: 11px; text-align: left; transition: .15s ease; }.theme-option:hover { color: #fff; background: rgba(148,163,184,.08); }.theme-option.active { color: #fff; border-color: rgba(var(--cyan-rgb),.45); background: rgba(var(--cyan-rgb),.1); }.theme-dots { display: flex; align-items: center; gap: 3px; }.theme-dots i { width: 8px; height: 8px; border-radius: 50%; display: block; } .keyshow-control { position: relative; }.keyshow-button { display: flex; align-items: center; gap: 6px; height: 34px; padding: 0 10px; border: 1px solid rgba(148,163,184,.15); border-radius: 999px; background: rgba(var(--panel-rgb),.55); cursor: pointer; color: #7e8eae; transition: border-color .2s ease, color .2s ease; }.keyshow-button i { font-style: normal; font-size: 14px; }.keyshow-button:hover { border-color: rgba(var(--cyan-rgb),.7); color: #fff; }.keyshow-button.on { border-color: rgba(var(--green-rgb),.65); color: var(--text-main); box-shadow: 0 0 14px rgba(var(--green-rgb),.25); }.keyshow-led { width: 6px; height: 6px; border-radius: 50%; background: #64748b; }.keyshow-button.on .keyshow-led { background: var(--acc-green); box-shadow: 0 0 8px var(--acc-green); }.keyshow-popover { position: absolute; z-index: 8; top: calc(100% + 10px); right: 0; width: 236px; padding: 15px; border: 1px solid rgba(var(--cyan-rgb),.22); border-radius: 14px; background: rgba(var(--pop-rgb),.98); box-shadow: 0 18px 42px rgba(0,0,0,.35); }.keyshow-popover-title { margin: 0 0 11px; color: var(--text-main); font-size: 12px; font-weight: 800; }.keyshow-master { display: flex; align-items: center; justify-content: space-between; gap: 10px; width: 100%; padding: 10px 11px; border: 1px solid rgba(148,163,184,.16); border-radius: 11px; color: #a9b6cc; background: rgba(15,23,42,.4); cursor: pointer; text-align: left; }.keyshow-master.on { border-color: rgba(var(--green-rgb),.55); background: rgba(var(--green-rgb),.08); }.ks-master-text b, .ks-master-text small { display: block; }.ks-master-text b { color: #e2e8f0; font-size: 12px; }.keyshow-master.on .ks-master-text b { color: var(--acc-green); }.ks-master-text small { margin-top: 3px; color: #71819d; font-size: 9px; }.ks-switch { position: relative; flex: 0 0 34px; height: 18px; border-radius: 99px; background: #263452; transition: background .2s ease; }.ks-switch i { position: absolute; top: 3px; left: 3px; width: 12px; height: 12px; border-radius: 50%; background: #94a3b8; transition: all .2s ease; }.keyshow-master.on .ks-switch { background: rgba(var(--green-rgb),.5); }.keyshow-master.on .ks-switch i { left: 19px; background: var(--acc-green); box-shadow: 0 0 8px var(--acc-green); }.ks-styles { display: grid; gap: 5px; margin-top: 10px; }.ks-style { display: flex; align-items: center; gap: 9px; width: 100%; padding: 8px 9px; border: 1px solid transparent; border-radius: 10px; color: #a9b6cc; background: transparent; cursor: pointer; text-align: left; }.ks-style:hover { background: rgba(148,163,184,.08); }.ks-style.active { border-color: rgba(var(--cyan-rgb),.45); background: rgba(var(--cyan-rgb),.1); }.ks-style-icon { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 8px; color: var(--text-main); background: linear-gradient(135deg, rgba(var(--cyan-rgb),.35), rgba(var(--violet-rgb),.35)); font-style: normal; font-size: 13px; }.ks-style-text b, .ks-style-text small { display: block; }.ks-style-text b { color: #e2e8f0; font-size: 11px; }.ks-style-text small { margin-top: 2px; color: #71819d; font-size: 9px; }.ks-style.active .ks-style-text b { color: #fff; }.ks-note { margin: 11px 0 0; padding-top: 10px; border-top: 1px dashed rgba(148,163,184,.16); color: #71819d; font-size: 9px; line-height: 1.55; } .keyshow-popover { width: 272px; }.ks-layout-title { margin: 12px 0 6px; color: #7e8eae; font-size: 9px; font-weight: 800; letter-spacing: .08em; }.ks-positions { display: grid; grid-template-columns: repeat(6, 1fr); gap: 5px; }.ks-pos { position: relative; height: 30px; border: 1px solid rgba(148,163,184,.15); border-radius: 7px; background: rgba(15,23,42,.4); cursor: pointer; }.ks-pos:hover { border-color: rgba(var(--cyan-rgb),.5); }.ks-pos.active { border-color: rgba(var(--cyan-rgb),.65); background: rgba(var(--cyan-rgb),.12); box-shadow: 0 0 10px rgba(var(--cyan-rgb),.18); }.ks-pos i { position: absolute; width: 5px; height: 5px; border-radius: 50%; background: #7e8eae; transform: translate(-50%, -50%); }.ks-pos.active i { background: var(--acc-cyan); box-shadow: 0 0 6px var(--acc-cyan); }.ks-sizes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; }.ks-size { padding: 6px 0; border: 1px solid rgba(148,163,184,.15); border-radius: 7px; color: #a9b6cc; background: rgba(15,23,42,.4); cursor: pointer; font-size: 10px; font-weight: 700; }.ks-size:hover { border-color: rgba(var(--cyan-rgb),.5); color: #fff; }.ks-size.active { border-color: rgba(var(--cyan-rgb),.65); color: #fff; background: rgba(var(--cyan-rgb),.14); }
.hero-row { align-items: end; margin-bottom: 35px; } h2 { margin-bottom: 13px; font-size: clamp(34px,4vw,58px); line-height: 1.05; letter-spacing: -.065em; } h2 em { color: var(--acc-pink-bright); font-style: normal; }.hero-copy { margin-bottom: 0; color: #8292ae; font-size: 14px; }.range-control { position: relative; }.range-switch { gap: 3px; padding: 4px; border-radius: 13px; }.range-switch button { border: 0; padding: 9px 15px; border-radius: 9px; color: #7e8eae; background: transparent; cursor: pointer; font-size: 12px; }.range-switch button:hover { color: var(--text-main); }.range-switch button.active { color: #fff; background: var(--surface-active); box-shadow: 0 5px 13px rgba(0,0,0,.15); }.range-switch .calendar-button { padding-inline: 12px; color: var(--acc-cyan); }.date-popover { position: absolute; z-index: 5; top: calc(100% + 10px); right: 0; width: 252px; padding: 16px; border: 1px solid rgba(var(--cyan-rgb),.22); border-radius: 15px; background: rgba(var(--pop-rgb),.98); box-shadow: 0 18px 42px rgba(0,0,0,.35); }.date-popover-title { margin: 0 0 13px; color: var(--text-main); font-size: 12px; font-weight: 800; }.date-popover label { display: flex; flex-direction: column; gap: 6px; margin-top: 10px; color: #8d9ab3; font-size: 10px; }.date-popover input { width: 100%; border: 1px solid rgba(148,163,184,.2); border-radius: 8px; padding: 8px 9px; color: var(--text-main); background: rgba(var(--ink-rgb),.72); color-scheme: dark; font-size: 11px; }.date-popover input:focus { outline: 2px solid rgba(var(--cyan-rgb),.45); outline-offset: 1px; }.date-error { margin: 10px 0 0; color: var(--acc-pink-soft); font-size: 10px; }.date-popover-actions { display: flex; justify-content: end; gap: 8px; margin-top: 15px; }.date-popover-actions button { border: 0; border-radius: 8px; padding: 8px 10px; cursor: pointer; font-size: 10px; }.date-cancel { color: #a9b6cc; background: rgba(148,163,184,.12); }.date-apply { color: var(--apply-ink); background: var(--acc-cyan); font-weight: 800; }.date-apply:hover { background: var(--acc-cyan-bright); }
.runtime-warning { position: relative; z-index: 1; display: flex; align-items: center; gap: 10px; max-width: 1480px; margin: -54px auto 35px; padding: 11px 14px; border: 1px solid rgba(var(--amber-rgb),.28); border-radius: 12px; color: var(--acc-amber); background: rgba(84,64,31,.3); }.runtime-warning > span { display: grid; place-items: center; width: 18px; height: 18px; border-radius: 50%; color: #17120a; background: var(--acc-amber); font-size: 11px; font-weight: 900; }.runtime-warning b, .runtime-warning small { display: block; }.runtime-warning b { font-size: 11px; }.runtime-warning small { margin-top: 3px; color: #c1a968; font-size: 10px; }
.privacy-backdrop { position: fixed; z-index: 20; inset: 0; display: grid; place-items: center; padding: 22px; background: rgba(4,9,24,.72); backdrop-filter: blur(8px); }.privacy-dialog { width: min(100%, 520px); max-height: min(680px, calc(100vh - 44px)); overflow: auto; padding: 26px; border: 1px solid rgba(var(--cyan-rgb),.25); border-radius: 20px; background: linear-gradient(145deg, #192956, #101a39); box-shadow: 0 28px 80px rgba(0,0,0,.45); }.privacy-dialog-heading { display: flex; align-items: start; justify-content: space-between; gap: 18px; }.privacy-dialog h3 { margin: 5px 0 0; font-size: 22px; letter-spacing: -.05em; }.privacy-close { width: 30px; height: 30px; border: 1px solid rgba(148,163,184,.2); border-radius: 50%; color: #a9b6cc; background: rgba(148,163,184,.1); cursor: pointer; font-size: 20px; line-height: 1; }.privacy-close:hover { color: #fff; border-color: rgba(var(--cyan-rgb),.65); }.privacy-intro { margin: 22px 0 18px; color: #d7e0f0; font-size: 13px; line-height: 1.65; }.privacy-points { display: grid; gap: 10px; }.privacy-points article { display: grid; grid-template-columns: 29px 1fr; gap: 11px; padding: 13px; border: 1px solid rgba(148,163,184,.13); border-radius: 12px; background: rgba(var(--ink-rgb),.28); }.privacy-points article > span { color: var(--acc-cyan); font-size: 10px; font-weight: 900; }.privacy-points b, .privacy-points small { display: block; }.privacy-points b { margin-bottom: 4px; color: var(--text-main); font-size: 11px; }.privacy-points small { color: #91a0bc; font-size: 10px; line-height: 1.55; }.privacy-notice { display: grid; gap: 5px; margin-top: 14px; padding: 13px; border-left: 3px solid var(--acc-amber); color: #c1a968; background: rgba(var(--amber-rgb),.07); font-size: 10px; line-height: 1.55; }.privacy-notice b { color: var(--acc-amber); }.privacy-storage { display: grid; gap: 6px; margin-top: 17px; color: #71819d; font-size: 9px; }.privacy-storage code { overflow-wrap: anywhere; color: #a9b6cc; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 9px; }
.stat-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 15px; }.stat-card, .panel { border: 1px solid rgba(148,163,184,.13); background: linear-gradient(145deg,rgba(var(--panel-rgb),.86),rgba(15,23,42,.9)); box-shadow: 0 20px 50px rgba(0,0,0,.13); }.stat-card { position: relative; min-height: 168px; padding: 22px 23px; overflow: hidden; border-radius: 18px; }.stat-card::after { position: absolute; content: ""; right: -37px; bottom: -45px; width: 135px; height: 135px; border: 1px solid rgba(var(--cyan-rgb),.1); border-radius: 50%; }.stat-card-primary { background: linear-gradient(140deg,rgba(var(--hero-rgb),.97),rgba(var(--panel-rgb),.8)); }.highlight-card { background: linear-gradient(140deg,rgba(var(--pink-rgb),.55),rgba(var(--panel-rgb),.86)); }.card-icon { display: grid; place-items: center; width: 30px; height: 30px; margin-bottom: 19px; border-radius: 9px; font-size: 14px; }.icon-spark { color: var(--acc-amber); background: rgba(var(--amber-rgb),.14); }.icon-mouse { color: var(--acc-cyan); background: rgba(52,217,255,.13); }.icon-time { color: var(--acc-violet); background: rgba(var(--violet-rgb),.14); }.icon-top { color: var(--acc-pink-soft); background: rgba(var(--pink-rgb),.14); }.stat-card p { margin-bottom: 5px; color: #8d9ab3; font-size: 11px; }.stat-card strong { display: block; margin-bottom: 11px; font-size: 28px; letter-spacing: -.05em; }.unit { margin-left: 2px; color: #8d9ab3; font-size: 14px; font-weight: 500; letter-spacing: 0; }.trend { font-size: 11px; }.trend small { margin-left: 5px; color: #8190a9; }.trend.up { color: var(--acc-green); }.trend.neutral { color: #8d9ab3; }.accent-text { color: var(--acc-pink-soft); }
.content-grid { display: grid; grid-template-columns: minmax(0,1.8fr) minmax(300px,.85fr); gap: 15px; margin-bottom: 15px; }.panel { border-radius: 18px; }.keyboard-panel { padding: 27px 28px 20px; }.panel-heading { display: flex; align-items: start; justify-content: space-between; gap: 18px; margin-bottom: 28px; }.panel-heading.compact { align-items: center; margin-bottom: 22px; }.panel h3 { margin: 5px 0 0; font-size: 19px; letter-spacing: -.04em; }.legend { gap: 9px; color: #71819d; font-size: 10px; }.legend-gradient { display: block; width: 75px; height: 6px; border-radius: 99px; background: linear-gradient(90deg,var(--heat-1),var(--heat-2),var(--heat-3),var(--heat-4),var(--heat-5)); }
.keyboard-wrap { display: flex; flex-direction: column; gap: 8px; padding: 20px 16px; border-radius: 15px; background: rgba(var(--ink-rgb),.42); }.keyboard-row { display: flex; gap: 7px; min-height: 45px; }.keycap { display: flex; min-width: 0; flex-direction: column; justify-content: space-between; padding: 8px 8px 6px; border: 1px solid color-mix(in srgb,var(--key-color),white 18%); border-radius: 7px; color: #fff; background: linear-gradient(145deg,color-mix(in srgb,var(--key-color),white 9%),var(--key-color)); box-shadow: inset 0 1px rgba(255,255,255,.15),0 5px 10px rgba(0,0,0,.17); transition: transform .18s ease,filter .18s ease; }.keycap:hover { z-index: 2; filter: brightness(1.16); transform: translateY(-4px) scale(1.04); }.keycap span { overflow: hidden; color: rgba(255,255,255,.78); font-size: 9px; font-weight: 700; text-overflow: ellipsis; }.keycap b { overflow: hidden; font-size: 9px; font-weight: 700; text-overflow: ellipsis; }.keycap.muted { opacity: .7; }.keycap.warm { box-shadow: inset 0 1px rgba(255,255,255,.17),0 5px 14px color-mix(in srgb,var(--key-color),transparent 65%); }.keycap.hot { box-shadow: inset 0 1px rgba(255,255,255,.2),0 6px 18px color-mix(in srgb,var(--key-color),transparent 53%); }.keyboard-footer { justify-content: space-between; margin-top: 18px; color: #71819d; font-size: 10px; }.keyboard-footer span { display: flex; align-items: center; gap: 8px; }.live-indicator { width: 5px; height: 5px; }
.side-column { display: flex; flex-direction: column; gap: 15px; }.mouse-panel, .top-keys-panel { padding: 24px 25px; }.panel-kicker { padding: 5px 8px; border-radius: 6px; color: #7e8eae; font-size: 9px; }.mouse-content { gap: 20px; align-items: center; }.mouse-shape { position: relative; flex: 0 0 105px; height: 148px; border: 2px solid rgba(var(--violet-rgb),.58); border-radius: 52px 52px 43px 43px; background: linear-gradient(160deg,rgba(52,217,255,.2),rgba(var(--violet-rgb),.14)); transform: rotate(-3deg); }.mouse-top { position: relative; display: flex; height: 85px; overflow: hidden; border-bottom: 1px solid rgba(var(--violet-rgb),.25); border-radius: 50px 50px 0 0; }.mouse-button { position: relative; flex: 1; padding-top: 25px; color: #fff; text-align: center; font-size: 9px; }.mouse-left { border-right: 1px solid rgba(var(--violet-rgb),.25); background: linear-gradient(135deg,rgba(var(--pink-rgb),.82),rgba(var(--pink-rgb),.12)); }.mouse-right { background: linear-gradient(45deg,rgba(var(--violet-rgb),.1),rgba(var(--violet-rgb),.7)); }.mouse-wheel { position: absolute; top: 15px; left: 50%; width: 13px; height: 25px; border: 1px solid rgba(255,255,255,.55); border-radius: 8px; transform: translateX(-50%); }.mouse-wheel i { display: block; width: 3px; height: 8px; margin: 4px auto; border-radius: 3px; background: var(--acc-cyan); }.mouse-side-buttons { position: absolute; top: 65px; right: -8px; display: flex; flex-direction: column; gap: 5px; }.mouse-side-buttons i { width: 9px; height: 20px; border: 1px solid rgba(var(--green-rgb),.65); border-radius: 4px; background: rgba(var(--green-rgb),.35); }.mouse-stats { flex: 1; display: flex; flex-direction: column; gap: 12px; }.mouse-stat { display: grid; grid-template-columns: 7px 1fr auto; align-items: center; gap: 8px; color: #8d9ab3; font-size: 10px; }.mouse-stat i { width: 6px; height: 6px; border-radius: 50%; }.mouse-stat b { color: #e2e8f0; font-size: 11px; }.sparkline { color: var(--acc-pink-bright); font-size: 18px; letter-spacing: -5px; }.top-key-list { display: flex; flex-direction: column; gap: 13px; }.top-key-row { display: grid; grid-template-columns: 23px 48px 1fr 44px; align-items: center; gap: 9px; }.rank { color: #546582; font-size: 9px; }.top-key-label { color: #e2e8f0; font-size: 11px; font-weight: 700; }.mini-bar { height: 5px; overflow: hidden; border-radius: 99px; background: var(--bar-track); }.mini-bar i { display: block; height: 100%; border-radius: inherit; }.top-key-row b { color: #a9b6cc; text-align: right; font-size: 10px; }
.timeline-panel { padding: 24px 28px 20px; }.timeline-note { gap: 5px; color: #8190a9; font-size: 10px; }.timeline-note b { color: var(--acc-pink-soft); }.timeline-chart { position: relative; display: flex; align-items: end; gap: 7px; height: 120px; padding: 0 6px; }.chart-grid-lines { position: absolute; inset: 0 6px 20px; display: flex; flex-direction: column; justify-content: space-between; }.chart-grid-lines i { display: block; border-top: 1px dashed rgba(148,163,184,.1); }.chart-column { position: relative; z-index: 1; display: flex; flex: 1; height: 100%; flex-direction: column; align-items: center; justify-content: end; gap: 8px; }.chart-bar { position: relative; width: min(100%,30px); min-height: 5px; border-radius: 6px 6px 2px 2px; background: linear-gradient(180deg,var(--acc-pink-bright),var(--acc-violet) 75%,var(--bar-tip)); opacity: .85; transition: height .25s ease,opacity .2s ease; }.chart-bar:hover { opacity: 1; }.chart-bar span { position: absolute; top: -17px; left: 50%; display: none; color: var(--text-main); font-size: 8px; transform: translateX(-50%); }.chart-bar:hover span { display: block; }.chart-column small { height: 12px; color: #62728f; font-size: 8px; }.footer-note { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-top: 15px; color: #53627c; font-size: 10px; }.clear-button { border: 0; padding: 0; color: #63728d; background: transparent; cursor: pointer; font-size: 10px; }.clear-button:hover:not(:disabled) { color: var(--acc-pink-soft); }.clear-button:disabled { cursor: not-allowed; opacity: .35; }
/* Stacking fixes: the topbar layer (theme picker) must paint above the hero row
   (range buttons), and the runtime warning must stay above both when present. */
.topbar { z-index: 3; }.runtime-warning { z-index: 4; }
@media (max-width: 1050px) { .content-grid { grid-template-columns: 1fr; }.side-column { display: grid; grid-template-columns: 1fr 1fr; }.keyboard-panel { overflow-x: auto; }.keyboard-wrap { min-width: 770px; } }
@media (max-width: 720px) { .app-shell { padding: 22px 15px; }.topbar { align-items: flex-start; margin-bottom: 58px; }.topbar-actions { gap: 7px; }.demo-chip { display: none; }.hero-row { align-items: flex-start; flex-direction: column; }.range-switch { align-self: stretch; justify-content: space-between; }.range-switch button { flex: 1; }.stat-grid { grid-template-columns: 1fr 1fr; }.stat-card { min-height: 145px; padding: 16px; }.stat-card strong { font-size: 22px; }.side-column { display: flex; }.mouse-content { justify-content: center; }.timeline-panel, .keyboard-panel, .mouse-panel, .top-keys-panel { padding-inline: 17px; }.footer-note { flex-direction: column; gap: 7px; } }
</style>
