<script setup lang="ts">
import { computed, ref } from "vue";

type KeyItem = { id: string; label: string; count: number; width?: number; muted?: boolean };
type MouseStat = { label: string; value: number; color: string };

const ranges = ["今天", "本周", "本月"];
const activeRange = ref("今天");
const recording = ref(true);

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

const mouseStats: MouseStat[] = [
  { label: "左键", value: 4832, color: "#ff5c7a" },
  { label: "右键", value: 812, color: "#a78bfa" },
  { label: "滚轮", value: 1204, color: "#34d9ff" },
  { label: "侧键", value: 208, color: "#2de2a6" },
];
const hourlyActivity = [32, 48, 26, 18, 12, 22, 45, 72, 88, 64, 76, 94, 82, 68, 74, 91, 100, 86, 60, 44, 36, 30, 22, 16];
const allKeys = computed(() => keyboardRows.flat());
const totalKeyPresses = computed(() => allKeys.value.reduce((sum, key) => sum + key.count, 0));
const totalMouseActions = computed(() => mouseStats.reduce((sum, item) => sum + item.value, 0));
const topKeys = computed(() => [...allKeys.value].sort((a, b) => b.count - a.count).slice(0, 4));
const maxKeyCount = computed(() => Math.max(...allKeys.value.map((key) => key.count)));

function formatNumber(value: number) { return value.toLocaleString("zh-CN"); }
function heatColor(count: number) {
  const ratio = Math.min(count / maxKeyCount.value, 1);
  return `hsl(${205 - ratio * 185} 88% ${28 + (1 - ratio) * 18}%)`;
}
function heatLevel(count: number) {
  const ratio = count / maxKeyCount.value;
  return ratio > 0.65 ? "hot" : ratio > 0.28 ? "warm" : "cool";
}
</script>

<template>
  <main class="app-shell">
    <div class="ambient ambient-one"></div><div class="ambient ambient-two"></div>
    <header class="topbar">
      <div class="brand-lockup">
        <div class="brand-mark"><span></span><span></span><span></span></div>
        <div><p class="eyebrow">PERSONAL INPUT LAB</p><h1>Key<span>Pulse</span></h1></div>
      </div>
      <div class="topbar-actions">
        <div class="demo-chip"><i></i> 演示数据</div>
        <button class="record-button" :class="{ paused: !recording }" @click="recording = !recording"><span class="record-dot"></span>{{ recording ? "正在记录" : "已暂停" }}</button>
        <button class="avatar-button">KP</button>
      </div>
    </header>

    <section class="hero-row">
      <div><p class="eyebrow accent">YOUR RHYTHM, VISUALIZED</p><h2>今天的输入节奏<br /><em>比昨天更有力。</em></h2><p class="hero-copy">看见每一次敲击、点击和滚动，找到属于你的数字节奏。</p></div>
      <div class="range-switch" role="tablist" aria-label="时间范围">
        <button v-for="range in ranges" :key="range" :class="{ active: activeRange === range }" @click="activeRange = range">{{ range }}</button><button class="calendar-button" aria-label="选择日期">▣</button>
      </div>
    </section>

    <section class="stat-grid">
      <article class="stat-card stat-card-primary"><div class="card-icon icon-spark">✦</div><p>总按键数</p><strong>{{ formatNumber(totalKeyPresses) }}</strong><span class="trend up">↗ 12.8% <small>对比昨日</small></span></article>
      <article class="stat-card"><div class="card-icon icon-mouse">●</div><p>鼠标操作</p><strong>{{ formatNumber(totalMouseActions) }}</strong><span class="trend up">↗ 8.4% <small>对比昨日</small></span></article>
      <article class="stat-card"><div class="card-icon icon-time">◷</div><p>活跃时长</p><strong>5<span class="unit">h</span> 12<span class="unit">m</span></strong><span class="trend neutral">⌁ 分布在 9 个时段</span></article>
      <article class="stat-card highlight-card"><div class="card-icon icon-top">♛</div><p>今日冠军</p><strong>Space</strong><span class="trend accent-text">{{ formatNumber(8420) }} 次按下</span></article>
    </section>

    <section class="content-grid">
      <article class="panel keyboard-panel">
        <div class="panel-heading"><div><p class="eyebrow">KEYBOARD MAP</p><h3>键盘热力图</h3></div><div class="legend"><span class="legend-gradient"></span><small>低</small><small>高</small></div></div>
        <div class="keyboard-wrap">
          <div v-for="(row, rowIndex) in keyboardRows" :key="rowIndex" class="keyboard-row">
            <div v-for="key in row" :key="key.id" class="keycap" :class="[heatLevel(key.count), { muted: key.muted }]" :style="{ flex: `${key.width ?? 1} 1 0`, '--key-color': heatColor(key.count) }" :title="`${key.label}：${formatNumber(key.count)} 次`"><span>{{ key.label }}</span><b>{{ formatNumber(key.count) }}</b></div>
          </div>
        </div>
        <div class="keyboard-footer"><span><i class="live-indicator"></i>数据实时更新中</span><span>按键总量 · {{ formatNumber(totalKeyPresses) }}</span></div>
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

    <section class="panel timeline-panel"><div class="panel-heading compact"><div><p class="eyebrow">ACTIVITY PULSE · {{ activeRange }}</p><h3>一天中的活跃节奏</h3></div><span class="timeline-note">峰值时段 <b>16:00</b></span></div><div class="timeline-chart"><div class="chart-grid-lines"><i></i><i></i><i></i><i></i></div><div v-for="(value, hour) in hourlyActivity" :key="hour" class="chart-column"><div class="chart-bar" :style="{ height: `${value}%` }"><span>{{ value }}</span></div><small v-if="hour % 3 === 0">{{ String(hour).padStart(2, "0") }}:00</small></div></div></section>
    <footer class="footer-note"><span>KeyPulse · offline by design</span><span>隐私优先 · 只保存聚合统计，不保存输入文本</span></footer>
  </main>
