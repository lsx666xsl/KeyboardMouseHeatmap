"""Replay patch 4: DailyCard integration + footprint toggle UI."""
from pathlib import Path

p = Path(r"F:\TauriProject\KeyboardMouseHeatmap\src\App.vue")
t = p.read_text(encoding="utf-8")

# import
anchor = 'import { configureSound, playKeySound, type SoundVoice } from "./sound";'
assert anchor in t
t = t.replace(anchor, anchor + '\nimport DailyCard from "./DailyCard.vue";')

# state
anchor2 = "const toastMsg = ref(\"\");"
assert anchor2 in t
state = anchor2 + """
const footprintAuto = ref(localStorage.getItem("keypulse-footprint-auto") !== "0");
const showFootprintCard = ref(false);
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

function autoShowFootprintIfNew() {
  if (!footprintAuto.value || demoMode.value) return;
  const today = new Date().toISOString().slice(0, 10);
  const seen = localStorage.getItem("keypulse-footprint-seen") || "";
  if (seen === today) return;
  if (liveDashboard.value && liveDashboard.value.totalKeyPresses > 0) {
    openFootprintCard();
  }
}"""
t = t.replace(anchor2, state)

# after first dashboard fetch mark? auto show after connect: call once data ready
old_mount = """    connectToRuntime();
    wireSoundFx();"""
assert old_mount in t
t = t.replace(old_mount, """    connectToRuntime();
    wireSoundFx();
    setTimeout(autoShowFootprintIfNew, 2600);""")

# footer link
old_footer = '<button class="clear-button" :disabled="demoMode" @click="clearStats">清空本地数据</button>'
assert old_footer in t
t = t.replace(old_footer, '<button class="clear-button" :disabled="demoMode" @click="clearStats">清空本地数据</button><button class="footprint-button" @click="openFootprintCard">✦ 足迹卡</button>')

# DailyCard host before toast transition
old_toast = '<Transition name="toast-pop">'
assert old_toast in t
t = t.replace(old_toast, '<DailyCard v-if="showFootprintCard && footprintSnapshot" :snapshot="footprintSnapshot" @close="showFootprintCard = false; localStorage.setItem(\'keypulse-footprint-seen\', new Date().toISOString().slice(0, 10))" />\n    <Transition name="toast-pop">')

# fun settings row: add footprint toggle below achievements column (same row becomes 3 cols is heavy; place as its own full-width toggle before note)
note = '<p class="ks-note">⌨ 显示的是按下动作，不记录文本 · 托盘菜单或顶栏 ⌨ 按钮可随时开/关 · 拖动后选择任意预设位置可恢复对齐</p>'
assert note in t
extra = """              <div class="ks-layout-row">
                <div class="ks-layout-col"><div class="ks-layout-title">每日足迹卡</div>
                  <button class="ks-drag-toggle" :class="{ on: footprintAuto }" @click="toggleFootprintAuto(!footprintAuto)"><span class="ks-master-text"><b>{{ footprintAuto ? "自动提醒已开" : "自动提醒已关" }}</b><small>每天首次打开时弹出当天的足迹卡</small></span><span class="ks-switch"><i></i></span></button>
                </div>
                <div class="ks-layout-col"><div class="ks-layout-title"> </div>
                  <button class="ks-size" style="width:100%; padding:11px 0;" @click="openFootprintCard">✦ 立即查看今日足迹</button>
                </div>
              </div>
"""
t = t.replace(note, extra + note)

# styles
anchor_css = ".toast-pop-enter-from, .toast-pop-leave-to { opacity: 0; transform: translateY(16px) scale(.92); }"
assert anchor_css in t
t = t.replace(anchor_css, anchor_css + "\n.footprint-button { border: 0; padding: 0 10px; color: var(--tx-faint); background: transparent; cursor: pointer; font-size: 10px; }\n.footprint-button:hover { color: var(--acc-pink-soft); }")

p.write_text(t, encoding="utf-8")
print("patch4 applied")
