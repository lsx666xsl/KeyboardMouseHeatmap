<script setup lang="ts">
/** DailyCard — a shareable "typing footprint" card rendered on canvas.
 * Shows today's totals, champion, peak hour and the 24h activity rhythm. */
import { onMounted, ref, watch } from "vue";
import { invoke } from "@tauri-apps/api/core";

type Footprint = {
  date: string;
  totalKeyPresses: number;
  totalMouseActions: number;
  keys: Array<{ keyId: string; label: string; count: number }>;
  activity: Array<{ hour: number; count: number }>;
};

const props = defineProps<{ snapshot: Footprint; title?: string }>();
const emit = defineEmits<{ (e: "close"): void }>();

const canvas = ref<HTMLCanvasElement | null>(null);
const previewUrl = ref("");
const savedPath = ref("");

function fmt(n: number) {
  return n.toLocaleString("zh-CN");
}

function draw() {
  const c = canvas.value;
  if (!c) return;
  const dpr = window.devicePixelRatio || 1;
  const W = 900;
  const H = 500;
  c.width = W * dpr;
  c.height = H * dpr;
  const g = c.getContext("2d");
  if (!g) return;
  g.scale(dpr, dpr);
  g.clearRect(0, 0, W, H);

  const snap = props.snapshot;
  // background: brand gradient
  const bg = g.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0, "#101a3c");
  bg.addColorStop(0.55, "#1c2a5e");
  bg.addColorStop(1, "#3b2a6d");
  g.fillStyle = bg;
  g.fillRect(0, 0, W, H);
  // glows
  const glow = g.createRadialGradient(W * 0.85, H * 0.12, 10, W * 0.85, H * 0.12, 300);
  glow.addColorStop(0, "rgba(52,217,255,.22)");
  glow.addColorStop(1, "rgba(52,217,255,0)");
  g.fillStyle = glow;
  g.fillRect(0, 0, W, H);
  const glow2 = g.createRadialGradient(W * 0.12, H * 0.95, 10, W * 0.12, H * 0.95, 260);
  glow2.addColorStop(0, "rgba(255,92,122,.18)");
  glow2.addColorStop(1, "rgba(255,92,122,0)");
  g.fillStyle = glow2;
  g.fillRect(0, 0, W, H);

  const title = props.title || "今日输入足迹";
  const dateLabel = snap.date || new Date().toISOString().slice(0, 10);

  g.fillStyle = "#ff718b";
  g.font = "800 13px Inter, sans-serif";
  g.fillText("K E Y P U L S E", 46, 66);

  g.fillStyle = "#f8fafc";
  g.font = "900 30px Inter, sans-serif";
  g.fillText(title, 46, 116);

  g.fillStyle = "rgba(148,163,184,.9)";
  g.font = "500 13px Inter, sans-serif";
  g.fillText(dateLabel + " · offline by design", 46, 144);

  const top = snap.keys.slice().sort((a, b) => b.count - a.count)[0];
  const champion = top && top.count > 0 ? top : null;
  const peak = snap.activity.reduce((best, item) => (item.count > best.count ? item : best), { hour: -1, count: 0 });

  // big numbers
  const statX = [46, 244, 442, 640];
  const statTitles = ["总按键", "鼠标操作", "活跃时段", "冠军键"];
  const statValues = [fmt(snap.totalKeyPresses), fmt(snap.totalMouseActions), snap.activity.filter((a) => a.count > 0).length + " h", champion ? champion.label : "—"];
  const statSubs = [champion ? "峰值节奏持续在线" : "继续创造节奏", "点击与滚动", "有输入的小时数", champion ? fmt(champion.count) + " 次" : "今天还没有输入"];
  g.font = "800 12px Inter, sans-serif";
  for (let i = 0; i < 4; i++) {
    g.fillStyle = "rgba(148,163,184,.85)";
    g.fillText(statTitles[i], statX[i], 210);
    g.fillStyle = "#ffffff";
    g.font = "900 30px Inter, sans-serif";
    g.fillText(statValues[i], statX[i], 248);
    g.fillStyle = "rgba(167,139,250,.95)";
    g.font = "500 11px Inter, sans-serif";
    g.fillText(statSubs[i], statX[i], 270);
    g.font = "800 12px Inter, sans-serif";
  }

  // 24h rhythm bars
  const barTop = 330;
  const barH = 90;
  const barW = 13;
  const gap = (W - 92 - 24 * barW) / 23;
  const max = Math.max(1, ...snap.activity.map((a) => a.count));
  const colors = ["#276eaa", "#34d9ff", "#2de2a6", "#ffd166", "#ff5c7a"];
  for (let hour = 0; hour < 24; hour++) {
    const value = snap.activity[hour]?.count || 0;
    const h = Math.max(value > 0 ? 4 : 1, (value / max) * barH);
    const x = 46 + hour * (barW + gap);
    const ratio = value / max;
    const idx = Math.min(colors.length - 1, Math.floor(ratio * colors.length));
    g.fillStyle = colors[Math.max(0, idx)] + (value > 0 ? "cc" : "22");
    const y = barTop + barH - h;
    g.beginPath();
    g.roundRect(x, y, barW, h, 3);
    g.fill();
    if (hour % 4 === 0) {
      g.fillStyle = "rgba(148,163,184,.55)";
      g.font = "500 9px Inter, sans-serif";
      g.fillText(String(hour).padStart(2, "0"), x - 2, barTop + barH + 16);
    }
  }
  if (peak.hour >= 0) {
    g.fillStyle = "#ff8098";
    g.font = "800 12px Inter, sans-serif";
    g.fillText("峰值 " + String(peak.hour).padStart(2, "0") + ":00", 46, barTop + barH + 42);
  }

  // footer hint
  g.fillStyle = "rgba(148,163,184,.5)";
  g.font = "500 10px Inter, sans-serif";
  g.fillText("KeyPulse · 每一次敲击都算数", 46, H - 26);

  previewUrl.value = c.toDataURL("image/png");
}