</template>

<style>
:root { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #f8fafc; background: #0f172a; font-synthesis: none; text-rendering: optimizeLegibility; -webkit-font-smoothing: antialiased; }
* { box-sizing: border-box; } body { margin: 0; min-width: 320px; min-height: 100vh; } button { font: inherit; }
</style>

<style scoped>
.app-shell { position: relative; min-height: 100vh; overflow: hidden; padding: 34px clamp(22px, 5vw, 76px) 28px; background: radial-gradient(circle at 86% 6%, rgba(120,87,255,.17), transparent 29%), #0f172a; }
.ambient { position: absolute; pointer-events: none; border-radius: 50%; filter: blur(8px); }.ambient-one { width: 320px; height: 320px; right: -130px; top: 260px; background: #ff5c7a; opacity: .08; }.ambient-two { width: 240px; height: 240px; left: -120px; bottom: 160px; background: #34d9ff; opacity: .08; }
.topbar, .hero-row, .stat-grid, .content-grid, .timeline-panel, .footer-note { position: relative; z-index: 1; max-width: 1480px; margin-inline: auto; }.topbar, .hero-row { display: flex; align-items: center; justify-content: space-between; gap: 24px; }.topbar { margin-bottom: 82px; }.brand-lockup, .topbar-actions, .range-switch, .legend, .keyboard-footer, .mouse-content, .timeline-note { display: flex; align-items: center; }.brand-lockup { gap: 13px; }.brand-mark { width: 34px; height: 34px; display: flex; align-items: end; justify-content: center; gap: 3px; padding: 6px; border-radius: 11px; transform: rotate(-8deg); background: linear-gradient(135deg, #ff5c7a, #a78bfa); box-shadow: 0 8px 24px rgba(255,92,122,.23); }.brand-mark span { display: block; width: 5px; border-radius: 5px; background: #fff; }.brand-mark span:nth-child(1) { height: 11px; opacity: .75; }.brand-mark span:nth-child(2) { height: 18px; }.brand-mark span:nth-child(3) { height: 14px; opacity: .85; }
.eyebrow { margin: 0; color: #7e8eae; font-size: 10px; font-weight: 800; letter-spacing: .18em; line-height: 1.3; }.eyebrow.accent { color: #ff8098; } h1, h2, h3, p { margin-top: 0; } h1 { margin-bottom: 0; font-size: 19px; line-height: 1; letter-spacing: -.04em; } h1 span { color: #ff718b; }.topbar-actions { gap: 12px; }
.demo-chip, .record-button, .avatar-button, .range-switch, .panel-kicker { border: 1px solid rgba(148,163,184,.15); background: rgba(23,37,84,.55); }.demo-chip { display: flex; align-items: center; gap: 8px; padding: 9px 13px; border-radius: 999px; color: #a9b6cc; font-size: 11px; }.demo-chip i, .live-indicator { width: 7px; height: 7px; border-radius: 50%; background: #2de2a6; box-shadow: 0 0 0 4px rgba(45,226,166,.11), 0 0 14px #2de2a6; }.record-button { display: flex; align-items: center; gap: 8px; padding: 9px 13px; border-radius: 999px; color: #e2e8f0; cursor: pointer; font-size: 11px; transition: .2s ease; }.record-button:hover { border-color: rgba(52,217,255,.7); transform: translateY(-1px); }.record-button.paused { color: #a9b6cc; }.record-dot { width: 7px; height: 7px; border-radius: 50%; background: #ff5c7a; box-shadow: 0 0 12px #ff5c7a; }.paused .record-dot { background: #64748b; box-shadow: none; }.avatar-button { width: 34px; height: 34px; border-radius: 50%; color: #fff; font-size: 10px; font-weight: 800; cursor: pointer; background: linear-gradient(135deg, #34d9ff, #a78bfa); }
.hero-row { align-items: end; margin-bottom: 35px; } h2 { margin-bottom: 13px; font-size: clamp(34px,4vw,58px); line-height: 1.05; letter-spacing: -.065em; } h2 em { color: #ff718b; font-style: normal; }.hero-copy { margin-bottom: 0; color: #8292ae; font-size: 14px; }.range-switch { gap: 3px; padding: 4px; border-radius: 13px; }.range-switch button { border: 0; padding: 9px 15px; border-radius: 9px; color: #7e8eae; background: transparent; cursor: pointer; font-size: 12px; }.range-switch button:hover { color: #f8fafc; }.range-switch button.active { color: #fff; background: #2f3c65; box-shadow: 0 5px 13px rgba(0,0,0,.15); }.range-switch .calendar-button { padding-inline: 12px; color: #34d9ff; }
.stat-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 15px; }.stat-card, .panel { border: 1px solid rgba(148,163,184,.13); background: linear-gradient(145deg,rgba(23,37,84,.86),rgba(15,23,42,.9)); box-shadow: 0 20px 50px rgba(0,0,0,.13); }.stat-card { position: relative; min-height: 168px; padding: 22px 23px; overflow: hidden; border-radius: 18px; }.stat-card::after { position: absolute; content: ""; right: -37px; bottom: -45px; width: 135px; height: 135px; border: 1px solid rgba(52,217,255,.1); border-radius: 50%; }.stat-card-primary { background: linear-gradient(140deg,rgba(49,56,112,.97),rgba(23,37,84,.8)); }.highlight-card { background: linear-gradient(140deg,rgba(117,54,111,.55),rgba(23,37,84,.86)); }.card-icon { display: grid; place-items: center; width: 30px; height: 30px; margin-bottom: 19px; border-radius: 9px; font-size: 14px; }.icon-spark { color: #ffd166; background: rgba(255,209,102,.14); }.icon-mouse { color: #34d9ff; background: rgba(52,217,255,.13); }.icon-time { color: #a78bfa; background: rgba(167,139,250,.14); }.icon-top { color: #ff8098; background: rgba(255,92,122,.14); }.stat-card p { margin-bottom: 5px; color: #8d9ab3; font-size: 11px; }.stat-card strong { display: block; margin-bottom: 11px; font-size: 28px; letter-spacing: -.05em; }.unit { margin-left: 2px; color: #8d9ab3; font-size: 14px; font-weight: 500; letter-spacing: 0; }.trend { font-size: 11px; }.trend small { margin-left: 5px; color: #8190a9; }.trend.up { color: #2de2a6; }.trend.neutral { color: #8d9ab3; }.accent-text { color: #ff8098; }
.content-grid { display: grid; grid-template-columns: minmax(0,1.8fr) minmax(300px,.85fr); gap: 15px; margin-bottom: 15px; }.panel { border-radius: 18px; }.keyboard-panel { padding: 27px 28px 20px; }.panel-heading { display: flex; align-items: start; justify-content: space-between; gap: 18px; margin-bottom: 28px; }.panel-heading.compact { align-items: center; margin-bottom: 22px; }.panel h3 { margin: 5px 0 0; font-size: 19px; letter-spacing: -.04em; }.legend { gap: 9px; color: #71819d; font-size: 10px; }.legend-gradient { display: block; width: 75px; height: 6px; border-radius: 99px; background: linear-gradient(90deg,#276eaa,#34d9ff,#2de2a6,#ffd166,#ff5c7a); }
.keyboard-wrap { display: flex; flex-direction: column; gap: 8px; padding: 20px 16px; border-radius: 15px; background: rgba(8,16,35,.42); }.keyboard-row { display: flex; gap: 7px; min-height: 45px; }.keycap { display: flex; min-width: 0; flex-direction: column; justify-content: space-between; padding: 8px 8px 6px; border: 1px solid color-mix(in srgb,var(--key-color),white 18%); border-radius: 7px; color: #fff; background: linear-gradient(145deg,color-mix(in srgb,var(--key-color),white 9%),var(--key-color)); box-shadow: inset 0 1px rgba(255,255,255,.15),0 5px 10px rgba(0,0,0,.17); transition: transform .18s ease,filter .18s ease; }.keycap:hover { z-index: 2; filter: brightness(1.16); transform: translateY(-4px) scale(1.04); }.keycap span { overflow: hidden; color: rgba(255,255,255,.78); font-size: 9px; font-weight: 700; text-overflow: ellipsis; }.keycap b { overflow: hidden; font-size: 9px; font-weight: 700; text-overflow: ellipsis; }.keycap.muted { opacity: .7; }.keycap.warm { box-shadow: inset 0 1px rgba(255,255,255,.17),0 5px 14px color-mix(in srgb,var(--key-color),transparent 65%); }.keycap.hot { box-shadow: inset 0 1px rgba(255,255,255,.2),0 6px 18px color-mix(in srgb,var(--key-color),transparent 53%); }.keyboard-footer { justify-content: space-between; margin-top: 18px; color: #71819d; font-size: 10px; }.keyboard-footer span { display: flex; align-items: center; gap: 8px; }.live-indicator { width: 5px; height: 5px; }
.side-column { display: flex; flex-direction: column; gap: 15px; }.mouse-panel, .top-keys-panel { padding: 24px 25px; }.panel-kicker { padding: 5px 8px; border-radius: 6px; color: #7e8eae; font-size: 9px; }.mouse-content { gap: 20px; align-items: center; }.mouse-shape { position: relative; flex: 0 0 105px; height: 148px; border: 2px solid rgba(167,139,250,.58); border-radius: 52px 52px 43px 43px; background: linear-gradient(160deg,rgba(52,217,255,.2),rgba(167,139,250,.14)); transform: rotate(-3deg); }.mouse-top { position: relative; display: flex; height: 85px; overflow: hidden; border-bottom: 1px solid rgba(167,139,250,.25); border-radius: 50px 50px 0 0; }.mouse-button { position: relative; flex: 1; padding-top: 25px; color: #fff; text-align: center; font-size: 9px; }.mouse-left { border-right: 1px solid rgba(167,139,250,.25); background: linear-gradient(135deg,rgba(255,92,122,.82),rgba(255,92,122,.12)); }.mouse-right { background: linear-gradient(45deg,rgba(167,139,250,.1),rgba(167,139,250,.7)); }.mouse-wheel { position: absolute; top: 15px; left: 50%; width: 13px; height: 25px; border: 1px solid rgba(255,255,255,.55); border-radius: 8px; transform: translateX(-50%); }.mouse-wheel i { display: block; width: 3px; height: 8px; margin: 4px auto; border-radius: 3px; background: #34d9ff; }.mouse-side-buttons { position: absolute; top: 65px; right: -8px; display: flex; flex-direction: column; gap: 5px; }.mouse-side-buttons i { width: 9px; height: 20px; border: 1px solid rgba(45,226,166,.65); border-radius: 4px; background: rgba(45,226,166,.35); }.mouse-stats { flex: 1; display: flex; flex-direction: column; gap: 12px; }.mouse-stat { display: grid; grid-template-columns: 7px 1fr auto; align-items: center; gap: 8px; color: #8d9ab3; font-size: 10px; }.mouse-stat i { width: 6px; height: 6px; border-radius: 50%; }.mouse-stat b { color: #e2e8f0; font-size: 11px; }.sparkline { color: #ff718b; font-size: 18px; letter-spacing: -5px; }.top-key-list { display: flex; flex-direction: column; gap: 13px; }.top-key-row { display: grid; grid-template-columns: 23px 48px 1fr 44px; align-items: center; gap: 9px; }.rank { color: #546582; font-size: 9px; }.top-key-label { color: #e2e8f0; font-size: 11px; font-weight: 700; }.mini-bar { height: 5px; overflow: hidden; border-radius: 99px; background: #263452; }.mini-bar i { display: block; height: 100%; border-radius: inherit; }.top-key-row b { color: #a9b6cc; text-align: right; font-size: 10px; }
.timeline-panel { padding: 24px 28px 20px; }.timeline-note { gap: 5px; color: #8190a9; font-size: 10px; }.timeline-note b { color: #ff8098; }.timeline-chart { position: relative; display: flex; align-items: end; gap: 7px; height: 120px; padding: 0 6px; }.chart-grid-lines { position: absolute; inset: 0 6px 20px; display: flex; flex-direction: column; justify-content: space-between; }.chart-grid-lines i { display: block; border-top: 1px dashed rgba(148,163,184,.1); }.chart-column { position: relative; z-index: 1; display: flex; flex: 1; height: 100%; flex-direction: column; align-items: center; justify-content: end; gap: 8px; }.chart-bar { position: relative; width: min(100%,30px); min-height: 5px; border-radius: 6px 6px 2px 2px; background: linear-gradient(180deg,#ff718b,#a78bfa 75%,#455184); opacity: .85; transition: height .25s ease,opacity .2s ease; }.chart-bar:hover { opacity: 1; }.chart-bar span { position: absolute; top: -17px; left: 50%; display: none; color: #f8fafc; font-size: 8px; transform: translateX(-50%); }.chart-bar:hover span { display: block; }.chart-column small { height: 12px; color: #62728f; font-size: 8px; }.footer-note { display: flex; justify-content: space-between; margin-top: 15px; color: #53627c; font-size: 10px; }
@media (max-width: 1050px) { .content-grid { grid-template-columns: 1fr; }.side-column { display: grid; grid-template-columns: 1fr 1fr; }.keyboard-panel { overflow-x: auto; }.keyboard-wrap { min-width: 770px; } }
@media (max-width: 720px) { .app-shell { padding: 22px 15px; }.topbar { align-items: flex-start; margin-bottom: 58px; }.topbar-actions { gap: 7px; }.demo-chip { display: none; }.hero-row { align-items: flex-start; flex-direction: column; }.range-switch { align-self: stretch; justify-content: space-between; }.range-switch button { flex: 1; }.stat-grid { grid-template-columns: 1fr 1fr; }.stat-card { min-height: 145px; padding: 16px; }.stat-card strong { font-size: 22px; }.side-column { display: flex; }.mouse-content { justify-content: center; }.timeline-panel, .keyboard-panel, .mouse-panel, .top-keys-panel { padding-inline: 17px; }.footer-note { flex-direction: column; gap: 7px; } }
</style>
