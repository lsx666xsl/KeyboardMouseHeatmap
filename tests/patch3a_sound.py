"""Replay patch 3a: sound / achievements / count-up script state."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

# 1. import sound module
old = 'import { configureSound, playKeySound, type SoundVoice } from "./sound";'
if old not in t:
    anchor = 'import MiniStat from "./MiniStat.vue";'
    assert anchor in t
    t = t.replace(anchor, anchor + '\nimport { configureSound, playKeySound, type SoundVoice } from "./sound";')

# 2. state + logic after toggleMini
anchor_fn = """async function toggleMini() {
  try {
    miniEnabled.value = await invoke<boolean>("toggle_mini");
  } catch (error) {
    console.info("Could not toggle mini stats window.", error);
  }
}"""
assert anchor_fn in t, "toggleMini missing"
block = anchor_fn + """

// ---------- fun: sound, achievements, count-up ----------
const soundVoice = ref<SoundVoice>((localStorage.getItem("keypulse-sound") as SoundVoice) || "off");
const soundVolume = ref(Number(localStorage.getItem("keypulse-sound-volume")) || 60);
const achievementsOn = ref(localStorage.getItem("keypulse-achievements") !== "0");
const toastMsg = ref("");
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
let countTimer: ReturnType<typeof setInterval> | undefined;
function tweenTo(target: number, setter: (v: number) => void, current: () => number) {
  if (countTimer) clearInterval(countTimer);
  const from = current();
  const diff = target - from;
  if (Math.abs(diff) < 2) { setter(target); return; }
  const started = Date.now();
  const duration = 360;
  countTimer = setInterval(() => {
    const progress = Math.min((Date.now() - started) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    setter(Math.round(from + diff * eased));
    if (progress >= 1 && countTimer) { clearInterval(countTimer); countTimer = undefined; }
  }, 24);
}
watch(totalKeyPresses, (value) => {
  tweenTo(value, (n) => { shownKeys.value = n; }, () => shownKeys.value);
  checkAchievements(value);
});
watch(totalMouseActions, (value) => {
  tweenTo(value, (n) => { shownMouse.value = n; }, () => shownMouse.value);
});
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
}"""
t = t.replace(anchor_fn, block)

# 3. mount wiring
old_mount = """    connectToRuntime();
    refreshKeyshowState();
    refreshMiniState();"""
assert old_mount in t
t = t.replace(old_mount, """    connectToRuntime();
    wireSoundFx();
    refreshKeyshowState();
    refreshMiniState();""")

old_un = """  stopKeyshowChangedListener?.();
  stopMiniListener?.();"""
assert old_un in t
t = t.replace(old_un, """  stopKeyshowChangedListener?.();
  stopMiniListener?.();
  stopKeySoundListener?.();""")

# 4. tweened headline numbers
old_a = """<strong>{{ formatNumber(totalKeyPresses) }}</strong>"""
assert old_a in t
t = t.replace(old_a, """<strong>{{ formatNumber(shownKeys) }}</strong>""")
old_b = """<strong>{{ formatNumber(totalMouseActions) }}</strong>"""
assert old_b in t
t = t.replace(old_b, """<strong>{{ formatNumber(shownMouse) }}</strong>""")

p.write_text(t, encoding="utf-8")
print("patch3a applied")
