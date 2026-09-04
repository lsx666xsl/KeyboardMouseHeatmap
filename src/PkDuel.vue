<script setup lang="ts">
/** PkDuel — LAN typing duel. Discovery list, challenge, 60s head-to-head. */
import { onMounted, onUnmounted, ref } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

type Peer = { name: string; host: string; port: number };
type Phase = "idle" | "hosting" | "playing" | "result";

const emit = defineEmits<{ (e: "close"): void }>();
const playerName = ref(localStorage.getItem("keypulse-pk-name") || "");
const phase = ref<Phase>("idle");
const peers = ref<Peer[]>([]);
const myScore = ref(0);
const peerScore = ref(0);
const peerName = ref("对手");
const secondsLeft = ref(0);
const myRole = ref("");
const message = ref("");
const dueling = ref(false);

let pkLocal = 0;
let reportTimer: ReturnType<typeof setInterval> | undefined;
let stopPk: UnlistenFn | undefined;
let stopKey: UnlistenFn | undefined;

async function refreshPeers() {
  try {
    peers.value = await invoke<Peer[]>("pk_peers");
  } catch {
    peers.value = [];
  }
}

async function startHosting() {
  if (!playerName.value.trim()) playerName.value = "玩家" + Math.floor(Math.random() * 900 + 100);
  localStorage.setItem("keypulse-pk-name", playerName.value);
  try {
    await invoke("pk_start", { name: playerName.value });
    phase.value = "hosting";
    message.value = "等待对手挑战…（保持打开，同网段其他 KeyPulse 会看到你）";
  } catch (error) {
    message.value = String(error);
  }
}

async function challenge(peer: Peer) {
  if (!playerName.value.trim()) playerName.value = "玩家" + Math.floor(Math.random() * 900 + 100);
  localStorage.setItem("keypulse-pk-name", playerName.value);
  peerName.value = peer.name;
  try {
    await invoke("pk_challenge", { name: playerName.value, host: peer.host, port: peer.port });
  } catch (error) {
    message.value = String(error);
  }
}

function beginDuel() {
  phase.value = "playing";
  dueling.value = true;
  pkLocal = 0;
  myScore.value = 0;
  peerScore.value = 0;
  reportTimer = setInterval(() => {
    invoke("pk_report", { value: pkLocal }).catch(() => undefined);
  }, 1000);
}

function endDuel() {
  dueling.value = false;
  if (reportTimer) clearInterval(reportTimer);
  reportTimer = undefined;
  phase.value = "result";
  message.value = "";
}

async function stopAll() {
  dueling.value = false;
  if (reportTimer) clearInterval(reportTimer);
  reportTimer = undefined;
  try {
    await invoke("pk_stop");
  } catch {
    // already stopped
  }
  phase.value = "idle";
  message.value = "";
}

async function quitToLobby() {
  await stopAll();
  refreshPeers();
}

onMounted(async () => {
  refreshPeers();
  try {
    stopPk = await listen<any>("pk-event", (event) => {
      const payload = event.payload as Record<string, unknown>;
      const type = payload.type as string;
      if (type === "hosting") {
        phase.value = "hosting";
        message.value = "正在等待对手（本机端口 " + payload.port + "）…";
      } else if (type === "started") {
        myRole.value = (payload.role as string) || "";
        beginDuel();
        secondsLeft.value = Number(payload.seconds) || 60;
      } else if (type === "tick") {
        secondsLeft.value = Number(payload.left) ?? 0;
      } else if (type === "selfCount") {
        myScore.value = Number(payload.value) || 0;
      } else if (type === "peerCount") {
        peerScore.value = Number(payload.value) || 0;
      } else if (type === "ended") {
        endDuel();
      } else if (type === "stopped") {
        phase.value = "idle";
        dueling.value = false;
      }
    });
    // count local presses from the shared keyshow stream
    stopKey = await listen<{ kind: string; action: string }>("keyshow-event", (event) => {
      if (dueling.value && event.payload.kind === "key" && event.payload.action === "down") {
        pkLocal += 1;
      }
    });
  } catch {
    // no runtime
  }
});

