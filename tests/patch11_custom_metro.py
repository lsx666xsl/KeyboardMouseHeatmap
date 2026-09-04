"""Requirements 2+3 UI: custom sound picker + metronome row in settings; metronome dot on dashboard."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

# ---- imports for metronome tick ----
old_imp = 'import { configureSound, playKeySound, type SoundVoice } from "./sound";'
assert old_imp in t
t = t.replace(old_imp, 'import { configureSound, loadCustomSound, playKeySound, playMetronomeTick, type SoundVoice } from "./sound";')

# ---- script state after sound helpers ----
anchor = "function toggleAchievements(on: boolean) {"
assert anchor in t
block = anchor + """

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
}"""
t = t.replace(anchor, block)

# restore custom sound on boot when stored custom
old_mount = """    wireSoundFx();"""
assert old_mount in t
t = t.replace(old_mount, """    wireSoundFx();
    const storedCustom = localStorage.getItem("keypulse-custom-sound");
    if (soundVoice.value === "custom" && storedCustom) {
      invoke<string>("read_custom_sound_base64", { fileName: storedCustom })
        .then((dataUrl) => loadCustomSound(dataUrl))
        .catch(() => undefined);
    }""")

# cleanup timer
old_un = """  stopKeySoundListener?.();"""
assert old_un in t
t = t.replace(old_un, """  stopKeySoundListener?.();
  stopMetronome();""")

# ---- template: custom sound + metronome rows inside 趣味功能 section before note ----
note = '<p class="ks-note">⌨ 显示的是按下动作，不记录文本 · 托盘菜单或顶栏 ⌨ 按钮可随时开/关 · 拖动后选择任意预设位置可恢复对齐</p>'
assert note in t
extra = """              <div class="ks-layout-row">
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
"""
t = t.replace(note, extra + note)

# dashboard metronome dot marker (fixed bottom center) before toast transition
old_toast = '<Transition name="toast-pop">'
assert old_toast in t
t = t.replace(old_toast, '<Transition name="beat-pop"><i v-if="metronomeOn" :key="beatCount" class="beat-dot"></i></Transition>\n    <Transition name="toast-pop">')

# ---- css ----
anchor_css = ".ks-custom-hint"
if anchor_css not in t:
    anchor_css = ".ks-data-notice { margin: 8px 0 0; padding: 8px 10px; border-radius: 8px; color: var(--acc-amber); background: rgba(var(--amber-rgb), .08); font-size: 9px; line-height: 1.5; }"
    assert anchor_css in t
css = anchor_css + """
.ks-custom-hint { display: block; margin-top: 4px; color: var(--tx-faint); font-size: 8px; line-height: 1.5; overflow-wrap: anywhere; }
.beat-dot { position: fixed; z-index: 45; right: 18px; bottom: 16px; width: 10px; height: 10px; border-radius: 50%; background: var(--acc-pink); box-shadow: 0 0 12px var(--acc-pink); }
.beat-pop-enter-active { animation: beat-pulse .24s ease; }
.beat-pop-leave-active { display: none; }
@keyframes beat-pulse { 0% { transform: scale(.4); opacity: 1; } 100% { transform: scale(1.6); opacity: .2; } }
"""
t = t.replace(anchor_css, css)
p.write_text(t, encoding="utf-8")
print("custom sound + metronome UI added")