async function saveCard() {
  const c = canvas.value;
  if (!c) return;
  try {
    const fileName = "keypulse-footprint-" + (props.snapshot.date || "today");
    savedPath.value = await invoke<string>("save_footprint_png", {
      dataUrl: c.toDataURL("image/png"),
      fileName,
    });
  } catch (error) {
    savedPath.value = "保存失败：" + String(error);
  }
}

watch(() => props.snapshot, draw, { deep: true });
onMounted(() => {
  setTimeout(draw, 50);
});
</script>

<template>
  <div class="foot-backdrop" @click.self="emit('close')">
    <section class="foot-modal" role="dialog" aria-modal="true" aria-label="足迹卡片">
      <div class="foot-head"><div><p class="eyebrow accent">DAILY FOOTPRINT</p><h3>输入足迹卡</h3></div><button class="foot-close" aria-label="关闭足迹卡片" @click="emit('close')">×</button></div>
      <canvas ref="canvas" class="foot-canvas" :style="{ display: previewUrl ? 'none' : 'block' }"></canvas>
      <img v-if="previewUrl" :src="previewUrl" class="foot-preview" alt="输入足迹卡片预览" />
      <div class="foot-actions">
        <button class="foot-save" @click="saveCard">保存 PNG 到图片目录</button>
        <span v-if="savedPath" class="foot-saved">{{ savedPath }}</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.foot-backdrop { position: fixed; z-index: 30; inset: 0; display: grid; place-items: start center; padding: max(24px, 8vh) 24px 24px; background: rgba(4, 9, 24, .6); backdrop-filter: blur(8px); }
.foot-modal { width: min(100%, 940px); max-height: calc(100vh - max(28px, 8vh) - 50px); overflow: auto; padding: 22px; border: 1px solid rgba(var(--cyan-rgb), .25); border-radius: 20px; background: linear-gradient(145deg, rgba(var(--panel-rgb), .98), rgba(var(--pop-rgb), .98)); box-shadow: 0 28px 80px rgba(0, 0, 0, .45); }
.foot-head { display: flex; align-items: start; justify-content: space-between; gap: 14px; margin-bottom: 14px; }
.foot-modal h3 { margin: 4px 0 0; font-size: 20px; letter-spacing: -.04em; }
.foot-close { width: 30px; height: 30px; border: 1px solid rgba(var(--line-rgb), .25); border-radius: 50%; color: var(--tx-soft); background: rgba(var(--line-rgb), .1); cursor: pointer; font-size: 19px; line-height: 1; }
.foot-canvas { width: 100%; }
.foot-preview { display: block; width: 100%; border-radius: 14px; box-shadow: 0 12px 40px rgba(0, 0, 0, .3); }
.foot-actions { display: flex; align-items: center; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
.foot-save { padding: 9px 16px; border: 0; border-radius: 10px; color: #071021; background: var(--acc-cyan); font-weight: 800; font-size: 12px; cursor: pointer; }
.foot-save:hover { background: var(--acc-cyan-bright); }
.foot-saved { color: var(--tx-soft); font-size: 10px; overflow-wrap: anywhere; }
</style>