onUnmounted(() => {
  stopPk?.();
  stopKey?.();
  if (reportTimer) clearInterval(reportTimer);
  if (dueling.value) void invoke("pk_stop").catch(() => undefined);
});

const pct = (mine: number, theirs: number) => {
  const total = mine + theirs;
  if (!total) return 50;
  return Math.round((mine / total) * 100);
};
const isWinner = () => myScore.value > peerScore.value;
</script>

<template>
  <div class="pk-backdrop" @click.self="emit('close')">
    <section class="pk-modal" role="dialog" aria-modal="true" aria-label="PK 对战">
      <div class="pk-head"><div><p class="eyebrow accent">VS MODE</p><h3>打字 PK · 60 秒竞速</h3></div><button class="pk-close" aria-label="关闭 PK" @click="stopAll(); emit('close')">×</button></div>

      <div v-if="phase === 'idle'" class="pk-body">
        <p class="pk-intro">和同网段开启 KeyPulse 的朋友比 60 秒谁按得更多——谁键盘敲得快一目了然。</p>
        <label class="pk-name">你的昵称 <input v-model="playerName" maxlength="16" placeholder="输入昵称" /></label>
        <div class="pk-actions">
          <button class="pk-primary" @click="startHosting">🛡 开启对战等待挑战</button>
          <button class="pk-ghost" @click="refreshPeers">↻ 刷新对手</button>
        </div>
        <div v-if="message" class="pk-msg">{{ message }}</div>
        <div class="pk-peers">
          <div v-if="!peers.length" class="pk-empty">暂未发现对手 — 让对方也打开 PK 对战，并保持在同一网络</div>
          <div v-for="peer in peers" :key="peer.host + ':' + peer.port" class="pk-peer">
            <span class="pk-peer-name">{{ peer.name }}</span><span class="pk-peer-addr">{{ peer.host }}:{{ peer.port }}</span>
            <button class="pk-challenge" @click="challenge(peer)">⚡ 挑战</button>
          </div>
        </div>
      </div>

      <div v-else-if="phase === 'hosting'" class="pk-body">
        <p class="pk-waiting">🛡 已在 {{ playerName }} 名下等待挑战…</p>
        <div class="pk-actions"><button class="pk-ghost" @click="stopAll">取消等待</button></div>
        <div v-if="message" class="pk-msg">{{ message }}</div>
      </div>

      <div v-else-if="phase === 'playing'" class="pk-body">
        <div class="pk-vs"><span class="pk-me">{{ playerName || "我" }}</span><span class="pk-clock">{{ String(secondsLeft).padStart(2, "0") }}</span><span class="pk-me">{{ peerName }}</span></div>
        <div class="pk-bar"><i :style="{ width: pct(myScore, peerScore) + '%' }"></i></div>
        <div class="pk-scores"><span>{{ myScore }}</span><span>{{ peerScore }}</span></div>
        <p class="pk-tip">疯狂打字！⌨ 每 1 秒同步一次比分</p>
      </div>

      <div v-else class="pk-body">
        <p class="pk-result">{{ isWinner() ? "🏆 你赢了！" : myScore === peerScore ? "🤝 平局！" : "😅 惜败，再来一局？" }}</p>
        <div class="pk-final"><div><b>{{ myScore }}</b><small>{{ playerName || "我" }}</small></div><span>:</span><div><b>{{ peerScore }}</b><small>{{ peerName }}</small></div></div>
        <div class="pk-actions"><button class="pk-primary" @click="quitToLobby">⚔ 再战一局</button><button class="pk-ghost" @click="emit('close')">关闭</button></div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.pk-backdrop { position: fixed; z-index: 30; inset: 0; display: grid; place-items: center; padding: 22px; background: rgba(4, 9, 24, .6); backdrop-filter: blur(8px); }
.pk-modal { width: min(100%, 460px); max-height: min(680px, calc(100vh - 44px)); overflow: auto; padding: 22px; border: 1px solid rgba(var(--cyan-rgb), .25); border-radius: 20px; background: linear-gradient(145deg, rgba(var(--panel-rgb), .98), rgba(var(--pop-rgb), .98)); box-shadow: 0 26px 80px rgba(0, 0, 0, .45); }
.pk-head { display: flex; align-items: start; justify-content: space-between; gap: 14px; margin-bottom: 14px; }
.pk-modal h3 { margin: 4px 0 0; font-size: 20px; letter-spacing: -.04em; }
.pk-close { width: 30px; height: 30px; border: 1px solid rgba(var(--line-rgb), .25); border-radius: 50%; color: var(--tx-soft); background: rgba(var(--line-rgb), .1); cursor: pointer; font-size: 19px; line-height: 1; }
.pk-intro { margin: 0 0 14px; color: var(--tx-soft); font-size: 12px; line-height: 1.7; }
.pk-name { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; color: var(--tx-faint); font-size: 10px; }
.pk-name input { padding: 9px 11px; border: 1px solid rgba(var(--line-rgb), .28); border-radius: 10px; color: var(--tx-strong); background: rgba(var(--ink-rgb), .35); font-size: 13px; }
.pk-actions { display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.pk-primary { padding: 10px 16px; border: 0; border-radius: 11px; color: #071021; background: var(--acc-cyan); font-weight: 800; font-size: 12px; cursor: pointer; }
.pk-primary:hover { background: var(--acc-cyan-bright); }
.pk-ghost { padding: 10px 14px; border: 1px solid rgba(var(--line-rgb), .25); border-radius: 11px; color: var(--tx-soft); background: transparent; font-size: 12px; cursor: pointer; }
.pk-ghost:hover { border-color: rgba(var(--cyan-rgb), .6); color: var(--text-main); }
.pk-msg { margin: 4px 0 10px; color: var(--acc-amber); font-size: 11px; }
.pk-peers { display: grid; gap: 6px; margin-top: 6px; }
.pk-empty { padding: 14px; border: 1px dashed rgba(var(--line-rgb), .25); border-radius: 12px; color: var(--tx-faint); font-size: 11px; text-align: center; line-height: 1.6; }
.pk-peer { display: flex; align-items: center; gap: 8px; padding: 9px 11px; border: 1px solid rgba(var(--line-rgb), .16); border-radius: 11px; background: rgba(var(--ink-rgb), .25); }
.pk-peer-name { font-weight: 800; color: var(--tx-strong); font-size: 12px; }
.pk-peer-addr { color: var(--tx-faint); font-size: 9px; }
.pk-challenge { margin-left: auto; padding: 6px 12px; border: 0; border-radius: 9px; color: #fff; background: linear-gradient(135deg, var(--acc-pink), var(--acc-violet)); font-weight: 800; font-size: 11px; cursor: pointer; }
.pk-waiting { text-align: center; color: var(--tx-soft); font-size: 13px; padding: 10px 0; }
.pk-vs { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin: 6px 0 14px; }
.pk-me { max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 900; font-size: 14px; color: var(--tx-strong); }
.pk-clock { font-size: 40px; font-weight: 900; letter-spacing: -.05em; color: var(--acc-pink-soft); font-variant-numeric: tabular-nums; }
.pk-bar { height: 12px; border-radius: 99px; background: rgba(var(--line-rgb), .2); overflow: hidden; }
.pk-bar i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--acc-cyan), var(--acc-pink)); transition: width .5s ease; }
.pk-scores { display: flex; justify-content: space-between; margin-top: 6px; color: var(--tx-strong); font-size: 20px; font-weight: 900; font-variant-numeric: tabular-nums; }
.pk-tip { margin: 12px 0 0; color: var(--tx-faint); font-size: 10px; text-align: center; }
.pk-result { text-align: center; font-size: 26px; font-weight: 900; color: var(--text-main); margin: 4px 0 12px; }
.pk-final { display: flex; align-items: center; justify-content: center; gap: 22px; margin-bottom: 16px; }
.pk-final div { text-align: center; }
.pk-final b { display: block; font-size: 44px; font-weight: 900; color: var(--acc-pink-soft); letter-spacing: -.04em; }
.pk-final small { color: var(--tx-faint); font-size: 11px; }
.pk-final > span { font-size: 26px; font-weight: 900; color: var(--tx-faint); }
</style>
